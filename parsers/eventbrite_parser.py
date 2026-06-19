import requests
import json
from datetime import datetime

EVENTBRITE_TOKEN = ""  # Вставь токен из eventbrite.com/platform

def fetch_events_cyprus():
    if not EVENTBRITE_TOKEN:
        print("[eventbrite] Токен не задан, пропускаем")
        return []

    url = "https://www.eventbriteapi.com/v3/events/search/"
    params = {
        "location.address": "Cyprus",
        "location.within": "50km",
        "categories": "103,105,113",  # music, nightlife, arts
        "expand": "venue",
        "token": EVENTBRITE_TOKEN,
        "page_size": 20,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        events = r.json().get("events", [])
        result = []
        for e in events:
            result.append({
                "id": f"eb_{e['id']}",
                "title": e["name"]["text"],
                "date": e["start"]["local"],
                "venue": e.get("venue", {}).get("name", ""),
                "city": e.get("venue", {}).get("address", {}).get("city", "Cyprus"),
                "url": e["url"],
                "price": "Free" if e.get("is_free") else "Paid",
                "source": "Eventbrite",
            })
        print(f"[eventbrite] Найдено: {len(result)}")
        return result
    except Exception as ex:
        print(f"[eventbrite] Ошибка: {ex}")
        return []
