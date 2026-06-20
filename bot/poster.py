import requests
import json
import os
import re
import time

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")

def load_posted_ids(path: str = "data/posted_ids.json") -> set:
    if os.path.exists(path):
        with open(path) as f:
            return set(json.load(f))
    return set()

def save_posted_ids(ids: set, path: str = "data/posted_ids.json"):
    os.makedirs("data", exist_ok=True)
    with open(path, "w") as f:
        json.dump(list(ids), f)

def strip_markdown(text: str) -> str:
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'_+', '', text)
    text = re.sub(r'`+', '', text)
    return text.strip()

def extract_title_and_body(full_text: str) -> tuple[str, str]:
    lines = [l for l in full_text.splitlines() if l.strip()]
    if not lines:
        return "", ""
    title = strip_markdown(lines[0])[:80]
    body_lines = [strip_markdown(l) for l in lines[1:] if len(strip_markdown(l)) > 3]
    return title, "\n".join(body_lines[:4])

def pick_emoji(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["music", "concert", "festival", "jazz", "dj", "live", "саксофон", "хор", "виолончель"]):
        return "🎶"
    if any(w in t for w in ["party", "night", "club", "rave", "вечеринка"]):
        return "🎉"
    if any(w in t for w in ["art", "exhibition", "gallery", "выставка", "искусств"]):
        return "🎨"
    if any(w in t for w in ["food", "dinner", "brunch", "wine", "chef", "restaurant", "вино", "коктейль"]):
        return "🍷"
    if any(w in t for w in ["yoga", "sport", "run", "fitness", "велопрогулка", "скейт"]):
        return "🏃"
    if any(w in t for w in ["book", "lecture", "talk", "meetup", "networking", "книг", "клуб"]):
        return "🎤"
    if any(w in t for w in ["kids", "children", "дети", "детск"]):
        return "👶"
    if any(w in t for w in ["beach", "outdoor", "природ", "sunset", "море"]):
        return "🌊"
    return "📌"

def format_post(event: dict) -> str:
    full_text = event.get("full_text", "")
    if full_text:
        title, body = extract_title_and_body(full_text)
    else:
        title = strip_markdown(event.get("title", ""))
        body = ""

    emoji = pick_emoji(title)
    divider = "━" * 15

    lines = [divider, f"{emoji} {title.upper()}", divider, ""]

    if event.get("date"):
        line = f"📅 {event['date']}"
        if event.get("venue"):
            line += f" · {event['venue']}"
        elif event.get("city") and event["city"] != "Cyprus":
            line += f" · {event['city']}"
        lines.append(line)
    elif event.get("venue"):
        lines.append(f"📍 {event['venue']}")

    if event.get("price"):
        lines.append(f"💰 {event['price']}")

    if body:
        lines += ["", body]

    if event.get("url"):
        lines += ["", "🔗 Подробности ↓", event["url"]]

    lines += ["", "#Cyprus #Events #WhereParty #Larnaca #Nicosia #Limassol"]
    return "\n".join(lines)

def send_text(text: str, channel: str = None) -> bool:
    ch = channel or CHANNEL_ID
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": ch, "text": text, "disable_web_page_preview": False}, timeout=15)
        return r.ok
    except Exception as ex:
        print(f"[poster] send_text error: {ex}")
        return False

def send_photo_with_caption(photo_path: str, caption: str, channel: str = None) -> bool:
    ch = channel or CHANNEL_ID
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            r = requests.post(url, data={"chat_id": ch, "caption": caption[:1024]}, files={"photo": f}, timeout=60)
        return r.ok
    except Exception as ex:
        print(f"[poster] send_photo error: {ex}")
        return False

def post_new_events(events: list, channel_override: str = None, formatter=None):
    if not BOT_TOKEN or not (channel_override or CHANNEL_ID):
        print("[poster] BOT_TOKEN или CHANNEL_ID не заданы")
        return

    channel = channel_override or CHANNEL_ID
    posted_file = f"data/posted_{channel.strip('@')}.json" if channel_override else "data/posted_ids.json"
    fmt = formatter or format_post

    posted = load_posted_ids(posted_file)
    new_count = 0

    for event in events:
        eid = event.get("id")
        if eid in posted:
            continue

        text = fmt(event)
        photo_path = event.get("photo_path")

        if photo_path and os.path.exists(photo_path):
            ok = send_photo_with_caption(photo_path, text, channel)
            os.remove(photo_path)
            if not ok:
                ok = send_text(text, channel)
        else:
            ok = send_text(text, channel)

        if ok:
            posted.add(eid)
            new_count += 1
            print(f"[poster/{channel}] Опубликовано: {event.get('title', eid)[:50]}")
            time.sleep(3)
        else:
            print(f"[poster/{channel}] Ошибка: {event.get('title', eid)[:50]}")

    save_posted_ids(posted, posted_file)
    print(f"[poster/{channel}] Новых постов: {new_count}")
