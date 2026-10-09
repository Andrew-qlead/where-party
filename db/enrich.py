"""
Обогащение событий через Claude Haiku 4.5 (мультимодальный).

Читает подпись поста + картинку-флаер и извлекает структурированные поля:
дату (главная проблема IG — дата почти всегда на картинке, не в тексте),
venue, город, цену, категорию, и гейт is_event. Гоняется ТОЛЬКО на новых
событиях (после дедупа), поэтому вызовов немного.

ENV: ANTHROPIC_API_KEY (обязательный).
Модель: claude-haiku-4-5 (~$1/$5 за млн токенов вход/выход).
"""
import os
import json
import base64
from datetime import datetime, timezone

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5"

# 9 категорий проекта (совпадают с db/categorizer + CATEGORY_MAP в sync_supabase)
CATEGORIES = ["music", "nightlife", "art", "food", "sport",
              "networking", "culture", "kids", "outdoor", "other"]

# Города, которые понимает основное приложение (см. CITY_MAP в sync_supabase)
CITIES = ["Limassol", "Nicosia", "Larnaca", "Paphos", "Ayia Napa",
          "Protaras", "Paralimni", "Kyrenia", "Oroklini", "Germasogeia",
          "Polis", "Cyprus"]

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_event": {"type": "boolean",
                     "description": "true только если это анонс конкретного мероприятия с датой/местом на Кипре (концерт, вечеринка, фестиваль, выставка и т.п.). false для рекламы, новостей, продаж, общих постов."},
        "title": {"type": "string", "description": "Короткое название события на английском/оригинале (до 80 символов). Бренды и имена собственные (BEONIX, Nammos, DJ-имена) оставляй как есть."},
        "title_ru": {"type": "string", "description": "Название события на русском (до 80 символов), живое и естественное. Бренды/имена собственные оставляй латиницей (BEONIX, Nammos). Не машинный перевод — как написал бы редактор афиши."},
        "desc_ru": {"type": "string", "description": "Одно короткое цепляющее предложение о событии на русском (до 160 символов). Без хэштегов и эмодзи-спама."},
        "desc_en": {"type": "string", "description": "Одно короткое предложение о событии на английском (до 160 символов). Без хэштегов."},
        "date_iso": {"type": "string",
                     "description": "Дата НАЧАЛА события в формате YYYY-MM-DD. Ищи дату на картинке-флаере И в тексте. Разрешай относительные ('this Saturday', 'завтра') относительно даты поста. Если даты нет — пустая строка."},
        "time": {"type": "string", "description": "Время начала HH:MM или пустая строка."},
        "venue": {"type": "string", "description": "Название площадки/места или пустая строка."},
        "city": {"type": "string", "enum": CITIES,
                 "description": "Город Кипра. Если не ясно — Cyprus."},
        "price": {"type": "string", "description": "Цена входа числом (например '15') или пустая строка если бесплатно/не указано."},
        "category": {"type": "string", "enum": CATEGORIES,
                     "description": "Категория события."},
    },
    "required": ["is_event", "title", "title_ru", "desc_ru", "desc_en", "date_iso", "time", "venue", "city", "price", "category"],
}


def _get_client():
    try:
        import anthropic
    except ImportError:
        print("[enrich] пакет anthropic не установлен")
        return None
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _download_image(url: str) -> bytes | None:
    if not url or not url.startswith("http"):
        return None
    try:
        import requests
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception as e:
        print(f"[enrich] не скачал картинку: {str(e)[:80]}")
    return None


def _iso_to_display(date_iso: str) -> str:
    """YYYY-MM-DD -> '%d %b %Y' (формат, который понимают фильтр дат и sync)."""
    try:
        return datetime.strptime(date_iso.strip(), "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        return ""


def enrich_events(events: list[dict]) -> list[dict]:
    """Обогащает список событий через Haiku. Возвращает только те, что
    is_event=True. Мутирует event: date/venue/city/price/category + кладёт
    скачанные байты картинки в event['_image_bytes'] для перезаливки."""
    if not ANTHROPIC_API_KEY:
        print("[enrich] ANTHROPIC_API_KEY не задан — пропускаем обогащение")
        return events

    client = _get_client()
    if client is None:
        return events

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = []
    for event in events:
        caption = (event.get("full_text") or event.get("title") or "").strip()
        if not caption:
            continue

        img_bytes = _download_image(event.get("photo_url", ""))
        post_date = event.get("date", "")

        content = [{
            "type": "text",
            "text": (
                f"Дата поста: {post_date or 'неизвестна'}. Сегодня: {today}.\n"
                f"Подпись поста Instagram:\n{caption[:1500]}\n\n"
                "Извлеки данные о мероприятии. Дату ищи в первую очередь на картинке-флаере."
            ),
        }]
        if img_bytes:
            content.insert(0, {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(img_bytes).decode(),
                },
            })

        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": content}],
                output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            )
            text = next((b.text for b in resp.content if b.type == "text"), "")
            data = json.loads(text)
        except Exception as e:
            print(f"[enrich] ошибка Haiku для {event.get('id')}: {str(e)[:100]}")
            # Не смогли обогатить — оставляем событие как есть (не роняем пайплайн)
            if img_bytes:
                event["_image_bytes"] = img_bytes
            out.append(event)
            continue

        if not data.get("is_event"):
            print(f"[enrich] отброшено (не событие): {event.get('title','')[:50]}")
            continue

        # Мержим извлечённые поля
        if data.get("title"):
            event["title"] = data["title"][:80]
        if data.get("title_ru"):
            event["title_ru"] = data["title_ru"][:80]
        if data.get("desc_ru"):
            event["desc_ru"] = data["desc_ru"][:300]
        if data.get("desc_en"):
            event["desc_en"] = data["desc_en"][:300]
        d = _iso_to_display(data.get("date_iso", ""))
        if d:
            event["date"] = d
        if data.get("venue"):
            event["venue"] = data["venue"]
        if data.get("city"):
            event["city"] = data["city"]
        if data.get("price"):
            event["price"] = data["price"]
        if data.get("category") and data["category"] != "other":
            event["category"] = data["category"]
        if img_bytes:
            event["_image_bytes"] = img_bytes

        out.append(event)

    print(f"[enrich] обогащено событий: {len(out)} (из {len(events)})")
    return out
