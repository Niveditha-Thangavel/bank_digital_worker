"""
Banking Agent Backend (JSON-based) — uses only:
  - bank_statements.json    (source of transactions per customer)
  - credits_loan.json       (source of customers, credit_cards, loans)
  - decisions.json          (created/updated by this backend to store decisions)

CrewAI agent integration is preserved but optional:
  - If `crewai` is importable and LLM_API_KEY is set in env, the agent endpoints will invoke it.

Run:
    uvicorn backend:app --reload
"""
import os
import json
import uuid
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Body, Query
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from threading import Lock

load_dotenv()

# ---- FILE NAMES (use these three files only) ----
BANK_STATEMENTS_FILE = "bank_statements.json"   # must contain {"bank_statements":[...]}
CREDITS_LOAN_FILE = "credits_loan.json"         # must contain {"customer_accounts":[...]}
DECISIONS_FILE = "decisions.json"               # will be created/updated by this backend

# ---- Ensure decisions file exists ----
if not os.path.exists(DECISIONS_FILE):
    with open(DECISIONS_FILE, "w") as f:
        json.dump([], f, indent=2)

# ---- Simple file access helpers with thread-safety ----
_file_lock = Lock()

def _read_json_file(path: str) -> Any:
    if not os.path.exists(path):
        return {}
    with _file_lock:
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}

def _write_json_file(path: str, data: Any):
    with _file_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

# ---- Load source data helpers ----
def _load_bank_statements() -> List[Dict[str, Any]]:
    data = _read_json_file(BANK_STATEMENTS_FILE)
    return data.get("bank_statements", []) if isinstance(data, dict) else []

def _load_customer_accounts() -> List[Dict[str, Any]]:
    data = _read_json_file(CREDITS_LOAN_FILE)
    return data.get("customer_accounts", []) if isinstance(data, dict) else []

def _load_decisions() -> List[Dict[str, Any]]:
    data = _read_json_file(DECISIONS_FILE)
    return data if isinstance(data, list) else []

def _append_decision(decision_obj: Dict[str, Any]) -> Dict[str, Any]:
    decisions = _load_decisions()
    decisions.append(decision_obj)
    _write_json_file(DECISIONS_FILE, decisions)
    return decision_obj

# ---- Data access functions using only the two inputs ----
def list_customers() -> List[Dict[str, Any]]:
    return _load_customer_accounts()

def get_customer(customer_id: str) -> Optional[Dict[str, Any]]:
    customers = _load_customer_accounts()
    for c in customers:
        if c.get("customer_id") == customer_id:
            # return shallow copy
            return dict(c)
    return None

