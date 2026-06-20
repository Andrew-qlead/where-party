"""Извлекаем город из текста события."""
import re

CITY_PATTERNS = [
    # EN names
    (r'\b(Limassol|Lemesos)\b', 'Limassol'),
    (r'\bNicosia\b', 'Nicosia'),
    (r'\bLarnaca\b', 'Larnaca'),
    (r'\bPaphos\b', 'Paphos'),
    (r'\bAyia\s*Napa\b', 'Ayia Napa'),
    (r'\bProtaras\b', 'Protaras'),
    (r'\bFamagusta\b', 'Famagusta'),
    (r'\bLimassol\s*Marina\b', 'Limassol'),
    (r'\bOld\s*Town\s*Limassol\b', 'Limassol'),
    # RU names
    (r'\bЛимас[со]ле?\b', 'Limassol'),
    (r'\bЛемесо[се]\b', 'Limassol'),
    (r'\bНикосии?\b', 'Nicosia'),
    (r'\bЛарнак[еи]\b', 'Larnaca'),
    (r'\bПафос[еа]?\b', 'Paphos'),
    (r'\bАйя[\s-]Напа\b', 'Ayia Napa'),
    (r'\bПротарас[еа]?\b', 'Protaras'),
]

def extract_city(text: str) -> str:
    if not text:
        return ''
    for pattern, city in CITY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return city
    return ''
