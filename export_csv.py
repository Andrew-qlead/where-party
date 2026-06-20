"""
Экспорт всех событий из Firebase в CSV.
Запуск: python3 export_csv.py
Файл сохраняется на рабочий стол.
"""
import os
import csv
from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore

OUTPUT = os.path.expanduser("~/Desktop/WhereParty/events_export.csv")

def main():
    sa_path = "data/serviceAccount.json"
    if not firebase_admin._apps:
        cred = credentials.Certificate(sa_path)
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    docs = db.collection("events").order_by("created_at", direction=firestore.Query.DESCENDING).stream()

    rows = []
    for doc in docs:
        d = doc.to_dict()
        rows.append({
            "id": doc.id,
            "title": d.get("title", ""),
            "category": d.get("category", ""),
            "date": d.get("date", ""),
            "venue": d.get("venue", ""),
            "city": d.get("city", ""),
            "price": d.get("price", ""),
            "url": d.get("url", ""),
            "source": d.get("source", ""),
            "created_at": d.get("created_at", ""),
            "posted_tg": d.get("posted_tg", False),
            "posted_threads": d.get("posted_threads", False),
            "posted_instagram": d.get("posted_instagram", False),
        })

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Экспортировано {len(rows)} событий → {OUTPUT}")

if __name__ == "__main__":
    main()
