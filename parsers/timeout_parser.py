import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.timeout.com/cyprus/things-to-do/events-in-cyprus"

# Фразы-маркеры туристических советов (не событий)
NOT_EVENTS = ["take a ", "climb ", "visit the ", "dive into", "explore ", "discover ", "head to "]

def is_real_event(title: str) -> bool:
    t = title.lower().strip()
    if any(t.startswith(skip) for skip in NOT_EVENTS):
        return False
    # Нумерованные списки типа "1.Thing to do"
    if re.match(r'^\d+\.', t):
        return False
    return True

def fetch_events_timeout():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(BASE_URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        events = []

        for card in soup.select("article, [data-testid='tile-article']")[:20]:
            title_el = card.select_one("h3, h2, [data-testid='tile-title']")
            link_el = card.select_one("a[href]")
            if not title_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            if not is_real_event(title):
                continue

            href = link_el.get("href", "")
            url = href if href.startswith("http") else f"https://www.timeout.com{href}"

            date_el = card.select_one("time, [data-testid='tile-date']")
            date = date_el.get_text(strip=True) if date_el else ""

            events.append({
                "id": f"to_{re.sub(r'[^a-z0-9]', '', url.lower())[-30:]}",
                "title": title,
                "date": date,
                "venue": "",
                "city": "Cyprus",
                "url": url,
                "price": "",
            })

        print(f"[timeout] Найдено: {len(events)}")
        return events
    except Exception as ex:
        print(f"[timeout] Ошибка: {ex}")
        return []
