"""
Бэкфилл RU-канала: сбрасывает posted_tg=False для IG-событий, которые старый
код skip-пометил (english title → не постились в RU). После этого воркер
зальёт их в @WrPtCy на русском (5/цикл). posted_tg_en НЕ трогаем (в EN уже есть).
Firestore REST API — работает на любом Python. Запуск: railway run <py> scripts/reset_ru_for_ig.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.mark_all_posted_rest import (
    get_access_token, list_all_events, firestore_patch, PROJECT_ID,
)


def set_posted_tg_false(token: str, doc_name: str):
    url = f"https://firestore.googleapis.com/v1/{doc_name}?updateMask.fieldPaths=posted_tg"
    firestore_patch(token, url, {"fields": {"posted_tg": {"booleanValue": False}}})


def main():
    token = get_access_token()
    docs = list_all_events(token)
    print(f"Всего событий в базе: {len(docs)}")

    reset = 0
    for doc in docs:
        f = doc.get("fields", {})
        source = f.get("source", {}).get("stringValue", "")
        posted = f.get("posted_tg", {}).get("booleanValue", False)
        # только IG-события, которые сейчас помечены posted_tg=True (skip)
        if source.startswith("ig") and posted:
            try:
                set_posted_tg_false(token, doc["name"])
                reset += 1
            except Exception as e:
                print(f"  err {doc['name'].split('/')[-1]}: {e}")

    print(f"Сброшено posted_tg=False у IG-событий: {reset} — уйдут в RU-канал (5/цикл, каждые 15 мин)")


if __name__ == "__main__":
    main()
