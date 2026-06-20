import re
from bot.translator import translate_to_english

CATEGORY_EMOJI = {
    "music": "🎶", "nightlife": "🎉", "art": "🎨", "food": "🍷",
    "networking": "🎤", "culture": "📖", "outdoor": "🌊",
    "sport": "🏃", "kids": "👶", "other": "📌",
}

def strip_markdown(text: str) -> str:
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'_+', '', text)
    return text.strip()

def extract_title_and_body(full_text: str) -> tuple[str, str]:
    lines = [l for l in full_text.splitlines() if l.strip()]
    if not lines:
        return "", ""
    title = strip_markdown(lines[0])[:80]
    body_lines = [strip_markdown(l) for l in lines[1:] if len(strip_markdown(l)) > 3]
    return title, "\n".join(body_lines[:4])

def format_post_en(event: dict) -> str:
    full_text = event.get("full_text", "")
    if full_text:
        title, body = extract_title_and_body(full_text)
    else:
        title = strip_markdown(event.get("title", ""))
        body = ""

    # Переводим через DeepL
    title_en = translate_to_english(title)
    body_en = translate_to_english(body) if body else ""

    emoji = CATEGORY_EMOJI.get(event.get("category", ""), "📌")
    divider = "━" * 15

    lines = [divider, f"{emoji} {title_en.upper()}", divider, ""]

    if event.get("date"):
        line = f"📅 {event['date']}"
        if event.get("venue"):
            line += f" · {translate_to_english(event['venue'])}"
        elif event.get("city") and event["city"] != "Cyprus":
            line += f" · {event['city']}"
        lines.append(line)
    elif event.get("venue"):
        lines.append(f"📍 {translate_to_english(event['venue'])}")

    if event.get("price"):
        lines.append(f"💰 {event['price']}")

    if body_en:
        lines += ["", body_en]

    if event.get("url"):
        lines += ["", "🔗 Details & Tickets ↓", event["url"]]

    lines += ["", "#Cyprus #Events #WhereParty #CyprusNightlife #VisitCyprus"]
    return "\n".join(lines)
