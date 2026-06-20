CATEGORIES = {
    "music": [
        "music", "concert", "festival", "jazz", "dj", "live music", "band", "orchestra",
        "концерт", "музыка", "фестиваль", "джаз", "диджей", "оркестр", "саксофон", "вокал",
        "хор", "виолончель", "скрипка", "piano", "фортепиано", "рок", "поп", "электронная",
    ],
    "nightlife": [
        "party", "night", "club", "rave", "techno", "house", "dance floor", "bar night",
        "вечеринка", "ночной", "клуб", "рейв", "техно", "дискотека", "бар", "коктейль",
        "nightclub", "afterparty", "афтепати", "мастер-класс бармен", "бармен",
    ],
    "art": [
        "art", "exhibition", "gallery", "museum", "painting", "sculpture",
        "выставка", "галерея", "музей", "искусство", "живопись", "скульптура", "арт",
        "графика", "фотовыставка", "инсталляция", "художник", "художественный",
    ],
    "food": [
        "food", "dinner", "brunch", "wine", "chef", "restaurant", "culinary", "tasting", "gala",
        "еда", "ужин", "бранч", "вино", "шеф", "ресторан", "дегустация", "гастро",
        "пикник", "кулинарный", "винодельня", "пиво", "фестиваль еды", "картофель",
        "черешня", "лаванда", "фермерский", "рынок",
    ],
    "sport": [
        "yoga", "sport", "run", "fitness", "marathon", "tennis", "padel", "surf",
        "йога", "спорт", "бег", "фитнес", "марафон", "теннис", "серфинг", "велопрогулка",
        "велосипед", "заезд", "скейтборд", "скейт", "плавание", "триатлон", "велотур",
    ],
    "networking": [
        "networking", "meetup", "startup", "business", "it party", "tech", "summit",
        "нетворкинг", "митап", "стартап", "бизнес", "технологии", "саммит", "конференция",
        "форум", "питч", "инвестиции", "it", "айти", "разработчик", "девелопер", "релокация",
    ],
    "culture": [
        "book", "lecture", "talk", "theatre", "cinema", "film", "reading", "poetry",
        "книга", "лекция", "театр", "кино", "кинопоказ", "поэзия", "чтение", "клуб",
        "книжный", "дискуссия", "встреча", "разговор", "спектакль", "комедия", "стендап",
    ],
    "kids": [
        "kids", "children", "family", "child", "workshop for kids",
        "дети", "детский", "семейный", "ребёнок", "ребенок", "подростки", "школьники",
        "мастер-класс для детей", "творческий для детей", "летняя программа",
    ],
    "outdoor": [
        "outdoor", "beach", "hiking", "boat", "sea", "sunset", "rooftop", "open air",
        "природа", "пляж", "поход", "яхта", "море", "закат", "крыша", "пикник",
        "горы", "парк", "холм", "лес", "велотрек", "побережье", "заповедник",
    ],
}

def categorize(event: dict) -> str:
    text = (
        (event.get("title") or "") + " " +
        (event.get("full_text") or "") + " " +
        (event.get("venue") or "")
    ).lower()

    scores = {cat: 0 for cat in CATEGORIES}
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"
