# supadb.py
import os
from typing import Any, Dict, List, Optional
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY environment variables (use https://<project>.supabase.co and the secret key).")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def _normalize_resp(resp: Any, table: str = "<unknown>") -> List[Dict[str, Any]]:
    """
    Normalize Supabase APIResponse to a plain Python list of rows.
    Raises RuntimeError if response shape is unexpected or request failed.
    """
    # common pydantic APIResponse exposes .data
    data = getattr(resp, "data", None)
    if data is not None:
        return data

    # fallback: dict-like
    try:
        if isinstance(resp, dict) and "data" in resp:
            return resp["data"]
    except Exception:
        pass

    # fallback: resp.get("data")
    try:
        getter = getattr(resp, "get", None)
        if callable(getter):
            d = resp.get("data")
            if d is not None:
                return d
    except Exception:
        pass

    # if the server returned an error, the client may have thrown an exception already.
    raise RuntimeError(f"Unexpected supabase response for table '{table}': {repr(resp)}")


# safe select helper
def safe_select(table: str, select: str = "*", filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, order: Optional[Dict[str, Any]] = None):
    try:
        q = sb.table(table).select(select)
        if filters:
            for k, v in filters.items():
                if v is None:
                    continue
                q = q.eq(k, v)
        if order:
            # order example: {"column": "date", "ascending": False} or {"date": {"ascending":False}} depending usage
            # support both simple dict forms:
            if isinstance(order, dict):
                # try the simple pattern used in scripts: {"date": {"ascending": False}}
                for col, opts in order.items():
                    if isinstance(opts, dict):
                        asc = opts.get("ascending", True)
                        q = q.order(col, {"ascending": asc})
                    else:
                        # order={"column":"date","ascending":False}
                        pass
        if limit:
            q = q.limit(limit)
        resp = q.execute()
    except Exception as e:
        raise RuntimeError(f"Supabase request failed for table '{table}': {e}")
    return _normalize_resp(resp, table)


# safe insert/update wrappers (return inserted/updated row or list)
def safe_insert(table: str, payload: Any):
    try:
        resp = sb.table(table).insert(payload).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase insert failed for '{table}': {e}")
    rows = _normalize_resp(resp, table)
    return rows

def safe_update(table: str, payload: Any, eq_key: str, eq_val: Any):
    try:
        resp = sb.table(table).update(payload).eq(eq_key, eq_val).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase update failed for '{table}': {e}")
    rows = _normalize_resp(resp, table)
    return rows
# supadb.py
import os
from typing import Any, Dict, List, Optional
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY environment variables (use https://<project>.supabase.co and the secret key).")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


def _normalize_resp(resp: Any, table: str = "<unknown>") -> List[Dict[str, Any]]:
    """
    Normalize Supabase APIResponse to a plain Python list of rows.
    Raises RuntimeError if response shape is unexpected or request failed.
    """
    # common pydantic APIResponse exposes .data
    data = getattr(resp, "data", None)
    if data is not None:
        return data

    # fallback: dict-like
    try:
        if isinstance(resp, dict) and "data" in resp:
            return resp["data"]
    except Exception:
        pass

    # fallback: resp.get("data")
    try:
        getter = getattr(resp, "get", None)
        if callable(getter):
            d = resp.get("data")
            if d is not None:
                return d
    except Exception:
        pass

    # if the server returned an error, the client may have thrown an exception already.
    raise RuntimeError(f"Unexpected supabase response for table '{table}': {repr(resp)}")


# safe select helper
def safe_select(table: str, select: str = "*", filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, order: Optional[Dict[str, Any]] = None):
    try:
        q = sb.table(table).select(select)
        if filters:
            for k, v in filters.items():
                if v is None:
                    continue
                q = q.eq(k, v)
        if order:
            # order example: {"column": "date", "ascending": False} or {"date": {"ascending":False}} depending usage
            # support both simple dict forms:
            if isinstance(order, dict):
                # try the simple pattern used in scripts: {"date": {"ascending": False}}
                for col, opts in order.items():
                    if isinstance(opts, dict):
                        asc = opts.get("ascending", True)
                        q = q.order(col, {"ascending": asc})
                    else:
                        # order={"column":"date","ascending":False}
                        pass
        if limit:
            q = q.limit(limit)
        resp = q.execute()
    except Exception as e:
        raise RuntimeError(f"Supabase request failed for table '{table}': {e}")
    return _normalize_resp(resp, table)


# safe insert/update wrappers (return inserted/updated row or list)
def safe_insert(table: str, payload: Any):
    try:
        resp = sb.table(table).insert(payload).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase insert failed for '{table}': {e}")
    rows = _normalize_resp(resp, table)
    return rows

def safe_update(table: str, payload: Any, eq_key: str, eq_val: Any):
    try:
        resp = sb.table(table).update(payload).eq(eq_key, eq_val).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase update failed for '{table}': {e}")
    rows = _normalize_resp(resp, table)
    return rows

# --- Loan Decisions ---

def record_decision(customer_id: str, decision: str, reason: str):
    payload = {
        "customer_id": customer_id,
        "decision": decision,
        "reason": reason
    }
    rows = safe_insert("loan_decisions", payload)
    return rows[0] if rows else None


def list_decisions(customer_id: Optional[str] = None, limit: int = 50):
    filters = {}
    if customer_id:
        filters["customer_id"] = customer_id
    rows = safe_select(
        "loan_decisions",
        "*",
        filters=filters,
        order={"created_at": {"ascending": False}},
        limit=limit
    )
    return rows
