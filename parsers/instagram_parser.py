"""
Instagram парсер через Apify (актор apify/instagram-scraper).

Заменяет прежний Instaloader-логин (ловил checkpoint на Railway IP).
Apify держит собственный пул резидентных прокси и залогиненных сессий, поэтому
не банится на дата-центровом IP.

ENV (Railway, сервис where-party):
    APIFY_API_TOKEN            -- обязательный, токен из https://console.apify.com/account/integrations
    APIFY_IG_HASHTAGS          -- опционально, CSV хэштегов (перекрывает дефолт)
    APIFY_IG_ACCOUNTS          -- опционально, CSV юзернеймов (перекрывает дефолт)
    APIFY_IG_RESULTS_PER_URL   -- опционально, постов на URL (дефолт 12)
    APIFY_IG_DAYS              -- опционально, глубина в днях (дефолт 7)

Стоимость: ~$1.50 за 1000 постов (тариф apify/instagram-scraper, май 2026).
При дефолтах (10 хэштегов + 2 аккаунта × 12 постов ≈ 144 поста/цикл, 96 циклов/сутки)
это оценочно ~$20-40/мес — держим объём под контролем через RESULTS_PER_URL.
"""
import os
import re
import json
import hashlib
from datetime import datetime, timezone

import requests

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
APIFY_ACTOR = "apify~instagram-scraper"
APIFY_ENDPOINT = (
    f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"
)

# Хэштеги с событиями Кипра
_DEFAULT_HASHTAGS = [
    "cyprusevents", "cyprusparty", "cyprusnightlife", "limassolevents",
    "nicosiaevents", "larnacaevents", "paphosevents", "ayianapaevents",
    "cyprusmusic", "limassollife",
]

# Публичные аккаунты организаторов/площадок
_DEFAULT_ACCOUNTS = [
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


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return [x.strip().lstrip("#@") for x in raw.split(",") if x.strip()]


def _results_per_url() -> int:
    try:
        return max(1, int(os.environ.get("APIFY_IG_RESULTS_PER_URL", "12")))
    except ValueError:
        return 12


def _days() -> int:
    try:
        return max(1, int(os.environ.get("APIFY_IG_DAYS", "7")))
    except ValueError:
        return 7


def _item_to_event(item: dict) -> dict | None:
    """Маппит один пост из датасета Apify в наш event-dict (та же схема,
    что и у остальных источников: id/title/full_text/date/venue/city/url/
    price/photo_url/source). None — если пост не событие / не про Кипр / мусор."""
    caption = (item.get("caption") or "").strip()
    if len(caption) < 30:
        return None

    # Убираем строки из одних хэштегов/эмодзи, берём осмысленный текст
    lines = []
    for l in caption.splitlines():
        l = l.strip()
        if not l:
            continue
        clean = re.sub(r"#\S+", "", l).strip()
        if len(clean) > 5:
            lines.append(clean)
    if not lines:
        return None

    title = re.sub(r"\s+", " ", lines[0])[:80]
    full_text = " ".join(lines[:4])[:600]
    text_lower = (title + " " + full_text).lower()

    # Аккаунты отобраны вручную (это и есть фильтр «Кипр»), а событие/не-событие
    # решает Haiku (is_event). Здесь режем только явный спам/рекламу.
    if any(n in text_lower for n in NOISE):
        return None

    short_code = item.get("shortCode") or item.get("id") or ""
    if not short_code:
        return None

    # Дата поста -> "%d %b %Y"
    ts = item.get("timestamp") or ""
    date_str = ""
    if ts:
        try:
            date_str = datetime.fromisoformat(
                ts.replace("Z", "+00:00")
            ).strftime("%d %b %Y")
        except Exception:
            date_str = ""

    owner = item.get("ownerUsername") or ""
    location = item.get("locationName") or ""
    url = item.get("url") or f"https://www.instagram.com/p/{short_code}/"

    return {
        "id": f"ig_{hashlib.md5(str(short_code).encode()).hexdigest()[:12]}",
        "title": title,
        "full_text": full_text,
        "date": date_str,
        "venue": location,
        "city": "Cyprus",
        "url": url,
        "price": "",
        "photo_url": item.get("displayUrl") or "",
        "source": f"ig_{owner}" if owner else "ig",
    }


def _run_apify(direct_urls: list[str]) -> list[dict]:
    """Один синхронный прогон актора: отдаём URL профилей/хэштегов, получаем
    список постов. Тихо возвращаем [] при любой ошибке — цикл не должен падать."""
    payload = {
        "directUrls": direct_urls,
        "resultsType": "posts",
        "resultsLimit": _results_per_url(),
        "onlyPostsNewerThan": f"{_days()} days",
        "addParentData": False,
    }
    try:
        resp = requests.post(
            APIFY_ENDPOINT,
            params={"timeout": 280},
            headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
            json=payload,
            timeout=300,
        )
        if resp.status_code >= 400:
            print(f"[ig] Apify HTTP {resp.status_code}: {resp.text[:200]}")
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[ig] Apify запрос упал: {str(e)[:120]}")
        return []


def fetch_events_instagram() -> list[dict]:
    if not APIFY_TOKEN:
        print("[ig] APIFY_API_TOKEN не задан — пропускаем Instagram")
        return []

    # Только профили: скрейп хэштегов Instagram закрыл (explore/tags отдаёт
    # метаданные без подписей), поэтому источник — публичные аккаунты
    # организаторов/площадок Кипра. Список задаётся через APIFY_IG_ACCOUNTS.
    accounts = _env_list("APIFY_IG_ACCOUNTS", _DEFAULT_ACCOUNTS)
    direct_urls = [f"https://www.instagram.com/{a}/" for a in accounts]

    if not direct_urls:
        print("[ig] Нет аккаунтов (APIFY_IG_ACCOUNTS пуст) — пропускаем")
        return []

    print(f"[ig] Apify: {len(accounts)} аккаунтов, "
          f"{_results_per_url()} постов/аккаунт, глубина {_days()} дн.")

    items = _run_apify(direct_urls)
    print(f"[ig] Apify вернул {len(items)} постов")

    events = []
    seen_ids = set()
    for item in items:
        ev = _item_to_event(item)
        if ev and ev["id"] not in seen_ids:
            seen_ids.add(ev["id"])
            events.append(ev)

    print(f"[ig] После фильтра (Кипр + событие): {len(events)}")
    return events


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    evs = fetch_events_instagram()
    print(json.dumps(evs[:5], ensure_ascii=False, indent=2))
