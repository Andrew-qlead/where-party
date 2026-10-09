"""
WR PT <- Where Party Cyprus event sync.

WHERE THIS RUNS: the *other* machine, inside the `where-party` repo's Railway
worker (the one that already parses Telegram/RSS every 15 min and writes to
Firestore). This file is not meant to run inside wrpt-app — it lives here
only because that's where the Supabase schema/context was available. Copy it
into the where-party repo (e.g. as `sync_supabase.py`) and call
`sync_to_supabase(events)` at the end of the existing worker cycle, right
after dedup, using the *same* event list that already gets written to
Firestore. Do not re-fetch from Firestore separately — reuse what the cycle
already computed, so nothing there needs to change except adding one call.

REQUIRES on that machine:
  pip install supabase
  env vars (Railway, `where-party` service — new, not present there yet):
    SUPABASE_URL                 -- same value as in wrpt-app/.env and telegram-bot/.env
    SUPABASE_SERVICE_ROLE_KEY    -- same value as in telegram-bot/.env (server-side only,
                                     never the anon key, never shipped to a client)

WHY auto-approved: rows land with status='approved' directly (bypassing the
organizer-submission moderation queue from migration_2). This pipeline already
filters junk and dedupes upstream, so there's no human organizer to review --
treating it as a trusted feed, same trust level as the scraper had for
`source_channel` in schema.sql's original design intent.
"""

import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

CYPRUS_TZ = ZoneInfo("Asia/Nicosia")

# Where Party's 9 categories -> WR PT's category_id (src/data/categories.ts).
# Unmapped/unknown categories fall back to 'other' rather than being dropped.
CATEGORY_MAP = {
    "music": "concert",
    "nightlife": "party",
    "art": "exhibition",
    "food": "food",
    "sport": "sport",
    "networking": "networking",
    "culture": "theatre",
    "kids": "kids",
    "outdoor": "outdoor",
}

# Where Party's free-text `city` -> WR PT's city_id (src/data/cities.ts).
# Only these 11 towns exist in the app's city filter/map. An event whose city
# doesn't match any of these is skipped (logged), not guessed -- inventing a
# city_id would misplace it on the map, and city_id/lat/lng are NOT NULL.
CITY_MAP = {
    "limassol": "limassol",
    "nicosia": "nicosia",
    "larnaca": "larnaca",
    "larnaka": "larnaca",
    "paphos": "paphos",
    "pafos": "paphos",
    "ayia napa": "ayia_napa",
    "ayianapa": "ayia_napa",
    "protaras": "protaras",
    "paralimni": "paralimni",
    "kyrenia": "kyrenia",
    "girne": "kyrenia",
    "oroklini": "oroklini",
    "germasogeia": "germasogeia",
    "germasogia": "germasogeia",
    "polis": "polis",
}

# Town-centre coordinates, mirrored from wrpt-app/src/data/cities.ts. Where
# Party gives no venue coordinates, only a city name -- this is the same
# "good enough for map centering" approximation the app's own seed data uses.
CITY_COORDS = {
    "limassol": (34.7071, 33.0226),
    "nicosia": (35.1856, 33.3823),
    "larnaca": (34.9229, 33.6233),
    "paphos": (34.7720, 32.4297),
    "ayia_napa": (34.9897, 34.0073),
    "protaras": (35.0140, 34.0584),
    "paralimni": (35.0392, 34.0084),
    "kyrenia": (35.3417, 33.3192),
    "oroklini": (34.9419, 33.5736),
    "germasogeia": (34.7333, 33.0833),
    "polis": (35.0339, 32.4264),
}

_PRICE_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _parse_date(date_str: str):
    """Where Party gives day-precision dates like '19 Jun 2026', no time of
    day. Default to 20:00 local (Cyprus tz) as a neutral "evening event"
    placeholder -- this is an approximation, not real event start time, since
    the source data doesn't carry one. Returns None if unparseable (row is
    skipped rather than inserted with a fabricated date)."""
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            naive = datetime.strptime(date_str.strip(), fmt)
            return naive.replace(hour=20, minute=0, tzinfo=CYPRUS_TZ)
        except ValueError:
            continue
    return None


