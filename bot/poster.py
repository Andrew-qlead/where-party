import requests
import json
import os
import re
import time

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")

# ── Локальный JSON (только для Threads/Instagram — у них нет флага в Firebase) ──

def load_posted_ids(path: str = "data/posted_ids.json") -> set:
    if os.path.exists(path):
        with open(path) as f:
            return set(json.load(f))
    return set()

def save_posted_ids(ids: set, path: str = "data/posted_ids.json"):
    os.makedirs("data", exist_ok=True)
    with open(path, "w") as f:
        json.dump(list(ids), f)

# ── Форматирование ────────────────────────────────────────────────────────────

def _clean_title(text: str) -> str:
    text = re.sub(r'\*+|_+|`+', '', text)
    return text.strip()

def _short_body(full_text: str, title: str) -> str:
    lines = [l.strip() for l in full_text.splitlines() if len(l.strip()) > 10]
    # пропускаем первую строку если совпадает с заголовком
    if lines and lines[0].lower()[:50] == title.lower()[:50]:
        lines = lines[1:]
    # берём первые 2 предложения из первых строк
    text = " ".join(lines[:3])
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return " ".join(sentences[:2])[:280]

CATEGORY_EMOJI = {
    "music": "🎶", "nightlife": "🎉", "art": "🎨", "food": "🍷",
    "networking": "🎤", "culture": "📖", "outdoor": "🌊",
    "sport": "🏃", "kids": "👶", "other": "📅",
}

def pick_emoji(event: dict) -> str:
    cat = event.get("category", "")
    if cat in CATEGORY_EMOJI:
        return CATEGORY_EMOJI[cat]
    t = (event.get("title") or "").lower()
    if any(w in t for w in ["music","concert","festival","jazz","dj","live","саксофон","хор"]):
        return "🎶"
    if any(w in t for w in ["party","night","club","rave","вечеринка"]):
        return "🎉"
    if any(w in t for w in ["art","exhibition","gallery","выставка"]):
        return "🎨"
    if any(w in t for w in ["food","dinner","wine","restaurant","вино"]):
        return "🍷"
    if any(w in t for w in ["yoga","run","fitness","sport"]):
        return "🏃"
    if any(w in t for w in ["kids","children","дети"]):
        return "👶"
    return "📅"

def fetch_og_image(url: str) -> str:
    """Пробуем получить og:image со страницы события."""
    if not url or not url.startswith("http"):
        return ""
    try:
        r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        if not r.ok:
            return ""
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', r.text, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', r.text, re.I)
        return m.group(1) if m else ""
    except Exception:
        return ""

def format_post(event: dict) -> str:
    title = _clean_title(event.get("title") or "")
    body = _short_body(event.get("full_text") or "", title)
    emoji = pick_emoji(event)

    lines = [f"{emoji} {title}", ""]

    # дата · место · цена в одну строку
    meta_parts = []
    if event.get("date"):
        meta_parts.append(event["date"])
    venue = event.get("venue") or ""
    city = event.get("city") or ""
    if venue:
        meta_parts.append(venue)
    elif city and city != "Cyprus":
        meta_parts.append(city)
    if event.get("price"):
        meta_parts.append(event["price"])
    if meta_parts:
        lines.append(" · ".join(meta_parts))
        lines.append("")

    if body:
        lines.append(body)
        lines.append("")

    if event.get("url"):
        lines.append(f"🎟 Подробности → {event['url']}")
        lines.append("")

    lines.append(_hashtags(event))
    return "\n".join(lines)


def _hashtags(event: dict) -> str:
    tags = ["#Cyprus", "#Events", "#WhereParty"]
    city = event.get("city", "")
    city_tags = {
        "Limassol": "#Limassol", "Nicosia": "#Nicosia",
        "Larnaca": "#Larnaca", "Paphos": "#Paphos",
        "Ayia Napa": "#AyiaNapa", "Protaras": "#Protaras",
    }
    for c, tag in city_tags.items():
        if c.lower() in city.lower():
            tags.append(tag)
            break
    cat_tags = {
        "music": "#CyprusMusic", "nightlife": "#CyprusNightlife",
        "art": "#CyprusArt", "food": "#CyprusFood",
        "sport": "#CyprusSport", "kids": "#CyprusKids",
        "outdoor": "#CyprusOutdoor", "networking": "#CyprusNetworking",
    }
    cat = cat_tags.get(event.get("category", ""), "#CyprusEvents")
    tags.append(cat)
    return " ".join(tags)

# ── Отправка в Telegram ────────────────────────────────────────────────────────

def send_text(text: str, channel: str = None) -> bool:
    ch = channel or CHANNEL_ID
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": ch, "text": text, "disable_web_page_preview": False
        }, timeout=15)
        return r.ok
    except Exception as ex:
        print(f"[poster] send_text error: {ex}")
        return False

def send_photo_url(photo_url: str, caption: str, channel: str = None) -> bool:
    """Отправляем фото по URL. Если Telegram не может скачать — постим текст."""
    ch = channel or CHANNEL_ID
    # Пробуем через multipart (скачиваем сами и шлём как файл)
    try:
        img = requests.get(photo_url, timeout=8)
        if img.ok and img.headers.get("content-type", "").startswith("image"):
            tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            r = requests.post(tg_url, data={
                "chat_id": ch,
                "caption": caption[:1024],
            }, files={"photo": ("photo.jpg", img.content, "image/jpeg")}, timeout=20)
            if r.ok:
                return True
    except Exception:
        pass
    # Fallback — без фото
    return False

# ── Основная функция постинга — использует Firebase как источник правды ────────

def post_new_events(events: list, channel_override: str = None, formatter=None):
    """
    Постим события в Telegram.
    Фильтрация по posted_tg берётся из Firebase (поле в каждом event dict).
    После успешного поста — ставим posted_tg=True в Firebase.
    Локальный JSON больше не используется как фильтр для TG.
    """
    if not BOT_TOKEN or not (channel_override or CHANNEL_ID):
        print("[poster] BOT_TOKEN или CHANNEL_ID не заданы")
        return

    channel = channel_override or CHANNEL_ID
    fmt = formatter or format_post
    # platform: "tg" для основного канала, "tg_en" для EN
    platform = "tg" if not channel_override else "tg_en"

    mark_fb = None
    try:
        from db.firebase import mark_posted as _mark
        mark_fb = _mark
    except Exception:
        pass

    new_count = 0

    for event in events:
        eid = event.get("id")
        if not eid:
            continue

        if event.get(f"posted_{platform}"):
            continue

        text = fmt(event)
        photo_url = event.get("photo_url", "")

        if not photo_url or not photo_url.startswith("http"):
            photo_url = fetch_og_image(event.get("url", ""))

        if photo_url and photo_url.startswith("http"):
            ok = send_photo_url(photo_url, text, channel)
            if not ok:
                ok = send_text(text, channel)
        else:
            ok = send_text(text, channel)

        if ok:
            new_count += 1
            print(f"[poster/{channel}] Опубликовано: {event.get('title', eid)[:50]}")
            if mark_fb:
                try:
                    mark_fb(eid, platform)
                    event[f"posted_{platform}"] = True
                except Exception as e:
                    print(f"[poster] mark_posted error: {e}")
            time.sleep(3)
        else:
            print(f"[poster/{channel}] Ошибка: {event.get('title', eid)[:50]}")

    print(f"[poster/{channel}] Новых постов: {new_count}")
