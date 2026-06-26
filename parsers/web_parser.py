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
    # ── Русскоязычная афиша Кипра ─────────────────────────────────
    {
        "url": "https://vkcyprus.com/afisha/feed/",
        "name": "vkcyprus",
        "city": "Cyprus",
        "filter": False,  # уже категория "Афиша"
    },
    {
        "url": "https://afishamira.com/city/cyprus/feed/",
        "name": "afishamira",
        "city": "Cyprus",
        "filter": False,  # концерты и события для русскоязычных
    },
    # kiprinform отключён — новостной сайт, проходит аварии/погоду/политику
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
    # philenews отключён — 90% политика и общие новости, не афиша
    # ── Официальный туристический портал Кипра ───────────────────
    {
        "url": "https://www.visitcyprus.com/events/feed/",
        "name": "visitcyprus",
        "city": "Cyprus",
        "filter": False,  # уже категория events
    },
    # ── Развлечения / культура Cyprus Mail ────────────────────────
    {
        "url": "https://cyprus-mail.com/category/entertainment/feed/",
        "name": "cyprus-mail-entertainment",
        "city": "Cyprus",
        "filter": True,  # есть TV-рецензии и интервью — фильтруем
    },
    # cyprus-mail sport/athletics отключены — дают новостные статьи, не афишу
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


NOISE_PHRASES = [
    # спортивные новости (результаты, трансферы, рейтинги — не афиша)
    "breaks record", "world record", "championship parade", "must ditch",
    "wake-up call", "knicks", "nba", "premier league", "super rugby",
    "transfer", "signing", "squad", "coach sacked", "fired", "appointed",
    "thrash", "blunt attack", "sends mexico", "hold out", "scores twice",
    "ten-man", "hosts promoted", "lodge fifa", "travel restrictions",
    "hurricanes thrash", "world cup", "olympic", "paralympic", "champion",
    "ronaldo", "messi", "arsenal", "manchester", "barcelona", "real madrid",
    "group a:", "group b:", "group c:", "group d:", "match report",
    # не-кипрские события
    "waltham cross", "returns for summer 2026",
    # политика / некрологи
    "dies at", "passed away", "obituary", "election", "parliament",
    "prime minister", "government", "ceasefire", "war", "conflict", "troops",
    "judge orders", "stand trial", "bars her from", "protest", "rally",
    "erdogan", "trump", "nato", "biden", "putin", "zelensky", "macron",
    "orders talks", "turkish president", "orders officials", "president orders",
    "seminary", "diplomatic", "sanctions", "foreign minister", "summit",
    "white house", "kremlin", "pentagon", "european commission",
    # погода / инфраструктура / происшествия
    "braces for", "heat wave", "heat dome", "extreme heat", "deadly furnace",
    "prolonged extreme", "faces prolonged", "turns europe", "meteorolog",
    "clear weather", "isolated showers", "thunderstorms", "cloud cover",
    "weather forecast", "погода на", "прогноз погоды", "осадки", "облачность",
    "mostly clear", "автобус протаранил",
    # политика / памятные даты
    "памятные мероприятия", "годовщине начала", "великой отечест",
    "годовщина", "день победы", "anniversary of",
    # аварии / происшествия / смерть
    "road fatalities", "road deaths", "road accident", "traffic accident",
    "car crash", "fatal crash", "killed in", "died in", "fatalities",
    "reduction in road", "road safety report", "etsc", "per cent reduction",
    "записи скорой", "дтп", "авария на",
    # финансовые новости
    "stock", "shares", "nasdaq", "crypto crash", "bitcoin price",
    # сетевой/инвестиционный спам
    "resource networking club", "закрытая встреча для инвесторов",
    "иммиграционными экспертами", "save the date",
    # новостные дайджесты (утренние/вечерние обзоры)
    "утренний обзор", "вечерний обзор", "morning news review", "evening news review",
    "обзор новостей", "news review", "дайджест новостей", "новости дня",
    "morning digest", "evening digest",
    # смерти
    "скончался", "умер на", "погиб на", "died on a flight", "man died",
    # мошенничество/налоги (не события)
    "мошенничество от имени", "налоговой службы",
]

