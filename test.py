# test_supabase_inspect.py
import os
from supabase import create_client
from pprint import pprint

# Hardcode your real values while debugging (or rely on env vars)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://fqshgmyiegbifhbwapve.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_secret_n_-wuGWjL8cj08pXbUN25w_hGQ7Ql2E")

print("Using SUPABASE_URL:", SUPABASE_URL)
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# Perform a simple select
resp = sb.table("customers").select("customer_id").limit(1).execute()

# Print a safe inspection of the response object
print("\n--- raw response repr ---")
print(repr(resp))

print("\n--- dir(resp) ---")
pprint([x for x in dir(resp) if not x.startswith("_")])

print("\n--- attempt to print common attributes ---")
# common attribute names across versions: data, status_code, status, error, errors
for attr in ("data", "status_code", "status", "error", "errors", "count"):
    val = getattr(resp, attr, None)
    print(f"{attr}: {val!r}")

# If the client returns something like a dict inside .__dict__, show that too
print("\n--- resp.__dict__ ---")
try:
    pprint(resp.__dict__)
except Exception as e:
    print("cannot access __dict__:", e)

# Finally, print the data if present using the most-likely attribute names
data = getattr(resp, "data", None)
if data is None:
    # some versions return a tuple or an object with .get("data")
    try:
        data = resp.get("data")  # if resp supports .get
    except Exception:
        data = None

print("\n--- interpreted data (None means empty) ---")
pprint(data)
