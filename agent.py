# backend.py
"""
Banking Agent Backend (FastAPI) with Supabase integration.
Improvements:
- Added endpoints required by frontend (GET/POST customer, decisions update/list, api-status)
- Better error handling and API status indicator
- Upsert logic for POST /customer to load nested records (credit_cards, billing_cycles, loans, transactions)
Run:
    uvicorn backend:app --reload
"""
import os
import uuid
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Body, Header, Path, Query
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

# Supabase client
try:
    from supabase import create_client
except Exception as e:
    raise RuntimeError("supabase client not found. Install with: pip install supabase") from e

# Optional Crew/Agent imports (only used if available)
try:
    from crewai import Agent, Crew, LLM, Task
    from crewai.tools import BaseTool
    CREW_AVAILABLE = True
except Exception:
    CREW_AVAILABLE = False

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LLM_API_KEY = os.getenv("LLM_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY environment variables")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Banking Agent API (Supabase)")

# Allow local frontend (vite) + adjust as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],               # quick dev convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Simple server-side token auth (dev) ---
_tokens: Dict[str, Dict[str, str]] = {}  # token -> {"role": "admin"|"customer", "id": customer_id or admin_email}


def create_token(role: str, id_value: Optional[str] = None) -> str:
    t = str(uuid.uuid4())
    _tokens[t] = {"role": role, "id": id_value or ""}
    return t