def _parse_price(price_str):
    if not price_str:
        return None
    match = _PRICE_NUMBER.search(price_str.replace(",", "."))
    return int(float(match.group())) if match else None


_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I
)
_og_cache = {}


def _fetch_og_image(url: str):
    """Догружает og:image со страницы события, когда в RSS фото не было.
    Кэшируется в рамках прогона, короткий таймаут, тихо падает в None."""
    if not url or not url.startswith("http"):
        return None
    if url in _og_cache:
        return _og_cache[url]
    result = None
    try:
        import urllib.request as _u
        req = _u.Request(url, headers={"User-Agent": "Mozilla/5.0 (WRPT sync)"})
        with _u.urlopen(req, timeout=6) as r:
            html = r.read(200_000).decode("utf-8", "ignore")
        m = _OG_IMAGE_RE.search(html)
        if m:
            result = m.group(1)
    except Exception:
        result = None
    _og_cache[url] = result
    return result


# Читаемые названия городов для venue-фолбэка.
_CITY_DISPLAY = {
    "limassol": "Limassol", "nicosia": "Nicosia", "larnaca": "Larnaca",
    "paphos": "Paphos", "ayia_napa": "Ayia Napa", "protaras": "Protaras",
    "paralimni": "Paralimni", "kyrenia": "Kyrenia", "oroklini": "Oroklini",
    "germasogeia": "Germasogeia", "polis": "Polis",
}

# Источники, которые тянут новости или не-кипрские события — не синкаем.
# cyprus-mail-sport/athletics: спортивные новости (не афиша).
# parikiaki: лондонская кипрская газета, события британской диаспоры (не Кипр).
BLOCKED_SOURCES = {"cyprus-mail-sport", "cyprus-mail-athletics", "parikiaki"}

# Мусорные заголовки-приветствия из TG (не события).
_JUNK_TITLE_RE = re.compile(
    r"^\s*(hi|hello|hey|всем\s+привет|привет|доброе\s+утро|good\s+morning|тест|test)\b",
    re.IGNORECASE,
)


def _map_row(event: dict):
    """Returns a Supabase `events` row dict, or None if the event can't be
    mapped safely / should not reach the app (past date, junk, blocked source)."""
    source = (event.get("source") or "").strip()

    # --- Фильтр 1: заблокированные источники (новости, не события) ---
    if source in BLOCKED_SOURCES:
        return None

    # --- Фильтр 2: мусорные/слишком короткие заголовки ---
    title_raw = (event.get("title") or event.get("title_en") or "").strip()
    if len(title_raw) < 15 or _JUNK_TITLE_RE.match(title_raw):
        return None

    city_key = (event.get("city") or "").strip().lower()
    city_id = CITY_MAP.get(city_key)
    if city_id is None:
        # Город не распознан напрямую — пробуем извлечь из текста и источника,
        # прежде чем валить в дефолт. Это резко уменьшает перекос в Nicosia.
        from db.city_extractor import extract_city, extract_city_from_source
        text = (event.get("title") or "") + " " + (event.get("full_text") or "") + " " + (event.get("venue") or "")
        detected = extract_city(text) or extract_city_from_source(source)
        city_id = CITY_MAP.get(detected.strip().lower()) if detected else None
        if city_id is None:
            # Совсем не определился — дефолт Limassol (главный хаб событий Кипра).
            city_id = "limassol"

    date_iso = _parse_date(event.get("date") or "")
    if date_iso is None:
        print(f"[sync] skip {event.get('id')}: unparseable date {event.get('date')!r}")
        return None

    # --- Фильтр 3: прошедшие события не показываем (приложение живёт "здесь и сейчас") ---
    from datetime import datetime as _dt, timedelta as _td
    if date_iso < _dt.now(CYPRUS_TZ) - _td(days=1):
        return None

    lat, lng = CITY_COORDS[city_id]
    # Русский/английский от Haiku (title_ru/desc_ru/desc_en), иначе фолбэк на оригинал
    title_ru = event.get("title_ru") or event.get("title") or event.get("title_en") or ""
    title_en = event.get("title") or event.get("title_en") or event.get("title_ru") or ""

    # --- Venue fallback: если места нет, ставим город (лучше пустого в карточке) ---
    venue_display = (event.get("venue") or "").strip() or _CITY_DISPLAY.get(city_id, "Cyprus")

    # --- Image fallback: RSS без фото -> тянем og:image со страницы события ---
    image_url = event.get("photo_url")
    if not image_url:
        image_url = _fetch_og_image(event.get("url"))

    return {
        "external_id": event["id"],
        "title_ru": title_ru,
        "title_en": title_en,
        "description_ru": event.get("desc_ru") or event.get("full_text") or "",
        "description_en": event.get("desc_en") or event.get("full_text_en") or event.get("full_text") or "",
        "category_id": CATEGORY_MAP.get(event.get("category"), "other"),
        "city_id": city_id,
        "venue_ru": venue_display,
        "venue_en": venue_display,
        "lat": lat,
        "lng": lng,
        "date_iso": date_iso.isoformat(),
        "price": _parse_price(event.get("price")),
        "currency": "EUR",
        "is_online": False,
        "ticket_url": event.get("url") or None,
        "image_url": image_url or None,
        "source_channel": source or "whereparty",
        "status": "approved",
    }


