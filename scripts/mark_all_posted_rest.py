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


def list_all_events(token: str) -> list:
    """Все события из коллекции events."""
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents:runQuery"
    body = {"structuredQuery": {"from": [{"collectionId": "events"}], "limit": 1000}}
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        results = json.loads(r.read())
    return [r["document"] for r in results if "document" in r]


def mark_all_posted(token: str, doc_name: str, fields: list):
    """PATCH документа — выставляем нужные флаги."""
    mask = "&".join(f"updateMask.fieldPaths={f}" for f in fields)
    url = f"https://firestore.googleapis.com/v1/{doc_name}?{mask}"
    body = {"fields": {f: {"booleanValue": True} for f in fields}}
    firestore_patch(token, url, body)


def main():
    print("Получаем токен...")
    try:
        token = get_access_token()
    except ImportError:
        print("Нужна библиотека cryptography: pip install cryptography")
        sys.exit(1)
    print("Токен получен.")

    print("Загружаем все события...")
    docs = list_all_events(token)
    total = len(docs)
    print(f"Найдено: {total}")

    if total == 0:
        print("События не найдены.")
        return

    confirm = input(f"Пометить все {total} событий как posted_tg=True И posted_tg_en=True? [y/N] ").strip().lower()
    if confirm != "y":
        print("Отменено.")
        return

    for i, doc in enumerate(docs, 1):
        name = doc["name"]
        fields_to_set = []
        existing = doc.get("fields", {})
        if not existing.get("posted_tg", {}).get("booleanValue"):
            fields_to_set.append("posted_tg")
        if not existing.get("posted_tg_en", {}).get("booleanValue"):
            fields_to_set.append("posted_tg_en")
        if fields_to_set:
            try:
                mark_all_posted(token, name, fields_to_set)
            except Exception as e:
                print(f"  Ошибка {name.split('/')[-1]}: {e}")
        if i % 50 == 0 or i == total:
            print(f"  {i}/{total}")

    print(f"\nГотово. {total} событий помечено.")

if __name__ == "__main__":
    main()