def _is_event(title: str, desc: str) -> bool:
    text = (title + " " + desc).lower()
    if any(p in text for p in NOISE_PHRASES):
        return False
    return any(kw in text for kw in EVENT_KEYWORDS)


def _quality_score(event: dict) -> int:
    """Оценка качества события 0-4. Берём только если >= 1."""
    score = 0
    text = (event.get("title", "") + " " + event.get("full_text", "")).lower()
    if event.get("date"):
        score += 1
    if event.get("url"):
        score += 1
    if any(w in text for w in ["cyprus", "кипр", "limassol", "nicosia", "larnaca", "paphos"]):
        score += 1
    if any(w in text for w in ["ticket", "entrance", "admission", "free", "€", "price",
                                 "вход", "билет", "бесплатно", "цена"]):
        score += 1
    return score


def _parse_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        return dt.strftime("%d %b %Y")
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return raw[:10]


EN_MONTHS = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,
    "sep":9,"oct":10,"nov":11,"dec":12,
}
RU_MONTHS_WEB = {
    "января":1,"февраля":2,"марта":3,"апреля":4,"мая":5,"июня":6,
    "июля":7,"августа":8,"сентября":9,"октября":10,"ноября":11,"декабря":12,
}

def _extract_event_date(text: str, pub_date_str: str) -> str:
    """Пробуем вытащить реальную дату события из текста. Fallback — pubDate."""
    year = datetime.now().year
    # "19 June", "19 Jun", "June 19"
    def _try_date(y, mo, d):
        try:
            return datetime(y, mo, d).strftime("%d %b %Y")
        except ValueError:
            return None

    m = re.search(r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b', text, re.I)
    if m:
        day, mon_s = int(m.group(1)), m.group(2).lower()
        mon = EN_MONTHS.get(mon_s)
        if mon:
            r = _try_date(year, mon, day)
            if r: return r
    m = re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})\b', text, re.I)
    if m:
        mon_s, day = m.group(1).lower(), int(m.group(2))
        mon = EN_MONTHS.get(mon_s)
        if mon:
            r = _try_date(year, mon, day)
            if r: return r
    m = re.search(r'\b(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b', text, re.I)
    if m:
        day, mon_s = int(m.group(1)), m.group(2).lower()
        mon = RU_MONTHS_WEB.get(mon_s)
        if mon:
            r = _try_date(year, mon, day)
            if r: return r
    return _parse_date(pub_date_str)


def _extract_photo(item: str) -> str:
    """Ищем URL картинки в разных местах RSS-элемента."""
    # <media:thumbnail url="..."/>
    m = re.search(r'<media:thumbnail[^>]+url=["\']([^"\']+)["\']', item, re.S)
    if m:
        return m.group(1)
    # <media:content url="..." medium="image".../>
    m = re.search(r'<media:content[^>]+url=["\']([^"\']+\.(?:jpg|jpeg|png|webp))["\']', item, re.I)
    if m:
        return m.group(1)
    # <enclosure url="..." type="image/..."/>
    m = re.search(r'<enclosure[^>]+type=["\']image/[^"\']+["\'][^>]+url=["\']([^"\']+)["\']', item, re.S)
    if m:
        return m.group(1)
    m = re.search(r'<enclosure[^>]+url=["\']([^"\']+)["\'][^>]+type=["\']image/[^"\']+["\']', item, re.S)
    if m:
        return m.group(1)
    # первый <img src="..."> в теле описания
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', item, re.S)
    if m:
        return m.group(1)
    return ""


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
        if not _is_event(title, desc):
            continue

        date_str = _extract_event_date(title + " " + desc, pub_date)
        eid = f"{source_name}_{re.sub(r'[^a-z0-9]', '', title.lower()[:35])}"

        # убираем дату из конца заголовка: "Event name – 30.6.2026" → "Event name"
        title = re.sub(r'\s*[–\-—]\s*\d{1,2}[./]\d{1,2}[./]\d{4}\s*$', '', title).strip()

        events.append({
            "id": eid,
            "title": title[:80],
            "full_text": desc[:800],
            "date": date_str,
            "venue": "",
            "city": city,
            "url": link,
            "price": "",
            "photo_url": _extract_photo(item),
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
