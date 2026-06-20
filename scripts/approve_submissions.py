"""
Одобрение заявок из Firestore collection 'submissions'.

Запуск: python scripts/approve_submissions.py

Показывает список неодобренных заявок. На каждую:
  y — одобрить (переносит в events, ставит approved=True)
  n — пропустить
  d — удалить
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from db.firebase import get_db
from db.categorizer import categorize
from datetime import datetime, timezone

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())[:40]

def approve_submission(db, sub_ref, sub: dict):
    eid = f"submit_{slugify(sub.get('title','x'))}_{int(datetime.now().timestamp())}"
    event = {
        "id": eid,
        "title": sub.get("title", ""),
        "title_en": sub.get("title", ""),
        "full_text": sub.get("full_text", ""),
        "full_text_en": sub.get("full_text", ""),
        "date": sub.get("date", ""),
        "venue": sub.get("venue", ""),
        "city": sub.get("city", "Cyprus"),
        "url": sub.get("url", ""),
        "price": sub.get("price", ""),
        "photo_url": sub.get("photo_url", ""),
        "category": sub.get("category") or categorize(sub),
        "source": "user_submission",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "posted_tg": False,
        "posted_threads": False,
        "posted_instagram": False,
    }
    db.collection("events").document(eid).set(event)
    sub_ref.update({"approved": True, "event_id": eid})
    print(f"  ✓ Одобрено → events/{eid}")

def main():
    db = get_db()
    docs = list(db.collection("submissions").where("approved", "==", False).order_by("created_at").stream())
    if not docs:
        print("Нет заявок для одобрения.")
        return

    print(f"\n{'='*60}")
    print(f"Заявок на одобрение: {len(docs)}")
    print(f"{'='*60}\n")

    for doc in docs:
        sub = doc.to_dict()
        print(f"Заголовок : {sub.get('title','—')}")
        print(f"Дата      : {sub.get('date','—')}  {sub.get('time','')}")
        print(f"Город     : {sub.get('city','—')} | Категория: {sub.get('category','—')}")
        print(f"Место     : {sub.get('venue','—')}")
        print(f"URL       : {sub.get('url','—')}")
        print(f"Цена      : {sub.get('price','—')}")
        print(f"Описание  : {(sub.get('full_text','') or '')[:120]}...")
        print(f"Контакт   : {sub.get('contact','—')}")
        print()

        ans = input("  [y] одобрить  [n] пропустить  [d] удалить  > ").strip().lower()
        if ans == "y":
            approve_submission(db, doc.reference, sub)
        elif ans == "d":
            doc.reference.delete()
            print("  ✗ Удалено")
        else:
            print("  — Пропущено")
        print()

    print("Готово.")

if __name__ == "__main__":
    main()
