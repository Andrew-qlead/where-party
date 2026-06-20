import requests
import re
from datetime import datetime

BASE_URL = "https://eventor.com.cy"

def fetch_events_eventor():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://eventor.com.cy/",
    }

    # Пробуем несколько вероятных API-эндпоинтов JS-сайта
    endpoints = [
        "/api/events",
        "/api/v1/events",
        "/_next/data/events.json",
    ]

    for ep in endpoints:
        try:
            r = requests.get(BASE_URL + ep, headers=headers, timeout=10)
            if r.ok and "application/json" in r.headers.get("Content-Type", ""):
                data = r.json()
                events_raw = data if isinstance(data, list) else data.get("events", data.get("data", []))
                result = []
                for e in events_raw[:20]:
                    title = e.get("title") or e.get("name") or ""
                    if not title:
                        continue
                    result.append({
                        "id": f"ev_{e.get('id', re.sub(r'[^a-z0-9]', '', title.lower())[:20])}",
                        "title": title,
                        "date": e.get("date") or e.get("start_date") or e.get("startDate") or "",
                        "venue": e.get("venue") or e.get("location") or "",
                        "city": e.get("city") or "Cyprus",
                        "url": e.get("url") or e.get("link") or f"{BASE_URL}/event/{e.get('id', '')}",
                        "price": e.get("price") or "",
                    })
                if result:
                    print(f"[eventor] Найдено: {len(result)} (endpoint: {ep})")
                    return result
        except Exception:
            continue

    # Fallback: статический HTML
    try:
        r = requests.get(BASE_URL, headers=headers, timeout=15)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        events = []
        for a in soup.select("a[href*='/event']")[:20]:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not title or len(title) < 5:
                continue
            url = href if href.startswith("http") else BASE_URL + href
            events.append({
                "id": f"ev_{re.sub(r'[^a-z0-9]', '', url.lower())[-25:]}",
                "title": title,
                "date": "",
                "venue": "",
                "city": "Cyprus",
                "url": url,
                "price": "",
            })
        print(f"[eventor] Найдено (HTML): {len(events)}")
        return events
    except Exception as ex:
        print(f"[eventor] Ошибка: {ex}")
        return []
