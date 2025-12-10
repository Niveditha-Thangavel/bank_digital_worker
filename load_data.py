# load_data.py
import os
import json
import uuid
from pprint import pprint
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

import supadb  # local helper above

# helpers
def make_tx_id(customer_id: str, date: str, amount: Any, description: Optional[str]) -> str:
    return f"{customer_id}::{date}::{amount}::{(description or '').strip()}"

def ensure_tables_access():
    try:
        rows = supadb.safe_select("customers", "*", limit=1)
        # success even if empty
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to access 'customers' table. Ensure tables exist and env vars are correct. ({e})")

def upsert_customer(customer: Dict[str, Any]) -> Dict[str, Any]:
    cid = customer.get("customer_id") or str(uuid.uuid4())
    customer["customer_id"] = cid
    existing = supadb.safe_select("customers", "*", filters={"customer_id": cid}, limit=1)
    if existing:
        # update minimal fields
        payload = {
            "name": customer.get("name"),
            "account_creation_date": customer.get("account_creation_date")
        }
        rows = supadb.safe_update("customers", payload, "customer_id", cid)
        return rows[0] if rows else {}
    else:
        rows = supadb.safe_insert("customers", {
            "customer_id": cid,
            "name": customer.get("name"),
            "account_creation_date": customer.get("account_creation_date")
        })
        return rows[0] if rows else {}

def upsert_credit_card(customer_id: str, card: Dict[str, Any]) -> Dict[str, Any]:
    card_id = card.get("card_number") or card.get("card_id") or str(uuid.uuid4())
    payload = {
        "card_id": card_id,
        "customer_id": customer_id,
        "credit_limit": card.get("credit_limit") or 0,
        "current_balance": card.get("current_balance") or 0
    }
    existing = supadb.safe_select("credit_cards", "*", filters={"card_id": card_id}, limit=1)
    if existing:
        rows = supadb.safe_update("credit_cards", payload, "card_id", card_id)
        inserted = rows[0] if rows else {}
    else:
        rows = supadb.safe_insert("credit_cards", payload)
        inserted = rows[0] if rows else {}

    # billing cycles
    for cyc in card.get("billing_cycles", []):
        bc = {
            "card_id": card_id,
            "cycle_start": cyc.get("cycle_start"),
            "cycle_end": cyc.get("cycle_end"),
            "amount_due": cyc.get("amount_due"),
            "amount_paid": cyc.get("amount_paid"),
            "payment_date": cyc.get("payment_date"),
        }
        exists = supadb.safe_select("billing_cycles", "*", filters={"card_id": card_id, "cycle_start": bc["cycle_start"]}, limit=1)
        if exists:
            supadb.safe_update("billing_cycles", bc, "card_id", card_id)  # updates many rows if ambiguous, but we filtered on cycle_start as well earlier
        else:
            supadb.safe_insert("billing_cycles", bc)

    return inserted

def upsert_loan(customer_id: str, loan: Dict[str, Any]) -> Dict[str, Any]:
    loan_id = loan.get("loan_id") or str(uuid.uuid4())
    payload = {
        "loan_id": loan_id,
        "customer_id": customer_id,
        "loan_type": loan.get("loan_type"),
        "principal_amount": loan.get("principal_amount"),
        "outstanding_amount": loan.get("outstanding_amount"),
        "monthly_due": loan.get("monthly_due"),
        "last_payment_date": loan.get("last_payment_date"),
    }
    existing = supadb.safe_select("loans", "*", filters={"loan_id": loan_id}, limit=1)
    if existing:
        rows = supadb.safe_update("loans", payload, "loan_id", loan_id)
        return rows[0] if rows else {}
    else:
        rows = supadb.safe_insert("loans", payload)
        return rows[0] if rows else {}

def insert_transactions_for_customer(customer_id: str, transactions: List[Dict[str, Any]]) -> int:
    inserted = 0
    for t in transactions:
        tx_id = make_tx_id(customer_id, t.get("date"), t.get("amount"), t.get("description"))
        exists = supadb.safe_select("transactions", "*", filters={"tx_id": tx_id}, limit=1)
        if exists:
            continue
        payload = {
            "tx_id": tx_id,
            "customer_id": customer_id,
            "date": t.get("date"),
            "amount": t.get("amount"),
            "type": t.get("type"),
            "description": t.get("description"),
        }
        supadb.safe_insert("transactions", payload)
        inserted += 1
    return inserted

# top-level loaders
def load_customer_accounts(customer_accounts: List[Dict[str, Any]]):
    summary = {"customers": 0, "cards": 0, "billing_cycles": 0, "loans": 0}
    for cust in customer_accounts:
        cid = cust.get("customer_id") or str(uuid.uuid4())
        upsert_customer(cust)
        summary["customers"] += 1
        for card in cust.get("credit_cards", []):
            upsert_credit_card(cid, card)
            summary["cards"] += 1
            summary["billing_cycles"] += len(card.get("billing_cycles", []))
        for loan in cust.get("loans", []):
            upsert_loan(cid, loan)
            summary["loans"] += 1
    return summary

def load_bank_statements(statements: List[Dict[str, Any]]):
    summary = {"customers": 0, "transactions_inserted": 0}
    for rec in statements:
        cid = rec.get("customer_id")
        cnt = insert_transactions_for_customer(cid, rec.get("transactions", []))
        summary["customers"] += 1
        summary["transactions_inserted"] += cnt
    return summary

def main():
    # check env variables
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_KEY environment variables (https://<project>.supabase.co and secret key).")

    # ensure tables accessible
    try:
        ensure_tables_access()
    except Exception as e:
        raise SystemExit(f"Table access check failed: {e}")

    base = os.path.dirname(__file__)
    cust_file = os.path.join(base, "credits_loan.json")
    stmt_file = os.path.join(base, "bank_statements.json")

    if not os.path.exists(cust_file) or not os.path.exists(stmt_file):
        raise SystemExit("Place credits_loan.json and bank_statements.json in the script folder and re-run.")

    with open(cust_file, "r", encoding="utf-8") as f:
        cust_data = json.load(f)

    with open(stmt_file, "r", encoding="utf-8") as f:
        stmt_data = json.load(f)

    print("Loading customers / credit-cards / loans ...")
    s1 = load_customer_accounts(cust_data.get("customer_accounts", []))
    pprint(s1)

    print("Loading bank statements / transactions ...")
    s2 = load_bank_statements(stmt_data.get("bank_statements", []))
    pprint(s2)

    print("Done.")

if __name__ == "__main__":
    main()
