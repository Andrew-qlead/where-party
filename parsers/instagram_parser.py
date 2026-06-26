"""
Instagram парсер через Instaloader.
Нужны env vars: INSTAGRAM_SCRAPER_USERNAME, INSTAGRAM_SCRAPER_PASSWORD
Аккаунт — обычный личный (не бизнес, не API).
"""
import os
import re
import time
import hashlib
from datetime import datetime, timedelta, timezone

IG_USERNAME = os.environ.get("INSTAGRAM_SCRAPER_USERNAME", "")
IG_PASSWORD = os.environ.get("INSTAGRAM_SCRAPER_PASSWORD", "")
SESSION_FILE = "/tmp/ig_session"

# Хэштеги с событиями Кипра
HASHTAGS = [
    "cyprusevents",
    "cyprusparty",
    "cyprusnightlife",
    "limassolevents",
    "nicosiaevents",
    "larnacaevents",
    "paphosevents",
    "ayianapaevents",
    "cyprusmusic",
    "limassollife",
]

# Публичные аккаунты организаторов/площадок
ACCOUNTS = [
    "soldouttickets",
    "vivacy_gr",
]

CYPRUS_KEYWORDS = [
    "cyprus", "кипр", "limassol", "nicosia", "larnaca", "paphos",
    "ayia napa", "ayianapa", "protaras", "лимасол", "никосия",
    "ларнака", "пафос", "айя-напа",
]

EVENT_KEYWORDS = [
    "event", "concert", "party", "festival", "show", "exhibition",
    "workshop", "dinner", "live", "dj", "performance", "открытие",
    "вечеринка", "концерт", "фестиваль", "выставка", "билеты", "tickets",
]

NOISE = [
    "for sale", "real estate", "property", "mortgage", "loan",
    "recruitment", "vacancy", "job offer", "hiring", "we are looking",
]


def _get_loader():
    try:
        import instaloader
    except ImportError:
        print("[ig] instaloader не установлен")
        return None

    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_comments=False,
        save_metadata=False,
        quiet=True,
        request_timeout=10,
        max_connection_attempts=1,  # не retry при ошибке
    )
    if not IG_USERNAME or not IG_PASSWORD:
        return L

    try:
        L.load_session_from_file(IG_USERNAME, SESSION_FILE)
        print("[ig] Сессия загружена из файла")
    except Exception:
        try:
            L.login(IG_USERNAME, IG_PASSWORD)
            L.save_session_to_file(SESSION_FILE)
            print("[ig] Логин успешен, сессия сохранена")
        except Exception as e:
            print(f"[ig] Ошибка логина: {e}")
    return L


def _post_to_event(post, source_tag: str) -> dict | None:
    caption = post.caption or ""
    if len(caption) < 30:
        return None

    # Убираем строки из одних хэштегов/эмодзи
    lines = []
    for l in caption.splitlines():
        l = l.strip()
        if not l:
            continue
        clean = re.sub(r'#\S+', '', l).strip()
        if len(clean) > 5:
            lines.append(clean)

    if not lines:
        return None

    title = re.sub(r'\s+', ' ', lines[0])[:80]
    full_text = " ".join(lines[:4])[:600]
    text_lower = (title + " " + full_text).lower()

    # Фильтры
    if any(n in text_lower for n in NOISE):
        return None
    if not any(kw in text_lower for kw in CYPRUS_KEYWORDS):
        return None
    if not any(kw in text_lower for kw in EVENT_KEYWORDS):
        return None

    photo_url = ""
    try:
        photo_url = post.url
    except Exception:
        pass

    event_id = f"ig_{hashlib.md5(str(post.mediaid).encode()).hexdigest()[:12]}"

    return {
        "id": event_id,
        "title": title,
        "full_text": full_text,
        "date": post.date_utc.strftime("%d %b %Y"),
        "venue": "",
        "city": "Cyprus",
        "url": f"https://www.instagram.com/p/{post.shortcode}/",
        "price": "",
        "photo_url": photo_url,
        "source": f"ig_{source_tag}",
    }


def fetch_events_instagram() -> list[dict]:
    if not IG_USERNAME or not IG_PASSWORD:
        print("[ig] INSTAGRAM_SCRAPER_USERNAME/PASSWORD не заданы — пропускаем")
        return []

    try:
        import instaloader
    except ImportError:
        print("[ig] instaloader не установлен")
        return []

    L = _get_loader()
    if L is None:
        return []

    # Проверяем что логин прошёл — если нет, сразу выходим без retry
    try:
        if not L.context.is_logged_in:
            print("[ig] Не залогинен — пропускаем")
            return []
    except Exception:
        print("[ig] Не залогинен — пропускаем")
        return []

    events = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    for tag in HASHTAGS:
        try:
            hashtag = instaloader.Hashtag.from_name(L.context, tag)
            count = 0
            for post in hashtag.get_posts():
                if post.date_utc < cutoff:
                    break
                if count >= 15:
                    break
                ev = _post_to_event(post, tag)
                if ev:
                    events.append(ev)
                count += 1
                time.sleep(3)
            print(f"[ig] #{tag}: проверено {count} постов")
        except Exception as e:
            print(f"[ig] #{tag} ошибка: {str(e)[:80]}")
        time.sleep(5)

    for account in ACCOUNTS:
        try:
            profile = instaloader.Profile.from_username(L.context, account)
            count = 0
            for post in profile.get_posts():
                if post.date_utc < cutoff:
                    break
                if count >= 10:
                    break
                ev = _post_to_event(post, account)
                if ev:
                    events.append(ev)
                count += 1
                time.sleep(3)
            print(f"[ig] @{account}: проверено {count} постов")
        except Exception as e:
            print(f"[ig] @{account} ошибка: {str(e)[:80]}")
        time.sleep(5)

    print(f"[ig] Итого событий: {len(events)}")
    return events
