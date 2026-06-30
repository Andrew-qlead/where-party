import re
from bot.poster import _hashtags, _clean_title, _short_body, pick_emoji

def format_post_en(event: dict) -> str:
    """Шаблон C3 для EN-канала @partycy. URL отдельно — идёт в inline-кнопку."""
    title = _clean_title(event.get("title_en") or event.get("title") or "")
    full_text = event.get("full_text_en") or event.get("full_text") or ""
    body = _short_body(full_text, title)
    emoji = pick_emoji(event)

    # Одно предложение анонса
    if body:
        sentences = re.split(r'(?<=[.!?])\s+', body)
        body = sentences[0][:200]

    lines = [f"{emoji} <b>{title}</b>", ""]

    if body:
        lines.append(body)
        lines.append("")

    # Дата и место
    meta_parts = []
    if event.get("date"):
        meta_parts.append(f"📅 {event['date']}")
    venue = event.get("venue") or ""
    city = event.get("city") or ""
    if venue:
        meta_parts.append(f"📍 {venue}")
    elif city and city != "Cyprus":
        meta_parts.append(f"📍 {city}")
    if event.get("price"):
        meta_parts.append(f"💰 {event['price']}")
    if meta_parts:
        lines.append("  ·  ".join(meta_parts))
        lines.append("")

    lines.append(_hashtags(event))
    return "\n".join(lines)