def get_transactions(customer_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    bank_stmts = _load_bank_statements()
    for entry in bank_stmts:
        if entry.get("customer_id") == customer_id:
            txs = entry.get("transactions", [])
            # sort by date descending if date strings are ISO-like
            try:
                txs_sorted = sorted(txs, key=lambda x: x.get("date") or "", reverse=True)
            except Exception:
                txs_sorted = list(txs)
            return txs_sorted[:limit]
    return []

def get_credit_cards(customer_id: str) -> List[Dict[str, Any]]:
    cust = get_customer(customer_id)
    if not cust:
        return []
    return cust.get("credit_cards", []) or []

def get_loans(customer_id: str) -> List[Dict[str, Any]]:
    cust = get_customer(customer_id)
    if not cust:
        return []
    return cust.get("loans", []) or []

def list_decisions(customer_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    all_dec = _load_decisions()
    if customer_id:
        filtered = [d for d in all_dec if d.get("customer_id") == customer_id]
    else:
        filtered = all_dec
    # most recent first (by created_at) if present
    try:
        filtered_sorted = sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True)
    except Exception:
        filtered_sorted = filtered
    return filtered_sorted[:limit]

def record_decision(customer_id: str, decision: str, reason: str) -> Dict[str, Any]:
    obj = {
        "id": str(uuid.uuid4()),
        "customer_id": customer_id,
        "decision": decision,
        "reason": reason,
        "created_at": datetime.utcnow().isoformat()
    }
    return _append_decision(obj)

# ---- Optional: reload endpoints helpers (dev convenience) ----
def reload_sources():
    # simply reads them - read helpers always read fresh file contents
    return {
        "bank_statements_count": len(_load_bank_statements()),
        "customer_accounts_count": len(_load_customer_accounts()),
        "decisions_count": len(_load_decisions()),
    }

# ---- Optional CrewAI agent integration (kept) ----
try:
    from crewai import Agent, Crew, LLM, Task
    from crewai.tools import BaseTool
    CREW_AVAILABLE = True
except Exception:
    CREW_AVAILABLE = False

LLM_API_KEY = os.getenv("LLM_API_KEY")

# Agent Tools use local helpers above
if CREW_AVAILABLE:
    class FetchTool(BaseTool):
        name: str = "FetchBankStatement"
        description: str = "Fetch the bank statement and credit/loan profile for a specific customer_id"

        def _run(self, customer_id: str):
            cust = get_customer(customer_id)
            if not cust:
                return {"error": f"Customer {customer_id} not found"}
            transactions = get_transactions(customer_id, limit=200)
            cards = get_credit_cards(customer_id)
            loans = get_loans(customer_id)
            return {
                "customer": cust,
                "transactions": transactions,
                "credit_cards": cards,
                "loans": loans,
            }

    class RulesTool(BaseTool):
        name: str = "Rules provider"
        description: str = "Provides the rule-set text to check eligibility of loan"

        def _run(self, *args, **kwargs):
            return DEFAULT_RULES_TEXT

    def build_crew(prompt: str) -> Crew:
        # Use LLM_API_KEY if available; the user's environment controls this
        llm = LLM(model="gemini/gemini-2.5-flash", api_key=LLM_API_KEY) if LLM_API_KEY else LLM()
        chatbot = Agent(
            role="Chatbot",
            goal=f"Answer and accomplish the task in '{prompt}'",
            backstory="Expert in answering questions and completing the right task using the right tool",
            tools=[FetchTool(), RulesTool()],
            llm=llm,
        )
        chatbot_task = Task(
            description=(
                "Answer questions and accomplish the task using the available tools. "
                "Use FetchBankStatement to fetch customer's data and Rules provider to fetch decision rules."
            ),
            expected_output="Answer with correct tool usage and conclusions",
            agent=chatbot,
        )
        return Crew(agents=[chatbot], tasks=[chatbot_task], verbose=False)

# ---- Default rules text used by agent/tool if needed ----
DEFAULT_RULES_TEXT = (
    "Rules:\n"
    "1. Income Check: Income must be ≥ ₹20,000 per month\n"
    "2. Account Age: Account must be ≥ 6 months old\n"
    "3. Payment History: Late payments must be ≤ 2\n"
    "4. Transaction Issues: There must be no transaction anomalies\n"
    "5. Credit Usage: Credit utilization must be < 70%\n"
    "6. Current Loans: Customer must have ≤ 1 active loan\n"
    "7. Income–Spend Health Check: Monthly income must show a clear positive margin over monthly spending\n"
    "8. Transaction Activity Check: Customer should have consistent and healthy transaction activity\n"
    "9. Outlier Behavior Check: There must be no extreme or unexplained large transaction outliers\n"
    "10. Liquidity Buffer Check: Customer should maintain a reasonable financial buffer or savings room\n"
    "11. Credit History Strength: Customer must show reliable and stable historical credit behavior\n"
    "Decision rule (exact mapping):\n"
    '- If number_of_rules_satisfied == 11 -> decision = \"APPROVE\"\n'
    '- If 8 <= number_of_rules_satisfied < 11 -> decision = \"REVIEW\"\n'
    '- If number_of_rules_satisfied < 8 -> decision = \"REJECT\"\n\n'
    'OUTPUT REQUIREMENT: Return exactly the JSON object {"decision":"APPROVE|REVIEW|REJECT","reason":"string"} and NOTHING else.'
)

# ---- FastAPI app and endpoints ----
app = FastAPI(title="Banking Agent (JSON DB) - No Auth Mode")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Pydantic models (minimal) ----
class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[str] = None
    session_id: Optional[str] = None
    end_session: Optional[bool] = False
    role: Optional[str] = "customer"

# Sessions (in-memory, non-persistent except decisions)
_sessions_in_memory: Dict[str, List[Dict[str, Any]]] = {}
_sessions_history_in_memory: Dict[str, List[List[Dict[str, Any]]]] = {}

# --- Health ---
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/health/full")
def health_full():
    try:
        bank_count = len(_load_bank_statements())
        cust_count = len(_load_customer_accounts())
        dec_count = len(_load_decisions())
        return {"status": "ok", "bank_statements": bank_count, "customer_accounts": cust_count, "decisions": dec_count}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# --- Customers / read-only view built from credits_loan.json and bank_statements.json ---
@app.get("/customers")
def api_list_customers():
    customers = list_customers()
    # return minimal metadata
    summary = [{"customer_id": c.get("customer_id"), "account_creation_date": c.get("account_creation_date")} for c in customers]
    return {"status": "ok", "customers": summary}

@app.get("/customer/{customer_id}")
def api_get_customer_front(customer_id: str):
    cust = get_customer(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="customer not found")
    txs = get_transactions(customer_id, limit=500)
    cards = get_credit_cards(customer_id)
    loans = get_loans(customer_id)
    decisions = list_decisions(customer_id, limit=100)
    return {"status": "ok", "customer": cust, "transactions": txs, "credit_cards": cards, "loans": loans, "decisions": decisions}

# --- Decisions endpoints (persisted to decisions.json) ---
@app.get("/decisions")
def api_get_decisions(customer_id: Optional[str] = Query(None), limit: int = 100):
    rows = list_decisions(customer_id, limit)
    return {"status": "ok", "decisions": rows}

@app.post("/update-decisions")
def api_update_decision(payload: Dict[str, Any] = Body(...)):
    """
    Body: { "customer_id": "...", "decision": "APPROVE", "reason":"..." }
    This writes a new decision entry into decisions.json (append-only).
    """
    cust_id = payload.get("customer_id")
    decision = payload.get("decision")
    reason = payload.get("reason", "")
    if not cust_id or not decision:
        raise HTTPException(status_code=400, detail="customer_id and decision required")
    saved = record_decision(cust_id, decision, reason)
    return {"status": "ok", "decision": saved}

# --- Chat (lightweight) ---
@app.post("/chat")
def api_chat(req: ChatRequest):
    prompt = req.message
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in _sessions_in_memory:
        _sessions_in_memory[session_id] = []
    _sessions_in_memory[session_id].append({"role": "user", "text": prompt, "time": datetime.utcnow().isoformat()})

    combined_context = "\n".join([f"{t['role'].upper()}: {t['text']}" for t in _sessions_in_memory[session_id][-20:]])

    if req.customer_id:
        try:
            cust = get_customer(req.customer_id)
            txs = get_transactions(req.customer_id, limit=50)
            cards = get_credit_cards(req.customer_id)
            loans = get_loans(req.customer_id)
            # produce a brief summary
            total_credit_limit = sum((c.get("credit_limit") or 0) for c in cards)
            total_balance = sum((c.get("current_balance") or 0) for c in cards)
            credit_util = (total_balance / total_credit_limit * 100) if total_credit_limit else None
            recent_tx_count = len(txs)
            monthly_income_estimate = None
            credits = [t for t in txs if str(t.get("type","")).lower() == "credit"]
            if credits:
                try:
                    monthly_income_estimate = max((t.get("amount") or 0) for t in credits)
                except Exception:
                    monthly_income_estimate = None
            summary = {
                "customer_id": cust.get("customer_id"),
                "name": cust.get("name"),
                "monthly_income_estimate": monthly_income_estimate,
                "credit_utilization_pct": round(credit_util,2) if credit_util is not None else None,
                "recent_tx_count": recent_tx_count,
                "active_loans_count": len(loans),
            }
            combined_context += "\n\nCustomerSummary: " + str(summary)
            _sessions_in_memory[session_id].append({"role":"system","text":f"Fetched summary for {req.customer_id}","time":datetime.utcnow().isoformat()})
        except Exception:
            combined_context += "\n\nCustomerSummary: unavailable (read error)"

    # If Crew is available, optionally run agent; else fallback string
    assistant_reply = None
    if CREW_AVAILABLE:
        try:
            crew = build_crew(combined_context)
            result = crew.kickoff()
            assistant_reply = str(result)
            # if agent returns JSON decision, try to store
            try:
                import json as _json
                parsed = _json.loads(assistant_reply)
                if isinstance(parsed, dict) and parsed.get("decision") and parsed.get("reason") and req.customer_id:
                    record_decision(req.customer_id, parsed["decision"], parsed["reason"])
            except Exception:
                pass
        except Exception as exc:
            tb = traceback.format_exc()
            print(tb)
            assistant_reply = f"Agent error: {str(exc)}"
    else:
        if req.customer_id:
            assistant_reply = "Assistant (fallback): I have your account summary. Ask 'check eligibility' to run a rules check (agent not available)."
        else:
            assistant_reply = "Assistant (fallback): Provide your customer_id to fetch account information (agent not available)."

    _sessions_in_memory[session_id].append({"role":"assistant","text":assistant_reply,"time":datetime.utcnow().isoformat()})
    return {"reply": assistant_reply, "session_id": session_id, "session_snapshot": _sessions_in_memory.get(session_id)}

# --- Admin-run agent endpoint (invokes Crew if available) ---
@app.post("/admin/customers/{customer_id}/run-agent")
def admin_run_agent_for_customer(customer_id: str):
    if not CREW_AVAILABLE:
        raise HTTPException(status_code=501, detail="Agent integration not available on this server build")
    cust = get_customer(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="customer not found")
    txs = get_transactions(customer_id, limit=200)
    cards = get_credit_cards(customer_id)
    loans = get_loans(customer_id)
    prompt_parts = [
        f"Evaluate loan eligibility for customer {customer_id}.",
        "Use the following data (redacted where needed):",
        f"Customer: {cust}",
        f"Credit cards: {cards}",
        f"Loans: {loans}",
        f"Recent transactions (top 50): {txs[:50]}",
        "Return EXACTLY a JSON object: {\"decision\":\"APPROVE|REVIEW|REJECT\",\"reason\":\"...\"} and NOTHING else."
    ]
    prompt = "\n\n".join(prompt_parts)
    try:
        crew = build_crew(prompt)
        result = crew.kickoff()
        assistant_reply = str(result)
        import json as _json
        try:
            parsed = _json.loads(assistant_reply)
        except Exception:
            return {"status":"ok", "agent_reply": assistant_reply, "note":"agent output not valid JSON; decision not saved"}
        if isinstance(parsed, dict) and parsed.get("decision") and parsed.get("reason"):
            saved = record_decision(customer_id, parsed["decision"], parsed["reason"])
            return {"status":"ok", "agent_decision": parsed, "saved": saved}
        else:
            return {"status":"ok", "agent_reply": assistant_reply, "note":"agent output did not match expected decision shape"}
    except Exception as exc:
        tb = traceback.format_exc()
        print(tb)
        raise HTTPException(status_code=500, detail=f"failed to run agent: {str(exc)}")

# --- Dev helper: reload/read counts ---
@app.get("/_dev/reload-sources")
def dev_reload_sources():
    return reload_sources()

# --- Simple endpoints for transactions/creditcards/loans read-only under /customers ---
@app.get("/customers/{customer_id}/transactions")
def api_get_transactions(customer_id: str, limit: int = 200):
    txs = get_transactions(customer_id, limit)
    return {"status":"ok", "transactions": txs}

@app.get("/customers/{customer_id}/credit_cards")
def api_get_credit_cards(customer_id: str):
    cards = get_credit_cards(customer_id)
    return {"status":"ok", "credit_cards": cards}

@app.get("/customers/{customer_id}/loans")
def api_get_loans(customer_id: str):
    loans = get_loans(customer_id)
    return {"status":"ok", "loans": loans}
