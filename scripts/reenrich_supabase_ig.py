"""
Разовый: освежает уже залитые IG-события в Supabase (основное приложение) —
прогоняет их подпись+картинку через Haiku и переписывает title_ru/description_ru
(+ EN) на живой русский/английский. Нужен для событий, залитых до апгрейда,
у которых title_ru был английским. Запуск: railway run <venv-py> scripts/reenrich_supabase_ig.py
"""
import os, sys, json, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.enrich import enrich_events

SB = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def sb_get(path):
    req = urllib.request.Request(SB + path, headers=H)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def sb_patch(external_id, body):
    data = json.dumps(body).encode()
    url = f"{SB}/rest/v1/events?external_id=eq.{urllib.parse.quote(external_id)}"
    req = urllib.request.Request(url, data=data, method="PATCH",
                                 headers={**H, "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


rows = sb_get("/rest/v1/events?select=external_id,title_ru,description_ru,image_url,date_iso&source_channel=like.ig*&limit=100")
print(f"IG-событий в Supabase: {len(rows)}")

# собираем в event-dict для enrich
evs = []
for r in rows:
    evs.append({
        "id": r["external_id"],
        "title": r.get("title_ru") or "",
        "full_text": r.get("description_ru") or r.get("title_ru") or "",
        "photo_url": r.get("image_url") or "",
        "date": (r.get("date_iso") or "")[:10],
        "source": "ig_reenrich", "city": "Cyprus", "venue": "", "price": "", "url": "",
    })

enriched = enrich_events(evs)
by_id = {e["id"]: e for e in enriched}

updated = 0
for r in rows:
    e = by_id.get(r["external_id"])
    if not e:
        continue  # Haiku решил что не событие — не трогаем
    body = {}
    if e.get("title_ru"): body["title_ru"] = e["title_ru"]
    if e.get("title"): body["title_en"] = e["title"]
    if e.get("desc_ru"): body["description_ru"] = e["desc_ru"]
    if e.get("desc_en"): body["description_en"] = e["desc_en"]
    if body:
        try:
            sb_patch(r["external_id"], body)
            updated += 1
        except Exception as ex:
            print(f"  err {r['external_id']}: {ex}")

print(f"Обновлено (русский/английский от Haiku): {updated}")
