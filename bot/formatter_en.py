import re
from bot.poster import _hashtags, _clean_title, _short_body, pick_emoji

def format_post_en(event: dict) -> str:
    title = _clean_title(event.get("title_en") or event.get("title") or "")
    full_text = event.get("full_text_en") or event.get("full_text") or ""
    body = _short_body(full_text, title)
    emoji = pick_emoji(event)

    lines = [f"{emoji} {title}", ""]

    meta_parts = []
    if event.get("date"):
        meta_parts.append(event["date"])
    venue = event.get("venue") or ""
    city = event.get("city") or ""
    if venue:
        meta_parts.append(venue)
    elif city and city != "Cyprus":
        meta_parts.append(city)
    if event.get("price"):
        meta_parts.append(event["price"])
    if meta_parts:
        lines.append(" · ".join(meta_parts))
        lines.append("")

    if body:
        lines.append(body)
        lines.append("")

    if event.get("url"):
        lines.append(f"🎟 Tickets → {event['url']}")
        lines.append("")

    lines.append(_hashtags(event))
    return "\n".join(lines)
