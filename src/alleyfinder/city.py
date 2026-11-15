def normalize_city(raw: str) -> str:
    text = (raw or "").strip()
    if text.endswith("市"):
        text = text[:-1]
    return text.strip()
