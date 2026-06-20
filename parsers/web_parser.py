"""
Парсер RSS-лент с событиями Кипра.
Рабочие источники:
  - cyprus-mail.com  (What's On RSS)
  - vestnik.cy       (Вестник Кипра RSS)
  - philenews EN     (фильтруем по ключевым словам)
"""
import re
import requests
from datetime import datetime
from email.utils import parsedate_to_datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

EVENT_KEYWORDS = [
    "event", "concert", "festival", "exhibition", "party", "show",
    "performance", "theatre", "cinema", "workshop", "lecture",
    "marathon", "yoga", "market", "dinner", "tasting", "opening",
    "вечер", "концерт", "фестиваль", "выставка", "вечеринка",
    "спектакль", "мероприятие", "событие", "праздник",
]

RSS_SOURCES = [
    # ── Афиша / культура ──────────────────────────────────────────
    {
        "url": "https://cyprus-mail.com/category/entertainment/whats-on/feed/",
        "name": "cyprus-mail-whatson",
        "city": "Cyprus",
        "filter": False,
    },
    {
        "url": "https://www.parikiaki.com/feed/",
        "name": "parikiaki",
        "city": "Cyprus",
        "filter": True,
    },
    {
        "url": "https://en.philenews.com/feed/",
        "name": "philenews",
        "city": "Cyprus",
        "filter": True,
    },
    # ── Спорт ─────────────────────────────────────────────────────
    {
        "url": "https://cyprus-mail.com/category/sport/feed/",
        "name": "cyprus-mail-sport",
        "city": "Cyprus",
        "filter": True,
        "extra_keywords": [
            "marathon", "race", "tournament", "championship", "match",
            "league", "cup", "run", "triathlon", "cycling", "swim",
            "padel", "tennis", "yoga", "fitness", "game", "event",
        ],
    },
    {
        "url": "https://cyprus-mail.com/category/athletics/feed/",
        "name": "cyprus-mail-athletics",
        "city": "Cyprus",
        "filter": False,
    },
    # ── Дети / семья ──────────────────────────────────────────────
    {
        "url": "https://cyprus-mail.com/category/entertainment/whats-on/feed/",
        "name": "cyprus-mail-kids",
        "city": "Cyprus",
        "filter": True,
        "extra_keywords": [
            "kids", "children", "child", "family", "workshop for", "summer camp",
            "school", "junior", "youth", "animation", "puppet",
        ],
    },
]


def _get(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[web] GET {url[:60]} → {e}")
        return ""


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def _clean(text: str) -> str:
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"&[a-z]+;", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_event(title: str, desc: str) -> bool:
    text = (title + " " + desc).lower()
    return any(kw in text for kw in EVENT_KEYWORDS)


def _parse_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        return dt.strftime("%d %b %Y")
    except Exception:
        pass
    try:
        # ISO format
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return raw[:10]


def _parse_rss(xml: str, source_name: str, city: str, do_filter: bool, extra_keywords: list = None) -> list[dict]:
    events = []
    items = re.findall(r"<item>(.*?)</item>", xml, re.S)
    for item in items:
        def tag(name):
            m = re.search(rf"<{name}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>", item, re.S)
            return _clean(_strip_tags(m.group(1))) if m else ""

        title = tag("title")
        link = tag("link") or re.search(r"<link>(.*?)</link>", item, re.S)
        if hasattr(link, "group"):
            link = _clean(link.group(1))
        elif not isinstance(link, str):
            link = ""
        desc = tag("description") or tag("content:encoded")
        pub_date = tag("pubDate")

        if not title or len(title) < 8:
            continue
        if do_filter:
            keywords = (extra_keywords or []) + EVENT_KEYWORDS
            if not any(kw in (title + " " + desc).lower() for kw in keywords):
                continue

        date_str = _parse_date(pub_date)
        eid = f"{source_name}_{re.sub(r'[^a-z0-9]', '', title.lower()[:35])}"

        events.append({
            "id": eid,
            "title": title[:80],
            "full_text": desc[:800],
            "date": date_str,
            "venue": "",
            "city": city,
            "url": link,
            "price": "",
            "source": source_name,
        })
    return events


def fetch_events_web() -> list[dict]:
    all_events = []
    for src in RSS_SOURCES:
        xml = _get(src["url"])
        if not xml:
            continue
        events = _parse_rss(xml, src["name"], src["city"], src["filter"], src.get("extra_keywords"))
        all_events += events
        print(f"[{src['name']}] Найдено: {len(events)}")
    return all_events
