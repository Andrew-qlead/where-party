import re
from bot.poster import _hashtags

CATEGORY_EMOJI = {
    "music": "🎶", "nightlife": "🎉", "art": "🎨", "food": "🍷",
    "networking": "🎤", "culture": "📖", "outdoor": "🌊",
    "sport": "🏃", "kids": "👶", "other": "📌",
}

def format_post_en(event: dict) -> str:
    # Используем уже переведённые поля (сохранены при парсинге)
    title = event.get("title_en") or event.get("title", "")
    body = event.get("full_text_en") or event.get("full_text", "")

    title = re.sub(r'\*+|_+|`+', '', title).strip()[:80]

    # Берём первые 4 строки тела
    body_lines = [l.strip() for l in body.splitlines() if len(l.strip()) > 3]
    # Пропускаем первую строку если она совпадает с заголовком
    if body_lines and body_lines[0].lower().strip() == title.lower().strip():
        body_lines = body_lines[1:]
    body_short = "\n".join(body_lines[:4])

    emoji = CATEGORY_EMOJI.get(event.get("category", ""), "📌")
    divider = "━" * 15
    lines = [divider, f"{emoji} {title.upper()}", divider, ""]

    if event.get("date"):
        line = f"📅 {event['date']}"
        if event.get("venue"):
            line += f" · {event['venue']}"
        elif event.get("city") and event["city"] != "Cyprus":
            line += f" · {event['city']}"
        lines.append(line)
    elif event.get("venue"):
        lines.append(f"📍 {event['venue']}")

    if event.get("price"):
        lines.append(f"💰 {event['price']}")

    if body_short:
        lines += ["", body_short]

    if event.get("url"):
        lines += ["", "🔗 Details & Tickets ↓", event["url"]]

    lines += ["", _hashtags(event)]
    return "\n".join(lines)
