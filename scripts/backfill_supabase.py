"""
Одноразовый бэкфилл: все события из Firestore -> Supabase (WR PT app).
Работает локально на Python 3.14 через REST API (без firebase_admin).

Запуск:
  FIREBASE_SERVICE_ACCOUNT_JSON='...' SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
    python3 scripts/backfill_supabase.py
"""
import os, sys, json, time
import urllib.request
import urllib.error
import urllib.parse
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ID = "whereparty-88938"


def get_access_token() -> str:
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON не задан")
    sa = json.loads(sa_json)

    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=")
    now = int(time.time())
    claim = base64.urlsafe_b64encode(json.dumps({
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/datastore",
        "aud": "https://oauth2.googleapis.com/token",
        "exp": now + 3600,
        "iat": now,
    }).encode()).rstrip(b"=")
    msg = header + b"." + claim

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    private_key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    sig = private_key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
    jwt = (msg + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()

    data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt,
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["access_token"]


def _fs_value(v: dict):
    """Firestore REST value -> python."""
    if "stringValue" in v: return v["stringValue"]
    if "booleanValue" in v: return v["booleanValue"]
    if "integerValue" in v: return int(v["integerValue"])
    if "doubleValue" in v: return v["doubleValue"]
    if "nullValue" in v: return None
    if "timestampValue" in v: return v["timestampValue"]
    return None


def fetch_all_events(token: str) -> list[dict]:
    events = []
    page_token = ""
    base = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/events?pageSize=300"
    while True:
        url = base + (f"&pageToken={page_token}" if page_token else "")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        for doc in data.get("documents", []):
            fields = doc.get("fields", {})
            ev = {k: _fs_value(v) for k, v in fields.items()}
            if "id" not in ev or not ev["id"]:
                ev["id"] = doc["name"].rsplit("/", 1)[-1]
            events.append(ev)
        page_token = data.get("nextPageToken", "")
        if not page_token:
            break
    return events


def main():
    token = get_access_token()
    events = fetch_all_events(token)
    print(f"Из Firestore получено: {len(events)}")

    from sync_supabase import sync_to_supabase
    sync_to_supabase(events)


if __name__ == "__main__":
    main()