def validate_token(token_header: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Accept either raw token or 'Bearer <token>' header form.
    Returns token metadata dict from _tokens or None.
    """
    if not token_header:
        # no header supplied
        return None

    token = token_header

    # If the header is "Bearer <token>", strip the prefix (case-insensitive)
    if isinstance(token, str) and token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()

    # Simple debug logging to help you see what arrived (remove or lower in production)
    try:
        print(f"[auth] validate_token called with token_header='{token_header}' -> token='{token[:8]}...'")
    except Exception:
        pass

    return _tokens.get(token)




# --- Pydantic models for request/response validation ---
class AuthRequest(BaseModel):
    role: str = Field(..., description="customer|admin")
    customer_id: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None  # dev-only


class AuthResponse(BaseModel):
    token: str
    role: str
    id: Optional[str] = None


class TransactionIn(BaseModel):
    tx_id: Optional[str] = None
    customer_id: str
    date: Optional[datetime] = None
    amount: float
    type: str  # "credit" or "debit"
    description: Optional[str] = None


class CreditCardIn(BaseModel):
    card_id: Optional[str] = None
    card_number: Optional[str] = None  # accept either
    customer_id: str
    credit_limit: float
    current_balance: float


class BillingCycleIn(BaseModel):
    card_id: str
    cycle_start: str
    cycle_end: str
    amount_due: float
    amount_paid: float
    payment_date: Optional[str] = None


class LoanIn(BaseModel):
    loan_id: Optional[str] = None
    customer_id: str
    principal_amount: Optional[float] = None
    outstanding_amount: Optional[float] = None
    monthly_due: Optional[float] = None
    loan_type: Optional[str] = None


class CustomerIn(BaseModel):
    customer_id: Optional[str] = None
    name: str
    email: Optional[str] = None
    account_creation_date: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[str] = None
    session_id: Optional[str] = None
    end_session: Optional[bool] = False
    role: Optional[str] = "customer"


# --- Helper: normalize Supabase APIResponse shapes ---
def _normalize_resp(resp: Any, table: str = "<unknown>"):
    data = getattr(resp, "data", None)
    if data is not None:
        return data
    try:
        if isinstance(resp, dict) and "data" in resp:
            return resp["data"]
    except Exception:
        pass
    try:
        getter = getattr(resp, "get", None)
        if callable(getter):
            d = resp.get("data")
            if d is not None:
                return d
    except Exception:
        pass
    raise RuntimeError(f"Unexpected supabase response for table '{table}': {repr(resp)}")


# --- Safe wrappers for common DB operations ---
def safe_select(table: str, select: str = "*", filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, order: Optional[Dict[str, Any]] = None):
    try:
        q = sb.table(table).select(select)
        if filters:
            for k, v in filters.items():
                if v is None:
                    continue
                q = q.eq(k, v)
        if order:
            if isinstance(order, dict):
                for col, opts in order.items():
                    if isinstance(opts, dict):
                        asc = opts.get("ascending", True)
                        q = q.order(col, {"ascending": asc})
        if limit:
            q = q.limit(limit)
        resp = q.execute()
    except Exception as e:
        raise RuntimeError(f"Supabase request failed for select on '{table}': {e}")
    return _normalize_resp(resp, table)


def safe_insert(table: str, payload: Any):
    try:
        resp = sb.table(table).insert(payload).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase insert failed for '{table}': {e}")
    return _normalize_resp(resp, table)


def safe_update(table: str, payload: Any, match_key: str, match_value: Any):
    try:
        resp = sb.table(table).update(payload).eq(match_key, match_value).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase update failed for '{table}': {e}")
    return _normalize_resp(resp, table)


def safe_delete(table: str, match_key: str, match_value: Any):
    try:
        resp = sb.table(table).delete().eq(match_key, match_value).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase delete failed for '{table}': {e}")
    return _normalize_resp(resp, table)


# --- Business helpers (use safe wrappers) ---
def get_customer(customer_id: str) -> Optional[Dict[str, Any]]:
    rows = safe_select("customers", "*", filters={"customer_id": customer_id}, limit=1)
    return rows[0] if rows else None


def create_customer(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.copy()
    if not data.get("customer_id"):
        data["customer_id"] = str(uuid.uuid4())
    if "created_at" not in data:
        data["created_at"] = datetime.utcnow().isoformat()
    rows = safe_insert("customers", data)
    return rows[0] if rows else {}


def list_customers(limit: int = 100) -> List[Dict[str, Any]]:
    return safe_select("customers", "*", limit=limit, order={"created_at": {"ascending": False}})


def get_transactions(customer_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    return safe_select("transactions", "*", filters={"customer_id": customer_id}, limit=limit, order={"date": {"ascending": False}})


def add_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
    t = tx.copy()
    if not t.get("tx_id"):
        # create deterministic tx_id if possible, but fallback to uuid
        tx_id = t.get("tx_id")
        if not tx_id:
            tx_key = f"{t.get('customer_id')}::{t.get('date')}::{t.get('amount')}::{t.get('description') or ''}"
            t["tx_id"] = tx_key
    if not t.get("date"):
        t["date"] = datetime.utcnow().isoformat()
    rows = safe_insert("transactions", t)
    return rows[0] if rows else {}


def get_credit_cards(customer_id: str) -> List[Dict[str, Any]]:
    return safe_select("credit_cards", "*", filters={"customer_id": customer_id})


def add_credit_card(card: Dict[str, Any]) -> Dict[str, Any]:
    c = card.copy()
    if not c.get("card_id"):
        # prefer card_number as card_id if present
        c["card_id"] = c.get("card_id") or c.get("card_number") or str(uuid.uuid4())
    rows = safe_insert("credit_cards", c)
    return rows[0] if rows else {}


def get_loans(customer_id: str) -> List[Dict[str, Any]]:
    return safe_select("loans", "*", filters={"customer_id": customer_id})


def add_loan(loan: Dict[str, Any]) -> Dict[str, Any]:
    l = loan.copy()
    if not l.get("loan_id"):
        l["loan_id"] = str(uuid.uuid4())
    rows = safe_insert("loans", l)
    return rows[0] if rows else {}


def get_latest_rules() -> Optional[Dict[str, Any]]:
    rows = safe_select("rules", "*", limit=1, order={"updated_at": {"ascending": False}})
    return rows[0] if rows else None


def upsert_rules(rules_text: str) -> Dict[str, Any]:
    payload = {"rules_text": rules_text, "updated_at": datetime.utcnow().isoformat()}
    rows = safe_insert("rules", payload)
    return rows[0] if rows else {}


def record_decision(customer_id: str, decision: str, reason: str) -> Dict[str, Any]:
    payload = {
        "customer_id": customer_id,
        "decision": decision,
        "reason": reason,
        "created_at": datetime.utcnow().isoformat()
    }
    rows = safe_insert("loan_decisions", payload)
    return rows[0] if rows else {}


def update_decision_row(decision_id: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = safe_update("loan_decisions", payload, "id", decision_id)
    return rows[0] if rows else {}


def list_decisions(customer_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    filters = {"customer_id": customer_id} if customer_id else None
    rows = safe_select("loan_decisions", "*", filters=filters, limit=limit, order={"created_at": {"ascending": False}})
    return rows


def list_notifications(limit: int = 100) -> List[Dict[str, Any]]:
    return safe_select("notifications", "*", limit=limit, order={"created_at": {"ascending": False}})


def post_notification(title: str, body: str, level: str = "info") -> Dict[str, Any]:
    payload = {"title": title, "body": body, "level": level, "created_at": datetime.utcnow().isoformat()}
    rows = safe_insert("notifications", payload)
    return rows[0] if rows else {}


def get_setting(key: str) -> Optional[Dict[str, Any]]:
    rows = safe_select("settings", "*", filters={"key": key}, limit=1)
    return rows[0] if rows else None


def upsert_setting(key: str, value: Any) -> Dict[str, Any]:
    payload = {"key": key, "value": value, "updated_at": datetime.utcnow().isoformat()}
    rows = safe_insert("settings", payload)
    return rows[0] if rows else {}


# Sessions: in-memory with optional persistence
_sessions_in_memory: Dict[str, List[Dict[str, str]]] = {}
_sessions_history_in_memory: Dict[str, List[List[Dict[str, str]]]] = {}


def save_session_to_db(session_id: str, session_data: List[Dict[str, Any]]):
    payload = {"session_id": session_id, "data": session_data, "updated_at": datetime.utcnow().isoformat()}
    try:
        safe_insert("sessions", payload)
    except Exception:
        pass


def archive_session_in_db(session_id: str):
    pass


# --- Crew/Agent integration: omitted for brevity (same as you had) ---
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
            r = get_latest_rules()
            return r["rules_text"] if r and r.get("rules_text") else DEFAULT_RULES_TEXT

    def build_crew(prompt: str) -> Crew:
        llm = LLM(model="gemini/gemini-2.5-flash", api_key=LLM_API_KEY)
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


# --- API endpoints ---
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/health/full")
def health_full():
    try:
        _ = sb.table("customers").select("customer_id").limit(1).execute()
        return {"status": "ok", "supabase_connected": True}
    except Exception as exc:
        return {"status": "ok", "supabase_connected": False, "error": str(exc)}


# --- Auth (dev) ---
@app.post("/auth", response_model=AuthResponse)
def auth(req: AuthRequest):
    role = req.role.lower()
    if role == "customer":
        if not req.customer_id:
            raise HTTPException(status_code=400, detail="customer_id required for role=customer")
        cust = get_customer(req.customer_id)
        if not cust:
            raise HTTPException(status_code=404, detail="customer not found")
        token = create_token("customer", req.customer_id)
        return {"token": token, "role": "customer", "id": req.customer_id}
    elif role == "admin":
        if not req.email:
            raise HTTPException(status_code=400, detail="email required for admin login")
        token = create_token("admin", req.email)
        return {"token": token, "role": "admin", "id": req.email}
    else:
        raise HTTPException(status_code=400, detail="unknown role")


# --- Customers CRUD & frontend-shaped endpoints ---
@app.get("/customers")
def api_list_customers(limit: int = 100, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    rows = list_customers(limit)
    return {"status": "ok", "customers": rows}


@app.get("/customer/{customer_id}")
def api_get_customer_front(customer_id: str, authorization: Optional[str] = Header(None)):
    """
    Frontend-friendly customer endpoint (public name /customer/{id}).
    Returns customer meta, transactions, credit_cards, loans, decisions.
    """
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    try:
        cust = get_customer(customer_id)
        if not cust:
            raise HTTPException(status_code=404, detail="customer not found")
        txs = get_transactions(customer_id, limit=500)
        cards = get_credit_cards(customer_id)
        loans = get_loans(customer_id)
        decisions = list_decisions(customer_id, limit=100)
        return {"status": "ok", "customer": cust, "transactions": txs, "credit_cards": cards, "loans": loans, "decisions": decisions}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/customer")
def api_create_or_update_customer(payload: Dict[str, Any] = Body(...), authorization: Optional[str] = Header(None)):
    """
    Upsert customer and nested records.
    Expect payload with fields similar to:
    {
      "customer_id": "C101",
      "name": "Alice",
      "email": "...",
      "account_creation_date": "...",
      "credit_cards": [...],
      "loans": [...],
      "transactions": [...]  // optional flat list
    }
    Or you can POST the whole 'customer_accounts' object (array). This endpoint supports both single object and wrapper.
    """
    token_meta = validate_token(authorization)
    if token_meta is None or token_meta.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin token required")

    body = payload
    # support wrapper: {"customer_accounts": [...]} or direct single object
    try:
        if isinstance(body, dict) and "customer_accounts" in body:
            items = body.get("customer_accounts", [])
            results = []
            for cust in items:
                results.append(_upsert_full_customer(cust))
            return {"status": "ok", "imported": results}
        else:
            res = _upsert_full_customer(body)
            return {"status": "ok", "customer": res}
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        raise HTTPException(status_code=500, detail=str(e))


def _upsert_full_customer(cust_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Internal helper: upsert customer, credit_cards (and billing_cycles), loans, transactions.
    """
    cid = cust_obj.get("customer_id") or str(uuid.uuid4())
    # Customer upsert: try select, then update or insert
    existing = safe_select("customers", "*", filters={"customer_id": cid}, limit=1)
    base_payload = {
        "customer_id": cid,
        "name": cust_obj.get("name"),
        "email": cust_obj.get("email"),
        "account_creation_date": cust_obj.get("account_creation_date") or cust_obj.get("account_creation_date")
    }
    if existing:
        safe_update("customers", base_payload, "customer_id", cid)
    else:
        safe_insert("customers", base_payload)

    # credit cards and billing cycles
    for card in cust_obj.get("credit_cards", []):
        # normalize card id
        card_id = card.get("card_number") or card.get("card_id") or str(uuid.uuid4())
        card_payload = {
            "card_id": card_id,
            "card_number": card.get("card_number"),
            "customer_id": cid,
            "credit_limit": card.get("credit_limit"),
            "current_balance": card.get("current_balance"),
        }
        # upsert credit_cards by card_id
        existing_card = safe_select("credit_cards", "*", filters={"card_id": card_id}, limit=1)
        if existing_card:
            safe_update("credit_cards", card_payload, "card_id", card_id)
        else:
            safe_insert("credit_cards", card_payload)

        # billing cycles table (if present)
        for cyc in card.get("billing_cycles", []):
            bc = {
                "card_id": card_id,
                "cycle_start": cyc.get("cycle_start"),
                "cycle_end": cyc.get("cycle_end"),
                "amount_due": cyc.get("amount_due"),
                "amount_paid": cyc.get("amount_paid"),
                "payment_date": cyc.get("payment_date"),
            }
            # check if cycle exists (card_id + cycle_start)
            exists_bc = safe_select("billing_cycles", "*", filters={"card_id": card_id, "cycle_start": bc["cycle_start"]}, limit=1)
            if exists_bc:
                safe_update("billing_cycles", bc, "card_id", card_id)  # update by card_id + cycle_start might not be unique; adapt if needed
            else:
                safe_insert("billing_cycles", bc)

    # loans
    for loan in cust_obj.get("loans", []):
        loan_id = loan.get("loan_id") or str(uuid.uuid4())
        loan_payload = {
            "loan_id": loan_id,
            "customer_id": cid,
            "loan_type": loan.get("loan_type"),
            "principal_amount": loan.get("principal_amount"),
            "outstanding_amount": loan.get("outstanding_amount"),
            "monthly_due": loan.get("monthly_due"),
            "last_payment_date": loan.get("last_payment_date"),
        }
        if safe_select("loans", "*", filters={"loan_id": loan_id}, limit=1):
            safe_update("loans", loan_payload, "loan_id", loan_id)
        else:
            safe_insert("loans", loan_payload)

    # transactions (if provided at customer level)
    for t in cust_obj.get("transactions", []):
        tx_key = f"{cid}::{t.get('date')}::{t.get('amount')}::{t.get('description') or ''}"
        tx_payload = {
            "tx_id": tx_key,
            "customer_id": cid,
            "date": t.get("date"),
            "amount": t.get("amount"),
            "type": t.get("type"),
            "description": t.get("description"),
        }
        if safe_select("transactions", "*", filters={"tx_id": tx_key}, limit=1):
            safe_update("transactions", tx_payload, "tx_id", tx_key)
        else:
            safe_insert("transactions", tx_payload)

    return {"customer_id": cid}


# -----------------------------
# Admin CRUD & "Run Agent"
# -----------------------------
def _require_admin(authorization: Optional[str]):
    token_meta = validate_token(authorization)
    if token_meta is None or token_meta.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin token required")
    return token_meta


@app.get("/admin/customer/{customer_id}")
def admin_get_customer(customer_id: str, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    cust = get_customer(customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="customer not found")
    txs = get_transactions(customer_id, limit=500)
    cards = get_credit_cards(customer_id)
    loans = get_loans(customer_id)
    decisions = list_decisions(customer_id, limit=100)
    return {"status": "ok", "customer": cust, "transactions": txs, "credit_cards": cards, "loans": loans, "decisions": decisions}


@app.put("/admin/customer/{customer_id}")
def admin_update_customer(customer_id: str, payload: Dict[str, Any] = Body(...), authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    allowed = {"name", "email", "account_creation_date"}
    update_payload = {k: v for k, v in payload.items() if k in allowed}
    if not update_payload:
        raise HTTPException(status_code=400, detail=f"no updatable fields provided (allowed: {sorted(list(allowed))})")
    try:
        rows = safe_update("customers", update_payload, "customer_id", customer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to update customer: {e}")
    return {"status": "ok", "updated": rows[0] if rows else None}


@app.post("/admin/customers/{customer_id}/run-agent")
def admin_run_agent_for_customer(customer_id: str, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    if not CREW_AVAILABLE:
        raise HTTPException(status_code=501, detail="Agent integration not available on this server build")
    try:
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
        crew = build_crew(prompt)
        result = crew.kickoff()
        assistant_reply = str(result)
        import json as _json
        parsed = None
        try:
            parsed = _json.loads(assistant_reply)
        except Exception:
            return {"status": "ok", "agent_reply": assistant_reply, "note": "agent output not valid JSON; decision not saved"}
        if isinstance(parsed, dict) and parsed.get("decision") and parsed.get("reason"):
            try:
                saved = record_decision(customer_id, parsed["decision"], parsed["reason"])
            except Exception as e:
                return {"status": "ok", "agent_decision": parsed, "save_error": str(e)}
            return {"status": "ok", "agent_decision": parsed, "saved": saved}
        else:
            return {"status": "ok", "agent_reply": assistant_reply, "note": "agent output did not match expected decision shape"}
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        raise HTTPException(status_code=500, detail=f"failed to run agent: {e}")


# --------------------
# Decisions endpoints
# --------------------
@app.get("/decisions")
def api_get_decisions(customer_id: Optional[str] = Query(None), limit: int = 100, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    try:
        rows = list_decisions(customer_id, limit)
        return {"status": "ok", "decisions": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update-decisions")
def api_update_decision(payload: Dict[str, Any] = Body(...), authorization: Optional[str] = Header(None)):
    """
    Body: { "id": <decision_row_id>, "customer_id": "...", "decision": "APPROVE", "reason":"..." }
    If id provided => update that row; otherwise create new decision record.
    """
    token_meta = validate_token(authorization)
    if token_meta is None or token_meta.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin token required")
    d_id = payload.get("id")
    cust_id = payload.get("customer_id")
    decision = payload.get("decision")
    reason = payload.get("reason", "")
    if not cust_id or not decision:
        raise HTTPException(status_code=400, detail="customer_id and decision required")
    try:
        if d_id:
            updated = update_decision_row(d_id, {"customer_id": cust_id, "decision": decision, "reason": reason})
            return {"status": "ok", "updated": updated}
        else:
            saved = record_decision(cust_id, decision, reason)
            return {"status": "ok", "decision": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------
# Other CRUD endpoints (transactions, credit_cards, loans) - keep as before
# --------------------
@app.post("/transactions")
def api_add_transaction(tx: TransactionIn, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    obj = tx.dict()
    added = add_transaction(obj)
    return {"status": "ok", "transaction": added}


@app.get("/customers/{customer_id}/transactions")
def api_get_transactions(customer_id: str, limit: int = 200, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    txs = get_transactions(customer_id, limit)
    return {"status": "ok", "transactions": txs}


@app.post("/credit_cards")
def api_add_credit_card(card: CreditCardIn, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    added = add_credit_card(card.dict())
    return {"status": "ok", "credit_card": added}


@app.get("/customers/{customer_id}/credit_cards")
def api_get_credit_cards(customer_id: str, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    cards = get_credit_cards(customer_id)
    return {"status": "ok", "credit_cards": cards}


@app.post("/loans")
def api_add_loan(loan: LoanIn, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    added = add_loan(loan.dict())
    return {"status": "ok", "loan": added}


@app.get("/customers/{customer_id}/loans")
def api_get_loans(customer_id: str, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    loans = get_loans(customer_id)
    return {"status": "ok", "loans": loans}


# Rules, notifications, settings (same as before)
@app.get("/rules")
def api_get_rules(authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    r = get_latest_rules()
    if not r:
        return {"status": "ok", "rules_text": DEFAULT_RULES_TEXT}
    return {"status": "ok", "rules_text": r.get("rules_text", DEFAULT_RULES_TEXT)}


@app.post("/rules")
def api_set_rules(payload: Dict[str, Any] = Body(...), authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None or token_meta.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin token required")
    rules_text = payload.get("rules_text")
    if rules_text is None:
        raise HTTPException(status_code=400, detail="rules_text required")
    saved = upsert_rules(rules_text)
    return {"status": "ok", "rules": saved}


@app.get("/notifications")
def api_list_notifications(limit: int = 100, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    data = list_notifications(limit)
    return {"status": "ok", "notifications": data}


@app.post("/notifications")
def api_post_notification(payload: Dict[str, Any] = Body(...), authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None or token_meta.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin token required")
    title = payload.get("title")
    body_text = payload.get("body", "")
    level = payload.get("level", "info")
    if not title:
        raise HTTPException(status_code=400, detail="title required")
    note = post_notification(title, body_text, level)
    return {"status": "ok", "notification": note}


@app.get("/settings/{key}")
def api_get_setting(key: str, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    s = get_setting(key)
    return {"status": "ok", "setting": s}


@app.post("/settings/{key}")
def api_set_setting(key: str, payload: Dict[str, Any] = Body(...), authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None or token_meta.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin token required")
    value = payload.get("value")
    saved = upsert_setting(key, value)
    return {"status": "ok", "setting": saved}


# Sessions endpoints
@app.get("/sessions")
def api_list_sessions(authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    return {
        "active_sessions": [{"session_id": k, "turns": len(v)} for k, v in _sessions_in_memory.items()],
        "archived_sessions_counts": {k: len(v) for k, v in _sessions_history_in_memory.items()},
    }


@app.get("/sessions/{session_id}")
def api_get_session(session_id: str, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    s = _sessions_in_memory.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "turns": s}


@app.post("/sessions/{session_id}/end")
def api_end_session(session_id: str, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    s = _sessions_in_memory.pop(session_id, None)
    if s is None:
        raise HTTPException(status_code=404, detail="session not found")
    _sessions_history_in_memory.setdefault(session_id, []).append(s)
    try:
        save_session_to_db(session_id, s)
    except Exception:
        pass
    return {"status": "archived", "session_id": session_id}


# Chat endpoint (keeps the behavior you had)
@app.post("/chat")
def api_chat(req: ChatRequest, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    require_confirmation = False
    if token_meta and token_meta.get("role") == "customer" and not req.customer_id:
        req.customer_id = token_meta.get("id")
    prompt = req.message
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in _sessions_in_memory:
        _sessions_in_memory[session_id] = []
    _sessions_in_memory[session_id].append({"role": "user", "text": prompt, "time": datetime.utcnow().isoformat()})
    session_text_lines = []
    for turn in _sessions_in_memory[session_id][-20:]:
        role_tag = "USER" if turn.get("role") == "user" else "ASSISTANT"
        session_text_lines.append(f"{role_tag}: {turn.get('text')}")
    combined_context = "\n".join(session_text_lines)

    if req.customer_id and require_confirmation:
        recent_user_msgs = [t["text"].lower() for t in _sessions_in_memory[session_id] if t["role"] == "user"][-3:]
        consent_given = any("yes" in m or "ok" in m or "confirm" in m or "go ahead" in m for m in recent_user_msgs)
        if not consent_given:
            assistant_reply = "I can check your account to evaluate loan eligibility. This will fetch transaction and credit information. Do you want me to proceed? Reply 'yes' to continue."
            _sessions_in_memory[session_id].append({"role": "assistant", "text": assistant_reply, "time": datetime.utcnow().isoformat()})
            return {"reply": assistant_reply, "session_id": session_id, "session_snapshot": _sessions_in_memory.get(session_id)}

    if req.customer_id:
        try:
            cust = get_customer(req.customer_id)
            txs = get_transactions(req.customer_id, limit=50)
            cards = get_credit_cards(req.customer_id)
            loans = get_loans(req.customer_id)
            def redact_card(c: dict):
                card_id = c.get("card_id") or ""
                masked = None
                if card_id:
                    s = str(card_id)
                    masked = ("****" + s[-4:]) if len(s) >= 4 else ("****")
                return {
                    "card_id": c.get("card_id"),
                    "masked_number": masked,
                    "credit_limit": c.get("credit_limit"),
                    "current_balance": c.get("current_balance")
                }
            total_credit_limit = sum((c.get("credit_limit") or 0) for c in cards)
            total_balance = sum((c.get("current_balance") or 0) for c in cards)
            credit_utilization_pct = (total_balance / total_credit_limit * 100) if total_credit_limit else None
            active_loans_count = len([l for l in loans if (l.get("outstanding_amount") or l.get("outstanding") or 0) > 0])
            recent_tx_count = len(txs)
            credits = [t for t in txs if str(t.get("type", "")).lower() == "credit"]
            monthly_income_estimate = None
            if credits:
                try:
                    monthly_income_estimate = max((t.get("amount") or 0) for t in credits)
                except Exception:
                    monthly_income_estimate = None
            account_age_days = None
            try:
                acd = cust.get("account_creation_date")
                if acd:
                    from datetime import datetime as _dt
                    created = _dt.fromisoformat(acd) if isinstance(acd, str) else acd
                    account_age_days = (_dt.utcnow() - created).days
            except Exception:
                account_age_days = None
            summary = {
                "customer_id": cust.get("customer_id"),
                "name": cust.get("name"),
                "account_age_days": account_age_days,
                "monthly_income_estimate": monthly_income_estimate,
                "credit_utilization_pct": round(credit_utilization_pct, 2) if credit_utilization_pct is not None else None,
                "active_loans_count": active_loans_count,
                "recent_tx_count": recent_tx_count,
                "credit_cards": [redact_card(c) for c in cards],
            }
            combined_context += "\n\nCustomerSummary (redacted & derived signals): " + str(summary)
            _sessions_in_memory[session_id].append({
                "role": "system",
                "text": f"Fetched redacted customer summary for {req.customer_id} to evaluate loan eligibility",
                "time": datetime.utcnow().isoformat()
            })
        except Exception:
            combined_context += "\n\nCustomerSummary: unavailable (db read error)"
    else:
        combined_context += "\n\nNote: Customer ID not provided. If you need to check eligibility, please ask the user to provide their Customer ID or to log in. Do not attempt to fetch account data."

    assistant_reply = None
    if CREW_AVAILABLE:
        try:
            crew = build_crew(combined_context)
            result = crew.kickoff()
            assistant_reply = str(result)
            try:
                import json as _json
                parsed = _json.loads(assistant_reply)
                if isinstance(parsed, dict) and parsed.get("decision") and parsed.get("reason") and req.customer_id:
                    try:
                        record_decision(req.customer_id, parsed["decision"], parsed["reason"])
                    except Exception as save_exc:
                        print("Failed to save decision:", save_exc)
            except Exception:
                pass
        except Exception as exc:
            tb = traceback.format_exc()
            print(tb)
            assistant_reply = f"Agent error: {str(exc)}"
    else:
        if req.customer_id:
            assistant_reply = ("Assistant (fallback): I received your message and have access to your account. "
                               "Ask 'check eligibility' to run a basic rules check, or provide more details.")
        else:
            assistant_reply = ("Assistant (fallback): I received your message. I don't know who you are — "
                               "please provide your Customer ID or log in so I can check eligibility.")

    _sessions_in_memory[session_id].append({"role": "assistant", "text": assistant_reply, "time": datetime.utcnow().isoformat()})
    try:
        save_session_to_db(session_id, _sessions_in_memory[session_id])
    except Exception:
        pass
    if req.end_session:
        finished = _sessions_in_memory.pop(session_id, [])
        _sessions_history_in_memory.setdefault(session_id, []).append(finished)
        try:
            archive_session_in_db(session_id)
        except Exception:
            pass
    return {"reply": assistant_reply, "session_id": session_id, "session_snapshot": _sessions_in_memory.get(session_id)}


# Utility: list recent customers (for quick frontend)
@app.get("/customers/recent")
def api_customers_recent(limit: int = 50, authorization: Optional[str] = Header(None)):
    token_meta = validate_token(authorization)
    if token_meta is None:
        raise HTTPException(status_code=403, detail="token required")
    rows = list_customers(limit)
    return {"status": "ok", "customers": rows}


# API status indicator
@app.get("/api-status")
def api_status(authorization: Optional[str] = Header(None)):
    # optionally restrict this to authorized users; we'll allow any token in dev
    try:
        # quick supabase connectivity test
        try:
            sb.table("customers").select("customer_id").limit(1).execute()
            supabase_connected = True
        except Exception:
            supabase_connected = False
        counts = {}
        # get approximate counts for a few tables (best-effort)
        for t in ("customers", "transactions", "credit_cards", "loans", "loan_decisions"):
            try:
                # a cheap way: request one record and rely on success as indicator
                _ = sb.table(t).select("id").limit(1).execute()
                counts[t] = "reachable"
            except Exception:
                counts[t] = "unreachable"
        return {
            "status": "ok",
            "time": datetime.utcnow().isoformat(),
            "supabase_connected": supabase_connected,
            "table_reachability": counts
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# End of file
