import requests
import json
import os
import time

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")  # например @wherepartycyprus
POSTED_FILE = "data/posted_ids.json"

def load_posted_ids():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE) as f:
            return set(json.load(f))
    return set()

def save_posted_ids(ids):
    os.makedirs("data", exist_ok=True)
    with open(POSTED_FILE, "w") as f:
        json.dump(list(ids), f)

def format_post(event):
    lines = []
    lines.append(f"🎉 *{event['title']}*")
    if event.get("date"):
        lines.append(f"📅 {event['date']}")
    if event.get("venue"):
        lines.append(f"📍 {event['venue']}")
    if event.get("city"):
        lines.append(f"🌍 {event['city']}")
    if event.get("price"):
        lines.append(f"💰 {event['price']}")
    if event.get("url"):
        lines.append(f"🔗 {event['url']}")
    lines.append("")
    lines.append("#Cyprus #party #whereParty #Larnaca #Nicosia #Limassol")
    return "\n".join(lines)

def send_post(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    r = requests.post(url, json=data, timeout=10)
    return r.ok

def post_new_events(events):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("[poster] BOT_TOKEN или CHANNEL_ID не заданы")
        return

    posted = load_posted_ids()
    new_count = 0

    for event in events:
        eid = event.get("id")
        if eid in posted:
            continue
        text = format_post(event)
        ok = send_post(text)
        if ok:
            posted.add(eid)
            new_count += 1
            print(f"[poster] Опубликовано: {event['title']}")
            time.sleep(2)  # не спамим API
        else:
            print(f"[poster] Ошибка отправки: {event['title']}")

    save_posted_ids(posted)
    print(f"[poster] Новых постов: {new_count}")
