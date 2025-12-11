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
from io import StringIO
import csv
import html

load_dotenv()

BANK_STATEMENTS_FILE = "bank_statements.json"
CREDITS_LOAN_FILE = "credits_loan.json"
DECISIONS_FILE = "decisions.json"

if not os.path.exists(DECISIONS_FILE):
    with open(DECISIONS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)

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
    all_dec = _load_decisions()
    if customer_id:
        filtered = [d for d in all_dec if d.get("customer_id") == customer_id]
    else:
        filtered = all_dec
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

def reload_sources():
    return {
        "bank_statements_count": len(_load_bank_statements()),
        "customer_accounts_count": len(_load_customer_accounts()),
        "decisions_count": len(_load_decisions()),
    }

try:
    from crewai import Agent, Crew, LLM, Task
    from crewai.tools import BaseTool
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
        name:str = "UpdateDecisionTool"
        description:str = "Update the decision of customer id "
        def _run(self,customer_id:str,decision:str,reason:str):
            with open(DECISIONS_FILE) as f:
                data = json.load(f)
                for i in data:
                    if i["customer_id"] == customer_id:
                        pass




    def build_crew(prompt: str, role: str = "customer", tools: Optional[List[BaseTool]] = None) -> Crew:
        llm = LLM(model="gemini/gemini-2.5-flash", api_key=LLM_API_KEY) if LLM_API_KEY else LLM()
        
        if role == "admin":
            tool_list = [FetchdecTool(),FetchTool()]
            agent_goal = f"Provide answers and all requested details in a clean, comprehensive, professional format based on the prompt: '{prompt}'. Always use FetchDecisions tool if the request is about decisions."
            agent_backstory = "Expert in providing comprehensive analysis and detailed data access to administrators. You have full access to all historical decisions via the FetchDecisions tool."
            task_description = (
                "You are operating in Admin mode. Answer questions and accomplish the task using the available tools as the answer "
                "Use the FetchDecisions tool to fetch all decisions. Parse the JSON output from the tool and **format the result ONLY as a clean, structured Markdown table** (including ID, Customer ID, Decision, and Reason). **Do not include any text, headers, or footers before or after the table**. "  
                "Provide all details for the admin in a clean, structured format."
            )
            expected_output = "A sentence with clean Markdown table showing all decisions, or the required JSON object for evaluation, or a professional, detailed answer."
        else:
            tool_list = [FetchTool(), RulesTool()]
            agent_goal = f"Provide details and chats in a friendly way and accomplish the task in '{prompt}'"
            agent_backstory = "Expert in answering customer questions, providing friendly explanations, and completing the right task using the right tool. You have access to the customer's summary and profile when a customer_id is set. You CANNOT access other customer's data."
            task_description = (
                "Chat with the user in a friendly manner. "
                "Answer questions and accomplish the task using the available tools. "
                "Use the RulesProvider to fetch decision rules when an eligibility check is requested. "
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
_sessions_history_in_memory: Dict[str, List[List[Dict[str, Any]]]] = {}

def _get_customer_name(customer_id: Optional[str]) -> str:
    if not customer_id:
        return "(Unknown Customer)"
    cust = get_customer(customer_id)
    if not cust:
        return "(Unknown Customer)"
    return cust.get("name") or "(Unknown Customer)"

def _escape_pipe(text: str) -> str:
    return str(text).replace("|", "\\|")

def _decisions_to_markdown_table(decisions: List[Dict[str, Any]]) -> str:
    headers = ["ID", "Customer ID", "Customer Name", "Decision", "Reason", "Created At"]
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for d in decisions:
        row = [
            _escape_pipe(d.get("id", "")),
            _escape_pipe(d.get("customer_id", "")),
            _escape_pipe(d.get("customer_name", "")),
            _escape_pipe(d.get("decision", "")),
            _escape_pipe(d.get("reason", "")),
            _escape_pipe(d.get("created_at", "")),
        ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)

def _decisions_to_csv(decisions: List[Dict[str, Any]]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "customer_id", "customer_name", "decision", "reason", "created_at"])
    for d in decisions:
        writer.writerow([d.get("id",""), d.get("customer_id",""), d.get("customer_name",""), d.get("decision",""), d.get("reason",""), d.get("created_at","")])
    return output.getvalue()

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

