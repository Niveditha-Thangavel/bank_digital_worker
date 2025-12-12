import os, re
import json
import uuid
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Task
from crewai.tools import BaseTool

load_dotenv()

#Loading json files
BANK_STATEMENTS_FILE = "bank_statements.json"
CREDITS_LOAN_FILE = "credits_loan.json"
DECISIONS_FILE = "decisions.json"

if not os.path.exists(DECISIONS_FILE):
    with open(DECISIONS_FILE, "w", encoding="utf-8") as f:
        json.dump({"decisions": []}, f, indent=2, ensure_ascii=False)


#Functions to perform file actions
def _read_json_file(path: str) -> Any:
    """Return parsed JSON or {} on parse error."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_json_file(path: str, data: Any):
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[ERROR] Failed to write {path}: {e}")
        traceback.print_exc()
        raise

def _load_bank_statements() -> List[Dict[str, Any]]:
    data = _read_json_file(BANK_STATEMENTS_FILE)
    return data.get("bank_statements", []) if isinstance(data, dict) else []

def _load_customer_accounts() -> List[Dict[str, Any]]:
    data = _read_json_file(CREDITS_LOAN_FILE)
    return data.get("customer_accounts", []) if isinstance(data, dict) else []

def _load_decisions() -> Dict[str, List[Dict[str, Any]]]:
    """Always return canonical dict shape."""
    raw = _read_json_file(DECISIONS_FILE)
    if isinstance(raw, dict) and "decisions" in raw and isinstance(raw["decisions"], list):
        return raw
    if isinstance(raw, list):
        return {"decisions": raw}
    return {"decisions": []}

def _append_decision(decision_obj: Dict[str, Any], override_existing: bool = False) -> Dict[str, Any]:
    """Append decision WITHOUT LOCK."""
    data = _load_decisions()
    decisions = data.get("decisions", [])

    if override_existing:
        decisions = [d for d in decisions if d.get("customer_id") != decision_obj.get("customer_id")]

    decisions.append(decision_obj)
    data["decisions"] = decisions
    _write_json_file(DECISIONS_FILE, data)
    return decision_obj

def list_customers() -> List[Dict[str, Any]]:
    return _load_customer_accounts()

def get_customer(customer_id: str) -> Optional[Dict[str, Any]]:
    customers = _load_customer_accounts()
    for c in customers:
        if c.get("customer_id") == customer_id:
            return dict(c)
    return None

def get_transactions(customer_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    bank_stmts = _load_bank_statements()
    for entry in bank_stmts:
        if entry.get("customer_id") == customer_id:
            txs = entry.get("transactions", [])
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
    all_dec = _load_decisions().get("decisions", [])
    if customer_id:
        filtered = [d for d in all_dec if d.get("customer_id") == customer_id]
    else:
        filtered = all_dec
    try:
        filtered_sorted = sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True)
    except:
        filtered_sorted = filtered
    return filtered_sorted[:limit]

def record_decision(customer_id: str, decision: str, reason: str, override_existing: bool = False) -> Dict[str, Any]:
    obj = {
        "id": str(uuid.uuid4()),
        "customer_id": customer_id,
        "decision": decision,
        "reason": reason,
        "created_at": datetime.utcnow().isoformat()
    }
    print("Recording decision:", obj)
    return _append_decision(obj, override_existing=override_existing)

def reload_sources():
    return {
        "bank_statements_count": len(_load_bank_statements()),
        "customer_accounts_count": len(_load_customer_accounts()),
        "decisions_count": len(_load_decisions().get("decisions", [])),
    }

#Declaring tools to support chat model
try:
    CREW_AVAILABLE = True
except Exception:
    CREW_AVAILABLE = False

LLM_API_KEY = os.getenv("LLM_API_KEY")

if CREW_AVAILABLE:
    class FetchTool(BaseTool):
        name: str = "CustomerDataTool"
        description: str = "Provides the customer's data summary and full profile is available in the chat context if customer_id is set. Do not call with customer_id argument."

        def _run(self, *args, **kwargs):
            return "Customer's data summary and full profile (transactions, credit, loans) are available in the chat context if customer_id was provided."

    class RulesTool(BaseTool):
        name: str = "RulesProvider"
        description: str = "Provides the complete rule-set text to check eligibility of loan."

        def _run(self, *args, **kwargs):
            return DEFAULT_RULES_TEXT
        
    class FetchdecTool(BaseTool):
        name: str = "FetchDecisions"
        description: str = "Fetch all the decisions from decisions.json as a JSON string. Can be filtered by customer_id."

        def _run(self):
            decisions = _load_decisions()
            return json.dumps(decisions)

    class update_decisionTool(BaseTool):
        name:str = "UpdateDecisions"
        description:str = "Update the decision of customer id "
        def _run(self, customer_id: str, decision: str, reason: str):
            data = _load_decisions()  
            found = False
            print(decision, reason, customer_id)
            for d in data.get("decisions", []):
                if d.get("customer_id") == customer_id:
                    d["decision"] = decision
                    d["reason"] = reason
                    d["created_at"] = datetime.utcnow().isoformat()
                    found = True
                    break
            _write_json_file(DECISIONS_FILE, data)
            if found:
                return "Decision updated successfully"
            return "Customer id not found"

    #Creating crew with agent and task
    def build_crew(prompt: str, role: str) -> Crew:
        llm = LLM(model="gemini/gemini-2.5-flash", api_key=LLM_API_KEY) if LLM_API_KEY else LLM()
        
        #for admin chat
        if role == "admin":
            tool_list = [FetchdecTool(), update_decisionTool()]

            agent_goal = (
                f"Provide accurate, complete, and professionally formatted responses to the user in a friendly way "
                f"based on the administrator's request: '{prompt}'. "
                f"Use FetchDecisions for any request involving decisions or summaries."
                "use UpdateDecisions for updating decisions"
            )

            agent_backstory = (
                "You are an expert administrative decision-analysis agent. "
                "You have full access to all historical decisions via FetchDecisions "
                "and the ability to directly modify any customer's decision using "
                "update_decisionTool. "
                "You always respond with precise, professional, clean output — no extra text."
            )

            task_description = (
                "You are operating in Admin mode. Follow these rules carefully:\n\n"

                " **Fetching Decisions**\n"
                "- When the admin asks to show, view, list, retrieve, or compare decisions, "
                "you MUST call FetchDecisions.\n"
                "- Parse the returned JSON and output ONLY a clean Markdown table.\n"
                "- Columns: ID, Customer ID, Decision, Reason.\n"
                "- No text before or after the table.\n\n"

                " **Updating Decisions Automatically**\n"
                "- When the admin asks to change, modify, update, override, correct, or adjust "
                "a customer's decision, you MUST call update_decisionTool.\n"
                "- Use it with the required arguments: customer_id, decision, reason.\n"
                "- After the tool call, provide a short, professional confirmation message.\n\n"

                " **Formatting Rules**\n"
                "- Never include explanations unless explicitly asked.\n"
                "- Never output JSON unless the admin explicitly requests JSON.\n"
                "- Always maintain a clean, professional tone.\n\n"
            )

            expected_output = (
                "A clean Markdown table, or a confirmation message after decision update"
            )

        #for customer chat
        else:
            tool_list = [FetchTool(), RulesTool()]
            agent_goal = f"Provide details and chats in a friendly way and accomplish the task in '{prompt}'"
            agent_backstory = "Expert in answering customer questions, providing friendly explanations, and completing the right task using the right tool. You have access to the customer's summary and profile when a customer_id is set. You CANNOT access other customer's data."
            task_description = (
                "Chat with the user in a friendly manner. "
                "Answer questions and accomplish the task using the available tools. "
                "Use the RulesProvider to fetch decision rules when an eligibility check is requested and mention as the given format Decision: and Reason: always"
                "Use the CustomerDataTool as a reference that you have access to the customer's data. If customer_id is not provided, you cannot access account details. If unable to answer, apologize and tell that you will come back soon, also thank them for their patience. Provide only their details to the customer, by using their customer id."
            )
            expected_output = "User friendly answer to the question (no json)."

        chatbot = Agent(
            role="Chatbot",
            goal=agent_goal,
            backstory=agent_backstory,
            tools=tool_list,
            llm=llm,
        )
        
        chatbot_task = Task(
            description=task_description,
            expected_output=expected_output,
            agent=chatbot,
        )
        return Crew(agents=[chatbot], tasks=[chatbot_task], verbose=False)

#Rules used for analysis
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

#api connection
app = FastAPI(title="Banking Agent (JSON DB) - No Auth Mode")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[str] = None
    session_id: Optional[str] = None
    end_session: Optional[bool] = False
    role: Optional[str] = "customer"

_sessions_in_memory: Dict[str, List[Dict[str, Any]]] = {}

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/health/full")
def health_full():
    try:
        bank_count = len(_load_bank_statements())
        cust_count = len(_load_customer_accounts())
        dec_count = len(_load_decisions().get("decisions", []))
        return {"status": "ok", "bank_statements": bank_count, "customer_accounts": cust_count, "decisions": dec_count}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/customers")
def api_list_customers():
    customers = list_customers()
    summary = [{"customer_id": c.get("customer_id"), "account_creation_date": c.get("account_creation_date"), "name": c.get("name")} for c in customers]
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


@app.post("/update-decisions")
def api_update_decision(payload: Dict[str, Any] = Body(...)):
    cust_id = payload.get("customer_id")
    decision = payload.get("decision")
    reason = payload.get("reason", "")
    if not cust_id or not decision:
        raise HTTPException(status_code=400, detail="customer_id and decision required")
    # Here we record a new decision entry; preserve history by default
    saved = record_decision(cust_id, decision, reason)
    return {"status": "ok", "decision": saved}

@app.post("/admin/chat")
def admin_api_chat(req: ChatRequest):
    prompt = req.message
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in _sessions_in_memory:
        _sessions_in_memory[session_id] = []
    _sessions_in_memory[session_id].append({"role": "user", "text": prompt, "time": datetime.utcnow().isoformat()})

    combined_context = "\n".join([f"{t['role'].upper()}: {t['text']}" for t in _sessions_in_memory[session_id][-20:]])
    req.role = "admin"
    try:
        cust = get_customer(req.customer_id)
        txs = get_transactions(req.customer_id, limit=50)
        cards = get_credit_cards(req.customer_id)
        loans = get_loans(req.customer_id)
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
        combined_context += "\n\nCustomerSummary: " + json.dumps(summary, indent=2)
        combined_context += "\n\nCustomerFullProfile:"
        combined_context += "\n- Profile: " + json.dumps(cust, indent=2)
        combined_context += "\n- Transactions (Recent 50): " + json.dumps(txs, indent=2)
        combined_context += "\n- Credit Cards: " + json.dumps(cards, indent=2)
        combined_context += "\n- Loans: " + json.dumps(loans)

        _sessions_in_memory[session_id].append({"role":"system","text":f"Fetched summary and full profile for {req.customer_id} and injected into prompt context.","time":datetime.utcnow().isoformat()})
    except Exception:
        combined_context += "\n\nCustomerSummary: unavailable (read error)"

    assistant_reply = None
    if CREW_AVAILABLE:
        try:
            crew = build_crew(combined_context, role=req.role)
            try:
                setattr(crew, "verbose", True)
            except Exception:
                pass

            try:
                result = crew.kickoff()
                assistant_reply = str(result)
            except Exception as kickoff_exc:
                print("[CREW ERROR] kickoff failed:", repr(kickoff_exc))
                try:
                    for i, t in enumerate(getattr(crew, "tasks", []) or []):
                        print(f"[CREW DEBUG] Task[{i}] desc:", getattr(t, "description", None))
                        print(f"[CREW DEBUG] Task[{i}] expected_output:", getattr(t, "expected_output", None))
                except Exception as iterr:
                    print("[CREW DEBUG] task introspect failed:", iterr)
                try:
                    for i, a in enumerate(getattr(crew, "agents", []) or []):
                        print(f"[CREW DEBUG] Agent[{i}] role:", getattr(a, "role", None))
                        print(f"[CREW DEBUG] Agent[{i}] goal:", getattr(a, "goal", None))
                except Exception as aerr:
                    print("[CREW DEBUG] agent introspect failed:", aerr)

                tb = traceback.format_exc()
                print(tb)
                assistant_reply = f"Agent error: {str(kickoff_exc)}"
                
            if assistant_reply:
                print("[DEBUG] assistant raw reply:", assistant_reply)
                parsed = None
                try:
                    parsed = json.loads(assistant_reply)
                    print("[DEBUG] parsed JSON (direct):", parsed)
                except Exception:
                    parsed = None

                if parsed is None:
                    m_dec = re.search(r"(?mi)^\s*Decision\s*:\s*(.+)$", assistant_reply)
                    m_rea = re.search(r"(?mi)^\s*Reason\s*:\s*((?:.|\n)*?)(?:\n\s*\n|$)", assistant_reply, re.S)

                    decision_val = m_dec.group(1).strip() if m_dec else None
                    reason_val = None
                    if m_rea:
                        raw_reason = m_rea.group(1).strip()
                        lines = [ln.strip() for ln in raw_reason.splitlines() if ln.strip()]
                        reason_val = " ".join(lines)

                    if decision_val or reason_val:
                        parsed = {
                            "Decision": decision_val,
                            "decision": decision_val,
                            "Reason": reason_val,
                            "reason": reason_val
                        }
                        print("[DEBUG] parsed from regex:", parsed)

                if isinstance(parsed, dict) and req.customer_id:
                    dec = parsed.get("decision") or parsed.get("Decision") or parsed.get("DECISION")
                    rea = parsed.get("reason") or parsed.get("Reason") or parsed.get("REASON")
                    if dec and rea:
                        try:
                            print(f"[INFO] saving decision for {req.customer_id}: {dec} - {rea[:120]}...")
                            record_decision(req.customer_id, dec, rea, override_existing=True)
                            print("[INFO] record_decision succeeded")
                            try:
                                print("[INFO] DECISIONS_FILE path:", os.path.abspath(DECISIONS_FILE))
                            except Exception:
                                pass
                        except Exception as write_exc:
                            print("[ERROR] record_decision raised:", write_exc)
                            traceback.print_exc()
                    else:
                        print("[WARN] parsed dict missing decision/reason keys:", parsed)
                else:
                    print("[DEBUG] parsed not dict or no customer_id; parsed:", parsed)
            else:
                print("[WARN] assistant_reply empty after kickoff")
        except Exception as exc:
            tb = traceback.format_exc()
            print("[UNEXPECTED ERROR] in CREW_AVAILABLE branch:", tb)
            assistant_reply = f"Agent error: {str(exc)}"
    else:
        if req.customer_id:
            assistant_reply = "Assistant (fallback): I have your account summary. Ask 'check eligibility' to run a rules check (agent not available)."
        else:
            assistant_reply = "Assistant (fallback): Provide your customer_id to fetch account information (agent not available)."

    return {"reply": assistant_reply, "session_id": session_id, "session_snapshot": _sessions_in_memory.get(session_id)}

@app.post("/chat")
def api_chat(req: ChatRequest):
    prompt = req.message
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in _sessions_in_memory:
        _sessions_in_memory[session_id] = []
    _sessions_in_memory[session_id].append({"role": "user", "text": prompt, "time": datetime.utcnow().isoformat()})

    combined_context = "\n".join([f"{t['role'].upper()}: {t['text']}" for t in _sessions_in_memory[session_id][-20:]])


    req.role == "customer"
    try:
        cust = get_customer(req.customer_id)
        txs = get_transactions(req.customer_id, limit=50)
        cards = get_credit_cards(req.customer_id)
        loans = get_loans(req.customer_id)
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
        combined_context += "\n\nCustomerSummary: " + json.dumps(summary, indent=2)
        combined_context += "\n\nCustomerFullProfile:"
        combined_context += "\n- Profile: " + json.dumps(cust, indent=2)
        combined_context += "\n- Transactions (Recent 50): " + json.dumps(txs, indent=2)
        combined_context += "\n- Credit Cards: " + json.dumps(cards, indent=2)
        combined_context += "\n- Loans: " + json.dumps(loans)

        _sessions_in_memory[session_id].append({"role":"system","text":f"Fetched summary and full profile for {req.customer_id} and injected into prompt context.","time":datetime.utcnow().isoformat()})
    except Exception:
        combined_context += "\n\nCustomerSummary: unavailable (read error)"

    assistant_reply = None
    if CREW_AVAILABLE:
        try:
            crew = build_crew(combined_context, role=req.role)
            result = crew.kickoff()
            assistant_reply = str(result)
            try:
                
                print("[DEBUG] assistant raw reply:", assistant_reply)
                m_dec = re.search(r"(?mi)^Decision\s*:\s*(.+)$", assistant_reply)
                m_rea = re.search(r"(?mi)^Reason\s*:\s*((?:.|\n)*?)(?:\n\s*\n|$)", assistant_reply)

                decision_val = m_dec.group(1).strip() if m_dec else None
                reason_val = None

                if m_rea:
                    raw_reason = m_rea.group(1).strip()
                    lines = [ln.strip() for ln in raw_reason.splitlines() if ln.strip()]
                    reason_val = " ".join(lines)

                print("[DEBUG] extracted decision:", decision_val)
                print("[DEBUG] extracted reason:", reason_val)

                if decision_val and reason_val and req.customer_id:
                    print(f"[INFO] saving decision for {req.customer_id}")
                    record_decision(req.customer_id, decision_val, reason_val)
                else:
                    print("[WARN] Could not extract decision/reason from assistant reply")
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



@app.get("/decisions")
def get_decision():
    return _load_decisions()

@app.get("/_dev/reload-sources")
def dev_reload_sources():
    return reload_sources()

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


class BillingCycle(BaseModel):
    cycle_start: str
    cycle_end: str
    amount_due: float     
    amount_paid: float     
    payment_date: str

class CreditCard(BaseModel):
    card_number: str
    credit_limit: float   
    current_balance: float
    billing_cycles: List[BillingCycle] 

class Loan(BaseModel):
    loan_id: str
    loan_type: str
    principal_amount: float    
    outstanding_amount: float   
    monthly_due: float          
    last_payment_date: str

class Transaction(BaseModel):
    date: str
    amount: float          
    type: str
    description: str

class customerdata(BaseModel):
    customer_id: str
    account_creation_date: Optional[str] = None
    name: Optional[str] = None
    credit_cards: Optional[List[CreditCard]] = None
    loans: Optional[List[Loan]] = None
    transactions: Optional[List[Transaction]] = None


@app.post("/admin/customer-data/saveCustomerData")
def api_update_customer_data(customer_data:customerdata):
    customer_id = customer_data.customer_id

    
    credits_loan_data = _read_json_file(CREDITS_LOAN_FILE)
    customer_accounts = credits_loan_data.get("customer_accounts", [])
    
    customer_found_cl = False
    for i, account in enumerate(customer_accounts):
        if account.get("customer_id") == customer_id:
            customer_found_cl = True
            

            if customer_data.account_creation_date is not None:
                customer_accounts[i]["account_creation_date"] = customer_data.account_creation_date
            if customer_data.name is not None:
                customer_accounts[i]["name"] = customer_data.name
                
        
            if customer_data.credit_cards is not None:
                customer_accounts[i]["credit_cards"] = [c.model_dump() for c in customer_data.credit_cards]
                
            if customer_data.loans is not None:
                customer_accounts[i]["loans"] = [l.model_dump() for l in customer_data.loans]
            break
            
    if not customer_found_cl:
        raise HTTPException(status_code=404, detail=f"Customer ID {customer_id} not found in {CREDITS_LOAN_FILE}")
        
    credits_loan_data["customer_accounts"] = customer_accounts
    _write_json_file(CREDITS_LOAN_FILE, credits_loan_data)
    
    
    bank_statements_data = _read_json_file(BANK_STATEMENTS_FILE)
    bank_statements = bank_statements_data.get("bank_statements", [])
    
    customer_found_bs = False
    if customer_data.transactions is not None:
        for i, statement in enumerate(bank_statements):
            if statement.get("customer_id") == customer_id:
                customer_found_bs = True
                bank_statements[i]["transactions"] = [t.model_dump() for t in customer_data.transactions]
                break
                
        if not customer_found_bs and customer_found_cl and customer_data.transactions:
             bank_statements.append({
                "customer_id": customer_id,
                "transactions": [t.model_dump() for t in customer_data.transactions]
             })
             customer_found_bs = True

    bank_statements_data["bank_statements"] = bank_statements
    _write_json_file(BANK_STATEMENTS_FILE, bank_statements_data)
    
    return {"status": "ok", "message": f"Customer ID {customer_id} data successfully updated in {CREDITS_LOAN_FILE} and {BANK_STATEMENTS_FILE}."}