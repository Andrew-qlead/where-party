"""Извлекаем город из текста события."""
import re

CITY_PATTERNS = [
    # --- Limassol ---
    (r'\bLimassol\s*Marina\b', 'Limassol'),
    (r'\bOld\s*Town\s*Limassol\b', 'Limassol'),
    (r'\b(Limassol|Lemesos)\b', 'Limassol'),
    (r'\bЛимас[со]ол?[еаы]?\b', 'Limassol'),
    (r'\bЛемесо[се]\b', 'Limassol'),
    # районы/площадки Лимассола
    (r'\b(Germasogeia|Гермасо[гй]ия|Гермасойя)\b', 'Limassol'),
    (r'\b(Molos|Молос|Enaerios|Энаэриос)\b', 'Limassol'),

    # --- Nicosia ---
    (r'\b(Nicosia|Lefkosia|Lefkosa)\b', 'Nicosia'),
    (r'\bНикоси[еия]{1,2}\b', 'Nicosia'),
    (r'\bЛефкоси[еия]{1,2}\b', 'Nicosia'),

    # --- Larnaca ---
    (r'\b(Larnaca|Larnaka)\b', 'Larnaca'),
    (r'\bЛарнак[еиауы]?\b', 'Larnaca'),
    (r'\b(Oroklini|Orokl_ini|Ороклини|Финикудес|Finikoudes)\b', 'Larnaca'),

    # --- Paphos ---
    (r'\b(Paphos|Pafos)\b', 'Paphos'),
    (r'\bПафос[еауы]?\b', 'Paphos'),
    (r'\b(Coral\s*Bay|Корал\s*Бэй|Полис|Polis)\b', 'Paphos'),

    # --- Ayia Napa ---
    (r'\bAyia\s*Napa\b', 'Ayia Napa'),
    (r'\bАй[яьи]\s*[-\s]?Напа\b', 'Ayia Napa'),

    # --- Protaras / Paralimni ---
    (r'\bProtaras\b', 'Protaras'),
    (r'\bПротарас[еауы]?\b', 'Protaras'),
    (r'\b(Paralimni|Паралимни)\b', 'Paralimni'),

    # --- Kyrenia ---
    (r'\b(Kyrenia|Girne)\b', 'Kyrenia'),
    (r'\bКирени[еия]{1,2}\b', 'Kyrenia'),
]

# Привязка города по источнику (Telegram-каналы/RSS с явной географией).
# Срабатывает только когда текст города не дал результата.
SOURCE_CITY = {
    "kipr_podslushano_limasol": "Limassol",
    "kipr_podslushano_nicosia": "Nicosia",
    "cyprus_music": "",  # общий, не привязан
}


def extract_city(text: str) -> str:
    if not text:
        return ''
    for pattern, city in CITY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return city
    return ''


def extract_city_from_source(source: str) -> str:
    """Фолбэк: город по источнику, если из текста не извлёкся."""
    return SOURCE_CITY.get((source or '').strip(), '')
