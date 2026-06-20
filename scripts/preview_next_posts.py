"""
Показывает следующие 5 постов которые пойдут в @WrPtCy — без отправки.
Запуск: railway run --service pacific-forgiveness python3 scripts/preview_next_posts.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from scripts.mark_all_posted_rest import get_access_token

PROJECT_ID = "whereparty-88938"
import urllib.request

def query_unposted(token, limit=5):
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents:runQuery"
    body = {
        "structuredQuery": {
            "from": [{"collectionId": "events"}],
            "where": {"fieldFilter": {
                "field": {"fieldPath": "posted_tg"},
                "op": "EQUAL",
                "value": {"booleanValue": False}
            }},
            "limit": limit,
        }
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def fv(fields, key):
    f = fields.get(key, {})
    return (f.get("stringValue") or f.get("booleanValue") or
            f.get("integerValue") or f.get("doubleValue") or "")

token = get_access_token()
results = query_unposted(token, limit=5)
docs = [r["document"] for r in results if "document" in r]

print(f"Следующих постов в очереди: {len(docs)}\n{'='*60}")

for i, doc in enumerate(docs, 1):
    f = doc.get("fields", {})
    title = fv(f, "title")
    date = fv(f, "date")
    city = fv(f, "city")
    url = fv(f, "url")
    photo = fv(f, "photo_url")
    desc = fv(f, "full_text")

    print(f"\n── ПОСТ {i} {'─'*40}")
    print(f"Заголовок: {title}")
    print(f"Дата:      {date}")
    print(f"Город:     {city}")
    print(f"Фото:      {photo or '—'}")
    print(f"URL:       {url or '—'}")
    if desc:
        print(f"Текст:     {desc[:200]}...")
    print()
