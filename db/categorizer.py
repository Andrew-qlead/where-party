# keyword → (category, weight)
# weight 2 = сильный сигнал, 1 = слабый
KEYWORDS = {
    # MUSIC
    "dj": ("nightlife", 2), "dj-": ("nightlife", 2),
    "concert": ("music", 2), "концерт": ("music", 2),
    "live music": ("music", 2), "живая музыка": ("music", 2),
    "orchestra": ("music", 2), "оркестр": ("music", 2),
    "jazz": ("music", 2), "джаз": ("music", 2),
    "saxophone": ("music", 2), "saxofon": ("music", 2), "саксофон": ("music", 2),
    "piano": ("music", 2), "фортепиано": ("music", 2),
    "violin": ("music", 2), "скрипка": ("music", 2),
    "cello": ("music", 2), "виолончель": ("music", 2),
    "choir": ("music", 2), "хор": ("music", 2),
    "opera": ("music", 2), "опера": ("music", 2),
    "classical": ("music", 2), "классическая": ("music", 2),
    "philharmonic": ("music", 2), "филармония": ("music", 2),
    "band": ("music", 1), "группа": ("music", 1),
    "vocalist": ("music", 1), "вокал": ("music", 1),
    "musician": ("music", 1), "музыкант": ("music", 1),
    "музыка": ("music", 1),
    "festival of music": ("music", 2), "music festival": ("music", 2),
    "festival": ("music", 1), "фестиваль": ("music", 1),
    "live": ("music", 1), "лайв": ("music", 1),
    "музыкальный вечер": ("music", 2), "music evening": ("music", 2),

    # NIGHTLIFE
    "nightclub": ("nightlife", 2), "ночной клуб": ("nightlife", 2),
    "rave": ("nightlife", 2), "рейв": ("nightlife", 2),
    "techno": ("nightlife", 2), "техно": ("nightlife", 2),
    "house music": ("nightlife", 2),
    "dance floor": ("nightlife", 2),
    "afterparty": ("nightlife", 2), "афтепати": ("nightlife", 2),
    "club night": ("nightlife", 2), "ночная вечеринка": ("nightlife", 2),
    "вечеринка": ("nightlife", 2), "party": ("nightlife", 2),
    "dj set": ("nightlife", 2), "dj-сет": ("nightlife", 2),
    "dj night": ("nightlife", 2),
    "salsa night": ("nightlife", 2), "latin night": ("nightlife", 2),
    "ladies night": ("nightlife", 2),
    "disco": ("nightlife", 2), "дискотека": ("nightlife", 2),
    "bar night": ("nightlife", 1),
    "коктейль": ("nightlife", 1),
    "дискотека": ("nightlife", 2),

    # ART
    "exhibition": ("art", 2), "выставка": ("art", 2),
    "gallery": ("art", 2), "галерея": ("art", 2),
    "painting": ("art", 2), "живопись": ("art", 2),
    "sculpture": ("art", 2), "скульптура": ("art", 2),
    "installation": ("art", 2), "инсталляция": ("art", 2),
    "vernissage": ("art", 2), "вернисаж": ("art", 2),
    "photography exhibition": ("art", 2), "фотовыставка": ("art", 2),
    "art show": ("art", 2), "арт-шоу": ("art", 2),
    "artist": ("art", 1), "художник": ("art", 1),
    "museum": ("art", 1), "музей": ("art", 1),

    # FOOD & WINE
    "wine tasting": ("food", 2), "дегустация вина": ("food", 2),
    "food festival": ("food", 2), "фестиваль еды": ("food", 2),
    "street food": ("food", 2), "стрит-фуд": ("food", 2),
    "culinary": ("food", 2), "кулинарный": ("food", 2),
    "gala dinner": ("food", 2), "гала-ужин": ("food", 2),
    "brunch": ("food", 2), "бранч": ("food", 2),
    "winery": ("food", 2), "винодельня": ("food", 2),
    "wine": ("food", 1), "вино": ("food", 1),
    "beer festival": ("food", 2), "пивной фестиваль": ("food", 2),
    "chef": ("food", 1), "шеф": ("food", 1),
    "tasting": ("food", 1), "дегустация": ("food", 1),
    "dinner": ("food", 1), "ужин": ("food", 1),
    "farmers market": ("food", 2), "фермерский рынок": ("food", 2),
    "lavender festival": ("food", 2), "лавандовый фестиваль": ("food", 2),
    "cherry festival": ("food", 2), "черешневый фестиваль": ("food", 2),

    # SPORT
    "regatta": ("sport", 2), "регата": ("sport", 2),
    "sailing race": ("sport", 2), "yacht race": ("sport", 2),
    "sailing": ("sport", 1), "парусный": ("sport", 1),
    "marathon": ("sport", 2), "марафон": ("sport", 2),
    "triathlon": ("sport", 2), "триатлон": ("sport", 2),
    "yoga": ("sport", 2), "йога": ("sport", 2),
    "padel": ("sport", 2), "падел": ("sport", 2),
    "tennis": ("sport", 2), "теннис": ("sport", 2),
    "cycling": ("sport", 2), "велопрогулка": ("sport", 2), "велотур": ("sport", 2),
    "surf": ("sport", 2), "серфинг": ("sport", 2),
    "swimming": ("sport", 2), "плавание": ("sport", 2),
    "football": ("sport", 2), "футбол": ("sport", 2),
    "basketball": ("sport", 2), "баскетбол": ("sport", 2),
    "skateboard": ("sport", 2), "скейтборд": ("sport", 2),
    "fitness": ("sport", 1), "фитнес": ("sport", 1),
    "tournament": ("sport", 1), "турнир": ("sport", 1),
    "race": ("sport", 1), "забег": ("sport", 1),
    "run": ("sport", 1), "бег": ("sport", 1),
    "workout": ("sport", 1), "тренировка": ("sport", 1),

    # NETWORKING
    "networking": ("networking", 2), "нетворкинг": ("networking", 2),
    "startup": ("networking", 2), "стартап": ("networking", 2),
    "pitch": ("networking", 2), "питч": ("networking", 2),
    "summit": ("networking", 2), "саммит": ("networking", 2),
    "conference": ("networking", 2), "конференция": ("networking", 2),
    "tech meetup": ("networking", 2), "tech event": ("networking", 2),
    "business forum": ("networking", 2), "бизнес-форум": ("networking", 2),
    "investors": ("networking", 2), "инвесторы": ("networking", 2),
    "meetup": ("networking", 1), "митап": ("networking", 1),
    "it party": ("networking", 2), "it meetup": ("networking", 2),
    "hackathon": ("networking", 2), "хакатон": ("networking", 2),
    "релокация": ("networking", 1),

    # CULTURE
    "workshop": ("culture", 2), "мастер-класс": ("culture", 2), "masterclass": ("culture", 2),
    "master class": ("culture", 2), "воркшоп": ("culture", 2),
    "charity": ("culture", 2), "благотворительн": ("culture", 2),
    "paint": ("culture", 1), "рисование": ("culture", 1),
    "craft": ("culture", 1), "творческий": ("culture", 1),
    "рукоделие": ("culture", 2), "рукодели": ("culture", 2),
    "наследие": ("culture", 1), "heritage": ("culture", 1),
    "поэтическ": ("culture", 2), "поэзия": ("culture", 2),
    "вечер встреч": ("culture", 2), "цикл встреч": ("culture", 2),
    "show": ("culture", 1), "шоу": ("culture", 2),
    "dog show": ("outdoor", 2), "dog fest": ("outdoor", 2),
    "автошоу": ("outdoor", 2), "автомобильный праздник": ("outdoor", 2),
    "car show": ("outdoor", 2), "car festival": ("outdoor", 2),
    "праздник": ("culture", 1), "celebration": ("culture", 1),
    "квест": ("culture", 2), "quest": ("culture", 2),
    "escape room": ("culture", 2),
    "theatre": ("culture", 2), "theater": ("culture", 2),
    "театр": ("culture", 2), "спектакль": ("culture", 2),
    "stand-up": ("culture", 2), "стендап": ("culture", 2), "stand up": ("culture", 2),
    "comedy show": ("culture", 2), "comedy night": ("culture", 2),
    "improv": ("culture", 2), "импровизация": ("culture", 2),
    "poetry": ("culture", 2), "поэзия": ("culture", 2),
    "poetry evening": ("culture", 2), "вечер поэзии": ("culture", 2),
    "book club": ("culture", 2), "книжный клуб": ("culture", 2),
    "lecture": ("culture", 2), "лекция": ("culture", 2),
    "talk": ("culture", 1), "дискуссия": ("culture", 1),
    "film screening": ("culture", 2), "кинопоказ": ("culture", 2),
    "cinema": ("culture", 2), "кино": ("culture", 2),
    "open air cinema": ("culture", 2),
    "documentary": ("culture", 2), "документальный": ("culture", 2),
    "reading": ("culture", 1), "чтение": ("culture", 1),
    "literary": ("culture", 2), "литературный": ("culture", 2),
    "drama": ("culture", 2), "драма": ("culture", 2),
    "greek drama": ("culture", 2),
    "performance": ("culture", 1), "перформанс": ("culture", 1),

    # KIDS
    "kids workshop": ("kids", 2), "children workshop": ("kids", 2),
    "workshop for kids": ("kids", 2), "мастер-класс для детей": ("kids", 2),
    "family day": ("kids", 2), "семейный день": ("kids", 2),
    "kids": ("kids", 2), "children": ("kids", 2),
    "дети": ("kids", 2), "детский": ("kids", 2),
    "family fun": ("kids", 2), "семейный праздник": ("kids", 2),
    "summer camp": ("kids", 2), "летний лагерь": ("kids", 2),
    "animation for kids": ("kids", 2),
    "puppets": ("kids", 2), "кукольный": ("kids", 2),

    # OUTDOOR
    "open water": ("outdoor", 2), "night run": ("outdoor", 2), "night race": ("outdoor", 2),
    "trail run": ("outdoor", 2), "trail": ("outdoor", 1),
    "wine walk": ("outdoor", 2), "city walk": ("outdoor", 2),
    "hiking": ("outdoor", 2), "поход": ("outdoor", 2), "хайкинг": ("outdoor", 2),
    "boat trip": ("outdoor", 2), "яхтенная прогулка": ("outdoor", 2),
    "sunset cruise": ("outdoor", 2), "sunset boat": ("outdoor", 2),
    "open air": ("outdoor", 2), "опен эйр": ("outdoor", 2),
    "beach party": ("outdoor", 2),
    "beach event": ("outdoor", 2),
    "rooftop": ("outdoor", 2), "крыша": ("outdoor", 2),
    "nature walk": ("outdoor", 2), "прогулка": ("outdoor", 1),
    "mountain": ("outdoor", 2), "горы": ("outdoor", 2), "троодос": ("outdoor", 2),
    "troodos": ("outdoor", 2),
    "forest": ("outdoor", 2), "лес": ("outdoor", 2),
    "park event": ("outdoor", 2),
    "sea": ("outdoor", 1), "море": ("outdoor", 1),
    "beach": ("outdoor", 1), "пляж": ("outdoor", 1),
    "sunset": ("outdoor", 1), "закат": ("outdoor", 1),
    "outdoor": ("outdoor", 2), "природа": ("outdoor", 2),
    "kayak": ("outdoor", 2), "каяк": ("outdoor", 2),
    "diving": ("outdoor", 2), "дайвинг": ("outdoor", 2),
}

CATEGORIES = list({v[0] for v in KEYWORDS.values()})


def categorize(event: dict) -> str:
    title = (event.get("title") or "").lower()
    body = (event.get("full_text") or "").lower()
    venue = (event.get("venue") or "").lower()

    # Заголовок весит в 3 раза больше тела
    scores: dict[str, float] = {}

    for kw, (cat, w) in KEYWORDS.items():
        if kw in title:
            scores[cat] = scores.get(cat, 0) + w * 3
        elif kw in body or kw in venue:
            scores[cat] = scores.get(cat, 0) + w

    if not scores:
        return "other"

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"
