import os
import deepl

_translator = None

def get_translator():
    global _translator
    if not _translator:
        key = os.environ.get("DEEPL_API_KEY", "")
        if not key:
            return None
        _translator = deepl.Translator(key)
    return _translator

def translate_to_english(text: str) -> str:
    if not text or not text.strip():
        return text
    translator = get_translator()
    if not translator:
        return text
    try:
        result = translator.translate_text(text, target_lang="EN-GB")
        return result.text
    except Exception as ex:
        print(f"[deepl] Ошибка перевода: {ex}")
        return text
