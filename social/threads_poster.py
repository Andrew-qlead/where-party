import os
import requests
import time
import re

THREADS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "")

BASE_URL = "https://graph.threads.net/v1.0"

CATEGORY_EMOJI = {
    "music": "🎶", "nightlife": "🎉", "art": "🎨", "food": "🍷",
    "networking": "🎤", "culture": "📖", "outdoor": "🌊", "sport": "🏃",
    "kids": "👶", "other": "📌"
}

CITY_TAG = {
    "limassol": "#Limassol", "nicosia": "#Nicosia",
    "larnaca": "#Larnaca", "paphos": "#Paphos",
    "ayia napa": "#AyiaNapa", "protaras": "#Protaras",
}

CAT_TAG = {
    "music": "#LiveMusic", "nightlife": "#Nightlife",
    "art": "#Art", "food": "#FoodAndDrink",
    "networking": "#Networking", "culture": "#Culture",
    "outdoor": "#Outdoors", "sport": "#Sport", "kids": "#FamilyFun",
}


def _hashtags(event: dict) -> str:
    tags = ["#Cyprus", "#CyprusEvents", "#WhereParty"]
    city = (event.get("city") or "").lower()
    for c, tag in CITY_TAG.items():
        if c in city:
            tags.append(tag)
            break
    cat = event.get("category", "")
    if cat in CAT_TAG:
        tags.append(CAT_TAG[cat])
    return " ".join(tags)


def _clean(text: str) -> str:
    text = re.sub(r'\*+|_+|`+', '', text)
    return text.strip()


def build_post(event: dict) -> str:
    """Один EN пост на событие. Лимит Threads — 500 символов."""
    title = _clean(event.get("title_en") or event.get("title", ""))
    body = _clean(event.get("full_text_en") or event.get("full_text", ""))
    emoji = CATEGORY_EMOJI.get(event.get("category", ""), "📌")
    tags = _hashtags(event)

    # Заголовок
    lines = [f"{emoji} {title}"]

    # Дата + место
    meta = []
    if event.get("date"):
        meta.append(f"📅 {event['date']}")
    venue = event.get("venue", "")
    city = event.get("city", "")
    if venue:
        meta.append(f"📍 {venue}")
    elif city and city != "Cyprus":
        meta.append(f"📍 {city}")
    if meta:
        lines.append("  ".join(meta))

    if event.get("price"):
        lines.append(f"💰 {event['price']}")

    # Тело — обрезаем по последнему полному предложению
    reserved = len("\n".join(lines)) + len(tags) + 10  # место под хэштеги
    available = 490 - reserved
    if body and available > 60:
        body_lines = [l for l in body.splitlines() if len(l.strip()) > 3]
        # Пропускаем первую строку если дублирует заголовок
        if body_lines and body_lines[0].lower().strip() == title.lower().strip():
            body_lines = body_lines[1:]
        excerpt = " ".join(body_lines)[:available]
        # Обрезаем по последней точке чтобы не обрывать на полуслове
        last_dot = max(excerpt.rfind(". "), excerpt.rfind(".\n"), excerpt.rfind("! "), excerpt.rfind("? "))
        if last_dot > available // 2:
            excerpt = excerpt[:last_dot + 1]
        if excerpt:
            lines.append(f"\n{excerpt}")

    if event.get("url"):
        lines.append(f"\n🔗 {event['url']}")

    lines.append(f"\n{tags}")
    return "\n".join(lines)[:500]


# ── API ───────────────────────────────────────────────────────────────────────

def _create_container(text: str, image_url: str = None) -> str | None:
    url = f"{BASE_URL}/{THREADS_USER_ID}/threads"
    params = {"access_token": THREADS_TOKEN, "text": text}
    if image_url:
        params["media_type"] = "IMAGE"
        params["image_url"] = image_url
    else:
        params["media_type"] = "TEXT"
    r = requests.post(url, params=params, timeout=15)
    if r.ok:
        return r.json().get("id")
    print(f"[threads] create error: {r.text}")
    return None


def _publish(creation_id: str) -> bool:
    url = f"{BASE_URL}/{THREADS_USER_ID}/threads_publish"
    r = requests.post(url, params={
        "creation_id": creation_id,
        "access_token": THREADS_TOKEN,
    }, timeout=15)
    if not r.ok:
        print(f"[threads] publish error: {r.text}")
    return r.ok


def post_to_threads(text: str, image_url: str = None) -> bool:
    if not THREADS_TOKEN or not THREADS_USER_ID:
        return False
    cid = _create_container(text, image_url)
    if not cid:
        return False
    time.sleep(5)
    return _publish(cid)


def post_event_bilingual(event: dict) -> bool:
    """Один пост на событие (EN). Без RU дубля — Threads аудитория EN."""
    photo = event.get("photo_url", "")
    text = build_post(event)
    ok = post_to_threads(text, image_url=photo if photo else None)
    return ok


# Оставляем для обратной совместимости
def post_events_to_threads(events, formatter, posted_ids):
    new_posted = set()
    for event in events:
        eid = event.get("id")
        if eid in posted_ids:
            continue
        ok = post_event_bilingual(event)
        if ok:
            new_posted.add(eid)
            time.sleep(10)
    return new_posted
