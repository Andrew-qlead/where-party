import os

def translate_to_english(text: str) -> str:
    if not text or not text.strip():
        return text
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source="auto", target="en").translate(text[:4900])
        return result or text
    except Exception as ex:
        print(f"[translate] Ошибка: {ex}")
        return text
