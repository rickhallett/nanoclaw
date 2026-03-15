import math


def score(backlinks: int, days_since_modified: float, half_life: int) -> float:
    recency = math.exp(-days_since_modified / half_life)
    if backlinks == 0:
        return recency * 0.5
    return backlinks * recency


def is_exempt(note_type: str, backlinks: int, min_backlinks_to_exempt: int) -> bool:
    if note_type in ("decision", "person"):
        return True
    return backlinks >= min_backlinks_to_exempt