@app.get("/decisions")
def api_get_decisions(customer_id: Optional[str] = Query(None), limit: int = 100, format: str = Query("table")):
    rows = list_decisions(customer_id, limit)

    structured = []
    for d in rows:
        cid = d.get("customer_id")
        structured.append({
            "id": d.get("id"),
            "customer_id": cid,
            "customer_name": _get_customer_name(cid),
            "decision": d.get("decision"),
            "reason": d.get("reason"),
            "created_at": d.get("created_at")
        })

    structured = sorted(structured, key=lambda x: x.get("created_at",""), reverse=True)

    fmt = (format or "table").lower()
    if fmt == "json":
        return {"status": "ok", "format": "json", "decisions": structured}
    elif fmt == "csv":
        csv_text = _decisions_to_csv(structured)
        return {"status": "ok", "format": "csv", "csv": csv_text, "decisions": structured}
    else:
        md_table = _decisions_to_markdown_table(structured)
        html_table = "<pre>" + html.escape(md_table) + "</pre>"
        return {"status": "ok", "format": "table", "table": md_table, "table_html_pre": html_table, "decisions": structured}

@app.post("/update-decisions")
def api_update_decision(payload: Dict[str, Any] = Body(...)):
    cust_id = payload.get("customer_id")
    decision = payload.get("decision")
    reason = payload.get("reason", "")
    if not cust_id or not decision:
        raise HTTPException(status_code=400, detail="customer_id and decision required")
    saved = record_decision(cust_id, decision, reason)
    return {"status": "ok", "decision": saved}

@app.post("/chat")
def api_chat(req: ChatRequest):
    prompt = req.message
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in _sessions_in_memory:
        _sessions_in_memory[session_id] = []
    _sessions_in_memory[session_id].append({"role": "user", "text": prompt, "time": datetime.utcnow().isoformat()})

    combined_context = "\n".join([f"{t['role'].upper()}: {t['text']}" for t in _sessions_in_memory[session_id][-20:]])

    if not req.customer_id and req.role != "admin":
        admin_keywords = ["all customer", "all decisions", "all users", "full data", "admin"]
        if any(keyword in prompt.lower() for keyword in admin_keywords):
            req.role = "admin"

    if req.customer_id and req.role == "customer":
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
            combined_context += "\n- Loans: " + json.dumps(loans, indent=2)

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
        f"Admin request: Evaluate loan eligibility for customer {customer_id} using the following data and rules.",
        DEFAULT_RULES_TEXT,
        "Customer Data:",
        f"Customer Profile: {json.dumps(cust, indent=2)}",
        f"Credit Cards: {json.dumps(cards, indent=2)}",
        f"Loans: {json.dumps(loans, indent=2)}",
        f"Recent Transactions (top 50): {json.dumps(txs[:50], indent=2)}",
        "Return EXACTLY a JSON object: {\"decision\":\"APPROVE|REVIEW|REJECT\",\"reason\":\"...\"} and NOTHING else."
    ]
    prompt = "\n\n".join(prompt_parts)
    try:
        llm = LLM(model="gemini/gemini-2.5-flash", api_key=LLM_API_KEY) if LLM_API_KEY else LLM()
        
        admin_agent = Agent(
            role="Loan Eligibility Evaluator",
            goal="Analyze the provided customer data against the default rules and return a strict JSON decision.",
            backstory="A specialized, rules-driven expert for rapid credit evaluation, operating under strict protocol.",
            tools=[],
            llm=llm,
        )
        
        admin_task = Task(
            description=f"Strictly evaluate the customer's data against the decision rules provided in the prompt. {prompt}",
            expected_output="A single JSON object: {\"decision\":\"APPROVE|REVIEW|REJECT\",\"reason\":\"string\"}",
            agent=admin_agent,
        )
        
        crew = Crew(agents=[admin_agent], tasks=[admin_task], verbose=False)
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

# Updated Pydantic Models to handle floats from frontend

class BillingCycle(BaseModel):
    cycle_start: str
    cycle_end: str
    amount_due: float      # Changed from implicit strict check to float
    amount_paid: float     # Changed from implicit strict check to float
    payment_date: str

class CreditCard(BaseModel):
    card_number: str
    credit_limit: float    # Changed from int to float
    current_balance: float # Changed from int to float
    billing_cycles: List[BillingCycle] # Better validation than just 'list'

class Loan(BaseModel):
    loan_id: str
    loan_type: str
    principal_amount: float     # Changed from int to float
    outstanding_amount: float   # Changed from int to float
    monthly_due: float          # Changed from int to float
    last_payment_date: str

class Transaction(BaseModel):
    date: str
    amount: float          # Changed from int to float
    type: str
    description: str

class customerdata(BaseModel):
    customer_id: str
    account_creation_date: Optional[str] = None
    name: Optional[str] = None
    # Ensure these are typed as Lists of the models above
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