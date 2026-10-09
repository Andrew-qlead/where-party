"""
Noise-фильтр событий: отсекает новости, некрологи, ДТП, политику, спорт-результаты
и прочий не-афишный шум. Раньше жил в web_parser.py; вынесен отдельно, потому что
источники, кроме Instagram, удалены, а main.py по-прежнему использует NOISE_PHRASES
и _quality_score для финальной чистки.
"""

NOISE_PHRASES = [
    # ── СМЕРТЬ / НЕКРОЛОГИ ───────────────────────────────────────────────────
    "dies at", "died at", "passed away", "obituary", "in memoriam", "funeral",
    "was laid to rest", "memorial service", "condolences", "in loving memory",
    "tragic death", "tragic accident", "died on a flight", "died suddenly",
    "man died", "woman died", "child died", "person died", "people died",
    "body found", "bodies found", "found dead", "dead body",
    "тело найдено", "обнаружено тело", "найден мёртвым", "найдена мёртвой",
    "скончался", "скончалась", "скончались", "скончалась в",
    "умер ", "умерла ", "умер на", "умерла на", "умерли",
    "погиб в", "погиб на", "погибла", "погибли", "погибших",
    "гибель", "смерть", "смерти", "похороны", "некролог",
    "прощание с", "вечная память", "светлая память",
    "in memory of", "rip ", "rest in peace",

    # ── АВАРИИ / ДТП / КАТАСТРОФЫ ────────────────────────────────────────────
    "road fatalities", "road deaths", "road accident", "traffic accident",
    "car crash", "fatal crash", "killed in", "died in", "fatalities",
    "road safety report", "etsc", "per cent reduction",
    "записи скорой", "дтп", "авария на", "автобус протаранил",
    "столкновение", "наезд", "лобовое столкновение",
    "crash victims", "crash kills", "crash injures", "multi-car",
    "pile-up", "overturned", "fell off", "плавсредство",
    "train crash", "plane crash", "авиакатастрофа", "крушение",

    # ── ПОЖАРЫ / СТИХИЙНЫЕ БЕДСТВИЯ ─────────────────────────────────────────
    "пожар в", "пожар на", "лесной пожар", "пожар уничтожил",
    "вспыхнул пожар", "удалось потушить", "загорелся", "загорелась",
    "fire brought under control", "fire destroys", "fire kills",
    "wildfire", "bushfire", "forest fire", "building fire",
    "flood", "flooding", "earthquake", "tsunami", "hurricane", "tornado",
    "наводнение", "землетрясение", "оползень", "ураган",

    # ── ПРЕСТУПНОСТЬ / АРЕСТЫ / СУДЫ ─────────────────────────────────────────
    "arrested", "men arrested", "woman arrested", "man arrested",
    "police seize", "police arrest", "police find", "drug bust",
    "seized", "confiscated", "задержан", "задержана", "задержаны",
    "арестован", "арестована", "арестованы",
    "обыск", "уголовное дело", "осуждён", "осуждена", "приговор",
    "under arrest", "in custody", "charged with", "pleaded guilty",
    "convicted", "sentenced", "verdict", "acquitted",
    "judge orders", "stand trial", "bars her from", "man to face trial",
    "murder trial", "murder charge", "court ruling",
    "наркотики", "наркоторговля", "контрабанда",

    # ── НАСИЛИЕ / ПРЕСТУПЛЕНИЯ ────────────────────────────────────────────────
    "stabbing", "shooting", "gunshot", "gunfire", "bomb", "explosion",
    "attack on", "armed robbery", "robbery", "assault", "rape",
    "нападение", "убийство", "ограбление", "избиение", "теракт",
    "acts committed in the name", "name of revenge",
    "mass shooting", "knife attack", "acid attack",

    # ── ПОЛИТИКА / ПРАВИТЕЛЬСТВО ──────────────────────────────────────────────
    "election", "elections", "parliament", "prime minister",
    "president orders", "government", "minister", "ministry",
    "ceasefire", "war ", "conflict", "troops", "military operation",
    "protest", "rally", "demonstration", "митинг", "акция протеста",
    "erdogan", "trump", "nato", "biden", "putin", "zelensky", "macron",
    "orders talks", "turkish president", "orders officials",
    "diplomatic", "sanctions", "foreign minister",
    "white house", "kremlin", "pentagon", "european commission",
    "european parliament", "european council", "european union votes",
    "united nations", "un resolution", "security council",
    "выборы", "парламент", "правительство", "президент подписал",
    "министр", "премьер-министр", "политика", "партия",

    # ── НЕКРОЛОГИ / ПАМЯТНЫЕ ДАТЫ ─────────────────────────────────────────────
    "памятные мероприятия", "годовщине начала", "великой отечест",
    "годовщина трагедии", "день победы", "anniversary of the",
    "памятные мероприятия к",
    "семинар памяти", "seminary",

    # ── ПОГОДА / КЛИМАТ ───────────────────────────────────────────────────────
    "heat wave", "heat dome", "extreme heat", "deadly furnace",
    "prolonged extreme", "faces prolonged", "braces for",
    "meteorolog", "weather forecast", "погода на", "прогноз погоды",
    "осадки", "облачность", "isolated showers", "thunderstorms",
    "cloud cover", "mostly clear", "turns europe into",
    "temperature", "degrees celsius", "degrees fahrenheit",
    "global warming", "climate change", "климатический",

    # ── БОЛЕЗНИ / МЕДИЦИНА / ЭПИДЕМИИ ────────────────────────────────────────
    "outbreak", "epidemic", "pandemic", "вспышка", "заражение",
    "инфекция", "вирус распростран", "случаев заражения",
    "suicide", "суицид", "самоубийство",
    "hospital", "hospitalized", "госпитализирован",
    "overdose", "передозировка",

    # ── СПОРТИВНЫЕ НОВОСТИ (РЕЗУЛЬТАТЫ, ТРАНСФЕРЫ) ───────────────────────────
    "breaks record", "world record", "championship parade",
    "wake-up call", "knicks", "nba", "premier league", "super rugby",
    "transfer", "signing ", "squad", "coach sacked", "coach fired",
    "thrash", "scores twice", "ten-man", "hosts promoted",
    "lodge fifa", "hurricanes thrash", "world cup", "paralympic",
    "ronaldo", "messi", "arsenal", "manchester united", "manchester city",
    "barcelona", "real madrid", "chelsea", "liverpool", "juventus",
    "group a:", "group b:", "group c:", "group d:", "match report",
    "half-time", "full-time", "final score", "injury time",

    # ── ФИНАНСЫ / ЭКОНОМИКА ───────────────────────────────────────────────────
    "stock market", "shares fell", "shares rose", "nasdaq", "dow jones",
    "crypto crash", "bitcoin price", "inflation", "interest rate",
    "central bank", "gdp", "recession", "фондовый рынок", "акции упали",
    "биржа", "курс доллара", "курс евро", "инфляция",

    # ── МОШЕННИЧЕСТВО / СПАМ ─────────────────────────────────────────────────
    "мошенничество от имени", "налоговой службы",
    "resource networking club", "закрытая встреча для инвесторов",
    "иммиграционными экспертами",
    "phishing", "scam", "fraud alert",

    # ── НОВОСТНЫЕ ДАЙДЖЕСТЫ ───────────────────────────────────────────────────
    "утренний обзор", "вечерний обзор", "morning news review",
    "evening news review", "обзор новостей", "news review",
    "дайджест новостей", "новости дня", "morning digest", "evening digest",
    "weekly roundup", "daily briefing", "today in news",
    "top stories", "breaking news", "latest news",
    "новости кипра за", "главные новости",

    # ── РЕПОРТАЖИ О ПРОШЕДШИХ СОБЫТИЯХ (не анонсы) ───────────────────────────
    "фотографии с", "фото с праздно", "last wednesday we celebrated",
    "it was a very enjoyable", "everyone had a great time",
    "отпраздновали", "праздновали вместе",
    "photos from", "recap of", "highlights from",
    "review of the", "look back at", "обзор прошедшего",

    # ── НЕДВИЖИМОСТЬ / СТРОИТЕЛЬСТВО (новости, не события) ───────────────────
    "property prices", "real estate market", "housing market",
    "construction permit", "building permit",
    "цены на недвижимость", "рынок недвижимости",

    # ── МИГРАЦИЯ / ВИЗЫ / ПОЛИТИКА ────────────────────────────────────────────
    "asylum seekers", "migrants", "migration crisis", "border control",
    "visa policy", "deportation", "мигранты", "беженцы", "депортация",
    "нелегальные", "просители убежища",

    # ── РЕЛИГИЯ (новости, не мероприятия) ────────────────────────────────────
    "archbishop", "bishop", "church condemns", "synod", "holy war",
    "архиепископ", "митрополит", "патриарх",
]


def _quality_score(event: dict) -> int:
    """Оценка качества события 0-4. Берём только если >= 1."""
    score = 0
    text = (event.get("title", "") + " " + event.get("full_text", "")).lower()
    if event.get("date"):
        score += 1
    if event.get("url"):
        score += 1
    if any(w in text for w in ["cyprus", "кипр", "limassol", "nicosia", "larnaca", "paphos"]):
        score += 1
    if any(w in text for w in ["ticket", "entrance", "admission", "free", "€", "price",
                                 "вход", "билет", "бесплатно", "цена"]):
        score += 1
    return score
