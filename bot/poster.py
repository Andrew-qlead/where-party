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
    if any(w in t for w in ["music","concert","festival","jazz","dj","live","саксофон","хор","виолончель"]):
        return "🎶"
    if any(w in t for w in ["party","night","club","rave","вечеринка"]):
        return "🎉"
    if any(w in t for w in ["art","exhibition","gallery","выставка","искусств"]):
        return "🎨"
    if any(w in t for w in ["food","dinner","brunch","wine","chef","restaurant","вино","коктейль"]):
        return "🍷"
    if any(w in t for w in ["yoga","sport","run","fitness","велопрогулка","скейт"]):
        return "🏃"
    if any(w in t for w in ["book","lecture","talk","meetup","networking","книг","клуб"]):
        return "🎤"
    if any(w in t for w in ["kids","children","дети","детск"]):
        return "👶"
    if any(w in t for w in ["beach","outdoor","природ","sunset","море"]):
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
    """Отправляем фото по URL (не скачиваем локально)."""
    ch = channel or CHANNEL_ID
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        r = requests.post(url, json={
            "chat_id": ch,
            "photo": photo_url,
            "caption": caption[:1024],
        }, timeout=15)
        if not r.ok:
            print(f"[poster] sendPhoto failed ({r.status_code}), falling back to text")
        return r.ok
    except Exception as ex:
        print(f"[poster] send_photo_url error: {ex}")
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
    is_main_channel = not channel_override  # основной RU канал

    # Firebase mark_posted — импортируем если доступно
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

        # Пропускаем уже запощенные (флаг из Firebase, прочитанный при сохранении)
        # Для основного канала проверяем posted_tg, для EN — posted_tg_en
        flag_key = "posted_tg" if is_main_channel else f"posted_tg_{channel.strip('@')}"
        if event.get(flag_key) or event.get("posted_tg"):
            continue

        text = fmt(event)
        photo_url = event.get("photo_url", "")

        if photo_url and photo_url.startswith("http"):
            ok = send_photo_url(photo_url, text, channel)
            if not ok:
                ok = send_text(text, channel)
        else:
            ok = send_text(text, channel)

        if ok:
            new_count += 1
            print(f"[poster/{channel}] Опубликовано: {event.get('title', eid)[:50]}")
            # Ставим флаг в Firebase
            if mark_fb:
                try:
                    mark_fb(eid, "tg")
                    event["posted_tg"] = True  # обновляем локально чтобы не дублировать в этой сессии
                except Exception as e:
                    print(f"[poster] mark_posted error: {e}")
            time.sleep(3)
        else:
            print(f"[poster/{channel}] Ошибка: {event.get('title', eid)[:50]}")

    print(f"[poster/{channel}] Новых постов: {new_count}")
