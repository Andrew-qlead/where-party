"""
Одноразовый скрипт: пометить ВСЕ существующие события как posted_tg=True.

Запуск на Railway:
  railway run python scripts/mark_all_posted.py

Запуск локально (если есть data/serviceAccount.json):
  python scripts/mark_all_posted.py

Что делает: берёт все события из Firebase где posted_tg=False
и выставляет posted_tg=True батчами по 400.
После этого только НОВЫЕ события будут публиковаться в канал.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from db.firebase import get_db
from datetime import datetime, timezone

def main():
    db = get_db()

    print("Загружаем все события с posted_tg=False...")
    docs = list(db.collection("events").where("posted_tg", "==", False).stream())
    total = len(docs)
    print(f"Найдено: {total}")

    if total == 0:
        print("Всё уже помечено. Ничего делать не нужно.")
        return

    confirm = input(f"Пометить все {total} событий как posted_tg=True? [y/N] ").strip().lower()
    if confirm != "y":
        print("Отменено.")
        return

    now = datetime.now(timezone.utc).isoformat()
    batch = db.batch()
    count = 0

    for doc in docs:
        batch.update(doc.reference, {
            "posted_tg": True,
            "posted_tg_at": now,
        })
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
            print(f"  Обработано: {count}/{total}")

    if count % 400 != 0:
        batch.commit()

    print(f"Готово. Помечено: {count} событий.")
    print("Теперь только новые события будут публиковаться в канал.")

if __name__ == "__main__":
    main()
