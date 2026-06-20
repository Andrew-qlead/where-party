"""
Помечает все события с posted_tg=False как True.
Использует Firestore REST API — работает на Python 3.14.
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

import urllib.request
import urllib.error

PROJECT_ID = "whereparty-88938"

def get_access_token() -> str:
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        path = "data/serviceAccount.json"
        if os.path.exists(path):
            with open(path) as f:
                sa_json = f.read()
    if not sa_json:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON не задан")

    sa = json.loads(sa_json)
    import urllib.parse
    import hmac, hashlib, base64

    # JWT для Google OAuth2
    import json as _json
    header = base64.urlsafe_b64encode(_json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
    now = int(time.time())
    claim = base64.urlsafe_b64encode(_json.dumps({
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/datastore",
        "aud": "https://oauth2.googleapis.com/token",
        "exp": now + 3600,
        "iat": now,
    }).encode()).rstrip(b"=")

    msg = header + b"." + claim

    # Подписываем RSA SHA256
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend

    key_pem = sa["private_key"].encode()
    private_key = serialization.load_pem_private_key(key_pem, password=None, backend=default_backend())
    sig = private_key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=")
    jwt = (msg + b"." + sig_b64).decode()

    # Обмениваем JWT на токен
    data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt,
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["access_token"]


def firestore_get(token: str, url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def firestore_patch(token: str, url: str, body: dict):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"


def list_unposted(token: str) -> list:
    """Получаем все documents где posted_tg=False через runQuery."""
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents:runQuery"
    body = {
        "structuredQuery": {
            "from": [{"collectionId": "events"}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": "posted_tg"},
                    "op": "EQUAL",
                    "value": {"booleanValue": False}
                }
            },
            "limit": 500,
        }
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        results = json.loads(r.read())
    docs = [r["document"] for r in results if "document" in r]
    return docs


def mark_posted(token: str, doc_name: str):
    """PATCH одного документа — выставляем posted_tg=True."""
    url = f"https://firestore.googleapis.com/v1/{doc_name}?updateMask.fieldPaths=posted_tg"
    body = {
        "fields": {
            "posted_tg": {"booleanValue": True}
        }
    }
    firestore_patch(token, url, body)


def main():
    print("Получаем токен...")
    try:
        token = get_access_token()
    except ImportError:
        print("Нужна библиотека cryptography: pip install cryptography")
        sys.exit(1)
    print("Токен получен.")

    print("Загружаем события с posted_tg=False...")
    docs = list_unposted(token)
    total = len(docs)
    print(f"Найдено: {total}")

    if total == 0:
        print("Всё уже помечено!")
        return

    confirm = input(f"Пометить все {total} как posted_tg=True? [y/N] ").strip().lower()
    if confirm != "y":
        print("Отменено.")
        return

    for i, doc in enumerate(docs, 1):
        name = doc["name"]
        try:
            mark_posted(token, name)
            if i % 50 == 0 or i == total:
                print(f"  {i}/{total}")
        except Exception as e:
            print(f"  Ошибка {name.split('/')[-1]}: {e}")

    print(f"\nГотово. {total} событий помечено как posted_tg=True.")

if __name__ == "__main__":
    main()
