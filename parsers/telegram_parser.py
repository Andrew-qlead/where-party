import os
import asyncio
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

API_ID = int(os.environ.get("TELEGRAM_API_ID", 0))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
SESSION_FILE = "data/tg_session"
SESSION_STRING = os.environ.get("TG_SESSION_STRING", "")
PHOTO_DIR = "data/photos"

SOURCE_CHANNELS = [
    "cyprusit",
    "hub_cy",
    "cyproplan",
]

EVENT_KEYWORDS = [
    "event", "party", "festival", "concert", "night", "live",
    "show", "exhibition", "dinner", "brunch", "music", "art",
    "вечер", "концерт", "фестиваль", "выставка", "вечеринка",
]

SKIP_PHRASES = [
    "attention: events may be canceled",
    "please check yourself",
    "events may be canceled",
    "take a sunset",
    "climb ",
    "visit the acropolis",
    "dive into",
]

def is_event_post(text: str) -> bool:
    if not text:
        return False
    tl = text.lower()
    if any(p in tl for p in SKIP_PHRASES):
        return False
    # Слишком короткие — мусор
    if len(text.strip()) < 30:
        return False
    return any(kw in tl for kw in EVENT_KEYWORDS)

def extract_url(text: str, entities) -> str:
    """Извлекаем первую внешнюю ссылку из сообщения (не t.me на источник)."""
    # Сначала из Telegram entities (самый надёжный способ)
    if entities:
        from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl
        for ent in entities:
            if isinstance(ent, MessageEntityTextUrl):
                url = ent.url
                if url and "t.me" not in url:
                    return url
            if isinstance(ent, MessageEntityUrl):
                url = text[ent.offset:ent.offset + ent.length]
                if url and "t.me" not in url:
                    return url
    # Fallback: regex по тексту
    import re
    urls = re.findall(r'https?://[^\s\)]+', text)
    for url in urls:
        if "t.me" not in url:
            return url
    return ""

def strip_md(text: str) -> str:
    import re
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'(?<!\w)_+(?!\w)', '', text)
    text = re.sub(r'`+', '', text)
    return text

def clean_text(text: str) -> str:
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        skip = any(f"@{ch}" in line or f"t.me/{ch}" in line for ch in SOURCE_CHANNELS)
        if not skip:
            cleaned.append(strip_md(line))
    return "\n".join(cleaned).strip()

async def fetch_tg_events(limit_per_channel: int = 30) -> list[dict]:
    os.makedirs("data", exist_ok=True)
    os.makedirs(PHOTO_DIR, exist_ok=True)

    events = []

    from telethon.sessions import StringSession
    session = StringSession(SESSION_STRING) if SESSION_STRING else SESSION_FILE
    async with TelegramClient(session, API_ID, API_HASH) as client:
        for channel in SOURCE_CHANNELS:
            channel_events = []
            try:
                entity = await client.get_entity(channel)
                async for msg in client.iter_messages(entity, limit=limit_per_channel):
                    text = msg.text or msg.message or ""
                    if not is_event_post(text):
                        continue

                    has_photo = isinstance(msg.media, (MessageMediaPhoto, MessageMediaDocument))
                    photo_path = None

                    # Скачиваем фото сразу в рамках той же сессии
                    if has_photo:
                        try:
                            path = await client.download_media(msg, file=PHOTO_DIR)
                            if path and os.path.exists(path):
                                photo_path = path
                        except Exception:
                            photo_path = None

                    clean = clean_text(text)
                    event_id = f"tg_{channel}_{msg.id}"
                    url = extract_url(text, msg.entities)

                    channel_events.append({
                        "id": event_id,
                        "title": clean.splitlines()[0][:80] if clean else "Event",
                        "full_text": clean,
                        "date": msg.date.strftime("%d %b %Y") if msg.date else "",
                        "venue": "",
                        "city": "Cyprus",
                        "url": url,
                        "price": "",
                        "photo_path": photo_path,
                        "source": "tg",
                    })

                events += channel_events
                print(f"[tg/{channel}] Найдено: {len(channel_events)}")
            except Exception as ex:
                print(f"[tg/{channel}] Ошибка: {ex}")

    return events

def fetch_events_telegram() -> list[dict]:
    return asyncio.run(fetch_tg_events())
