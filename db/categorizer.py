CATEGORIES = {
    "music":       ["music", "concert", "festival", "jazz", "dj", "live music", "band", "orchestra"],
    "nightlife":   ["party", "night", "club", "rave", "techno", "house", "dance floor", "bar night"],
    "art":         ["art", "exhibition", "gallery", "museum", "выставка", "painting", "sculpture"],
    "food":        ["food", "dinner", "brunch", "wine", "chef", "restaurant", "culinary", "tasting", "gala"],
    "sport":       ["yoga", "sport", "run", "fitness", "marathon", "tennis", "padel", "surf"],
    "networking":  ["networking", "meetup", "startup", "business", "it party", "tech", "summit"],
    "culture":     ["book", "lecture", "talk", "theatre", "cinema", "film", "reading", "poetry"],
    "kids":        ["kids", "children", "family", "child", "workshop for kids"],
    "outdoor":     ["outdoor", "beach", "hiking", "boat", "sea", "sunset", "rooftop", "open air"],
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
