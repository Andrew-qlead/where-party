import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://en.philenews.com/category/whats-on/events-activities/"

def fetch_events_incyprus():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; WherePartyBot/1.0)"}
    try:
        r = requests.get(BASE_URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        events = []

        for title_el in soup.select("h3 a, h2 a")[:15]:
            title = title_el.get_text(strip=True)
            if not title:
                continue
            url = title_el.get("href", "")
            date = ""

            events.append({
                "id": f"ic_{re.sub(r'[^a-z0-9]', '', url.lower())[:30]}",
                "title": title,
                "date": date,
                "venue": "",
                "city": "Cyprus",
                "url": url,
                "price": "",
                "source": "in-cyprus.com",
            })

        print(f"[in-cyprus] Найдено: {len(events)}")
        return events
    except Exception as ex:
        print(f"[in-cyprus] Ошибка: {ex}")
        return []
