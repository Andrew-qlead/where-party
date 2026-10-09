"""
Разовый: копирует уже готовые русские/английские поля из Supabase в Firebase,
чтобы мини-апп (читает Firebase) показывал описание на нужном языке при
переключении RU/EN. Без новых вызовов Haiku — переиспользуем то, что уже есть.
Пишет в Firebase поля: title_ru, desc_ru, title_en, full_text_en, desc_en.
Запуск: railway run <venv-py> scripts/backfill_firebase_ru.py
"""
import os, sys, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.mark_all_posted_rest import get_access_token, firestore_patch, PROJECT_ID

SB = os.environ["SUPABASE_URL"].rstrip("/")
SKEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]


def sb_get(path):
    req = urllib.request.Request(SB + path, headers={"apikey": SKEY, "Authorization": f"Bearer {SKEY}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fb_patch(token, event_id, fields: dict):
    mask = "&".join(f"updateMask.fieldPaths={k}" for k in fields)
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/events/{event_id}?{mask}"
    body = {"fields": {k: {"stringValue": v} for k, v in fields.items()}}
    firestore_patch(token, url, body)


rows = sb_get("/rest/v1/events?select=external_id,title_ru,title_en,description_ru,description_en&source_channel=like.ig*&limit=200")
print(f"IG-событий в Supabase: {len(rows)}")

token = get_access_token()
done = 0
for r in rows:
    eid = r["external_id"]
    fields = {}
    if r.get("title_ru"): fields["title_ru"] = r["title_ru"]
    if r.get("title_en"): fields["title_en"] = r["title_en"]
    if r.get("description_ru"): fields["desc_ru"] = r["description_ru"]
    if r.get("description_en"):
        fields["desc_en"] = r["description_en"]
        fields["full_text_en"] = r["description_en"]  # мини-апп EN-body читает full_text_en
    if not fields:
        continue
    try:
        fb_patch(token, eid, fields)
        done += 1
    except Exception as e:
        print(f"  err {eid}: {str(e)[:100]}")

print(f"Обновлено в Firebase (RU/EN поля для мини-аппа): {done}")
