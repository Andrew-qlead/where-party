import os

DEEPL_KEY = os.environ.get("DEEPL_API_KEY", "")


def translate_to_russian(text: str) -> str:
    """Переводим текст на русский (для RU-канала когда источник на английском)."""
    if not text or not text.strip():
        return text
    # Если уже в основном кириллица — не переводим
    cyrillic = sum(1 for c in text if 'Ѐ' <= c <= 'ӿ')
    if len(text) > 0 and cyrillic / len(text) >= 0.2:
        return text
    if DEEPL_KEY:
        try:
            import urllib.request, urllib.parse, json
            payload = urllib.parse.urlencode({
                "text": text[:1500],
                "target_lang": "RU",
            }).encode()
            req = urllib.request.Request(
                "https://api-free.deepl.com/v2/translate",
                data=payload, method="POST",
                headers={
                    "Authorization": f"DeepL-Auth-Key {DEEPL_KEY}",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                result = json.loads(r.read())
                translated = result["translations"][0]["text"]
                if translated:
                    return translated
        except Exception as ex:
            print(f"[translate] DeepL→RU ошибка: {ex}")
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source="auto", target="ru").translate(text[:4900])
        return result or text
    except Exception as ex:
        print(f"[translate] Google→RU ошибка: {ex}")
        return text


def translate_to_english(text: str) -> str:
    if not text or not text.strip():
        return text
    # Если уже англоязычный — не переводим
    non_ascii = sum(1 for c in text if ord(c) > 127)
    if non_ascii < len(text) * 0.1:
        return text
    # DeepL
    if DEEPL_KEY:
        try:
            import urllib.request, urllib.parse, json
            payload = urllib.parse.urlencode({
                "text": text[:1500],
                "target_lang": "EN",
                "source_lang": "RU",
            }).encode()
            req = urllib.request.Request(
                "https://api-free.deepl.com/v2/translate",
                data=payload, method="POST",
                headers={
                    "Authorization": f"DeepL-Auth-Key {DEEPL_KEY}",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                result = json.loads(r.read())
                translated = result["translations"][0]["text"]
                if translated:
                    return translated
        except Exception as ex:
            print(f"[translate] DeepL ошибка: {ex}")
    # Fallback — Google
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source="auto", target="en").translate(text[:4900])
        return result or text
    except Exception as ex:
        print(f"[translate] Google ошибка: {ex}")
        return text
