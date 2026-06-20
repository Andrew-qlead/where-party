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
    # ── IT / нетворкинг ───────────────────────────────────────
    "cyprusit",             # Cyprus IT — главный IT-канал
    "hub_cy",               # Hub Cyprus
    # ── Общие афиши ───────────────────────────────────────────
    "cyproplan",            # Cyproplan — афиша всего Кипра
    "LentaCypRus",          # Лента Кипра
    "Vestnik_Kipra",        # Вестник Кипра (русскоязычная газета)
    "cyprus_kipr",          # Кипр Новости
    "evropakipr",           # Европа/Кипр
    "cyprus_music",         # Cyprus Culture & Music
    "kipr_podslushano_limasol",   # Подслушано Лимасол
    "kipr_podslushano_nicosia",   # Подслушано Никосия
    # ── Спорт ─────────────────────────────────────────────────
    "KouspoRun",            # Беговые события Кипра
    "CyprusRoadRaces",      # Шоссейные гонки
    "yoga_cyprus",          # Йога Кипр
    "padelcyprus",          # Падел Кипр
    # ── Дети / семья ──────────────────────────────────────────
    "Fractal_in_Cyprus",    # Кружки и лагеря для детей
    "kidscyprus",           # Детские события
    "mamacyprus",           # Мамы Кипра
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

async def fetch_tg_events(limit_per_channel: int = 20) -> list[dict]:
    if not API_ID or not API_HASH or not SESSION_STRING:
        print("[tg] API_ID/API_HASH/SESSION_STRING не заданы — пропускаем")
        return []

    events = []
    from telethon.sessions import StringSession
    session = StringSession(SESSION_STRING)

    try:
        client = TelegramClient(session, API_ID, API_HASH)
        await asyncio.wait_for(client.connect(), timeout=15)
    except Exception as ex:
        print(f"[tg] Не удалось подключиться: {ex}")
        return []

    try:
        for channel in SOURCE_CHANNELS:
            channel_events = []
            try:
                entity = await asyncio.wait_for(client.get_entity(channel), timeout=10)
                async for msg in client.iter_messages(entity, limit=limit_per_channel):
                    text = msg.text or msg.message or ""
                    if not is_event_post(text):
                        continue

                    clean = clean_text(text)
                    url = extract_url(text, msg.entities)

                    # Фото — берём только если это прямо прикреплённое фото (не скачиваем)
                    photo_url = ""
                    if isinstance(msg.media, MessageMediaPhoto):
                        photo_url = ""  # Telethon не даёт прямой URL без скачивания

                    channel_events.append({
                        "id": f"tg_{channel}_{msg.id}",
                        "title": clean.splitlines()[0][:80] if clean else "Event",
                        "full_text": clean,
                        "date": msg.date.strftime("%d %b %Y") if msg.date else "",
                        "venue": "",
                        "city": "Cyprus",
                        "url": url,
                        "price": "",
                        "photo_url": photo_url,
                        "source": "tg",
                    })

                events += channel_events
                print(f"[tg/{channel}] {len(channel_events)}")
            except asyncio.TimeoutError:
                print(f"[tg/{channel}] таймаут")
            except Exception as ex:
                print(f"[tg/{channel}] ошибка: {ex}")
    finally:
        await client.disconnect()

    return events

def fetch_events_telegram() -> list[dict]:
    return asyncio.run(fetch_tg_events())
