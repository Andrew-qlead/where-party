import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://in-cyprus.com/category/lifestyle/events/"

def fetch_events_incyprus():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(BASE_URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        events = []

        for card in soup.select("article")[:15]:
            title_el = card.select_one("h2 a, h3 a, .entry-title a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if not title or not url:
                continue

            date_el = card.select_one("time, .entry-date, .post-date")
            date = date_el.get("datetime") or date_el.get_text(strip=True) if date_el else ""

            img_el = card.select_one("img")
            image = img_el.get("src") or img_el.get("data-src") if img_el else ""

            events.append({
                "id": f"ic_{re.sub(r'[^a-z0-9]', '', url.lower())[-30:]}",
                "title": title,
                "date": date,
                "venue": "",
                "city": "Cyprus",
                "url": url,
                "price": "",
                "image": image,
            })

        print(f"[in-cyprus] Найдено: {len(events)}")
        return events
    except Exception as ex:
        print(f"[in-cyprus] Ошибка: {ex}")
        return []
