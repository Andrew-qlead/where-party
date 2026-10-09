"""
Разовый: удаляет из Firebase (коллекция events) все НЕ-IG события
(source не начинается с 'ig') — легаси из удалённых RSS/TG источников.
Firestore REST. Запуск: railway run <venv-py> scripts/delete_non_ig_firebase.py
"""
import os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.mark_all_posted_rest import get_access_token, list_all_events


def fb_delete(token, doc_name):
    req = urllib.request.Request(f"https://firestore.googleapis.com/v1/{doc_name}",
                                 method="DELETE", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()


token = get_access_token()
docs = list_all_events(token)
print(f"Всего в Firebase: {len(docs)}")

deleted = 0
for d in docs:
    src = d.get("fields", {}).get("source", {}).get("stringValue", "")
    if not src.startswith("ig"):
        try:
            fb_delete(token, d["name"])
            deleted += 1
        except Exception as e:
            print(f"  err {d['name'].split('/')[-1]}: {str(e)[:80]}")

print(f"Удалено не-IG из Firebase: {deleted} | осталось IG: {len(docs)-deleted}")