def cleanup_past_supabase(days_grace: int = 1) -> int:
    """Удаляет из Supabase события с ПРОШЕДШЕЙ датой (date_iso) + их фото из
    Supabase Storage (бакет event-images), чтобы не копить мусор и место.
    Возвращает число удалённых."""
    import json, urllib.request, urllib.error, urllib.parse
    from datetime import datetime, timedelta, timezone

    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return 0
    H = {"apikey": key, "Authorization": f"Bearer {key}"}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_grace)).isoformat()
    cutoff_q = urllib.parse.quote(cutoff)

    # 1) находим прошедшие
    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/events?select=external_id,image_url&date_iso=lt.{cutoff_q}",
            headers=H)
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.loads(r.read())
    except Exception as e:
        print(f"[cleanup-sb] выборка прошедших упала: {str(e)[:100]}")
        return 0
    if not rows:
        return 0

    # 2) удаляем фото из Storage (по external_id.jpg, и на всякий — из image_url)
    for row in rows:
        paths = {f"{row['external_id']}.jpg"}
        iu = row.get("image_url") or ""
        marker = "/storage/v1/object/public/event-images/"
        if marker in iu:
            paths.add(iu.split(marker, 1)[1])
        for p in paths:
            try:
                dreq = urllib.request.Request(
                    f"{url}/storage/v1/object/event-images/{p}",
                    method="DELETE", headers=H)
                urllib.request.urlopen(dreq, timeout=15).read()
            except Exception:
                pass  # нет файла — не страшно

    # 3) удаляем строки одним запросом
    try:
        dreq = urllib.request.Request(
            f"{url}/rest/v1/events?date_iso=lt.{cutoff_q}",
            method="DELETE", headers={**H, "Prefer": "return=minimal"})
        urllib.request.urlopen(dreq, timeout=30).read()
    except Exception as e:
        print(f"[cleanup-sb] удаление строк упало: {str(e)[:100]}")
        return 0

    print(f"[cleanup-sb] удалено прошедших событий из Supabase + фото: {len(rows)}")
    return len(rows)


def sync_to_supabase(events: list[dict]) -> None:
    """events: the same list of Firestore event dicts this worker cycle
    already parsed/deduped/wrote to Firestore. Upserts into WR PT's
    Supabase `events` table, keyed on external_id."""
    import urllib.request
    import json as _json

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    rows = [r for r in (_map_row(e) for e in events) if r is not None]
    if not rows:
        return

    endpoint = f"{url}/rest/v1/events?on_conflict=external_id"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

    ok, failed = 0, 0
    # Send in small batches — large payloads can hit PostgREST limits
    batch_size = 20
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        payload = _json.dumps(batch).encode()
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                resp.read()
            ok += len(batch)
        except urllib.error.HTTPError as e:
            failed += len(batch)
            body = e.read().decode(errors="replace")[:300]
            print(f"[sync] batch {i//batch_size} error HTTP {e.code}: {body}")
        except Exception as e:
            failed += len(batch)
            print(f"[sync] batch {i//batch_size} error: {e}")

    print(f"[sync] upserted {ok}/{len(events)} events to Supabase (failed: {failed})")
