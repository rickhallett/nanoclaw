"""changoctl engine — sustain ritual, mood logic, and briefing surface.

The sustain command is the signature interaction: resolve mood, pick item,
consume, pair with quote, return formatted atmospheric action.
"""

from pathlib import Path
from typing import Optional

from .config import MOOD_ITEM_MAP, MOOD_CATEGORY_MAP, VALID_MOODS
from . import store
from .flavour import random_action


def sustain(
    mood: str,
    session_context: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Full sustain ritual. Returns dict with all components.

    Keys: item, stock, mood, action, quote, out_of_stock, formatted, log_entry.
    """
    if mood not in VALID_MOODS:
        raise ValueError(f"invalid mood: {mood!r} (must be one of {VALID_MOODS})")

    primary_item = MOOD_ITEM_MAP[mood]
    primary_stock = store.get_stock(primary_item, db_path=db_path)

    if primary_stock > 0:
        chosen_item = primary_item
    else:
        inventory = store.get_inventory(db_path=db_path)
        fallback = [i for i in inventory if i["stock"] > 0]
        if fallback:
            chosen_item = fallback[0]["item"]
        else:
            chosen_item = primary_item

    result = store.consume(
        chosen_item, mood=mood, session_context=session_context, db_path=db_path
    )

    action = random_action(chosen_item)

    category = MOOD_CATEGORY_MAP[mood]
    quote = store.random_quote(category=category, db_path=db_path)

    formatted = _format_sustain(action, quote, chosen_item, result["stock"], mood)

    return {
        "item": chosen_item,
        "stock": result["stock"],
        "mood": mood,
        "action": action,
        "quote": quote,
        "out_of_stock": result["out_of_stock"],
        "formatted": formatted,
        "log_entry": result["log_entry"],
    }


def _format_sustain(
    action: str,
    quote: Optional[dict],
    item: str,
    stock: int,
    mood: str,
) -> str:
    """Format the sustain output: action + quote + status line."""
    parts = [action, ""]

    if quote:
        parts.append(f'"{quote["text"]}"')
        parts.append("")

    remaining = f"{stock} remaining" if stock > 0 else "EMPTY -- restock"
    parts.append(f"[{item}: {remaining} | mood: {mood}]")

    return "\n".join(parts)


def text_summary(db_path: Optional[Path] = None) -> str:
    """One-line summary for briefing integration.

    Example: "changoctl: espresso: 5, lagavulin: 2, stimpacks: 0, nos: 3 | 12 quotes"
    """
    inventory = store.get_inventory(db_path=db_path)
    quote_count = store.count_quotes(db_path=db_path)

    stock_parts = [f"{i['item']}: {i['stock']}" for i in inventory]
    stock_str = ", ".join(stock_parts)

    q_label = "quote" if quote_count == 1 else "quotes"
    return f"changoctl: {stock_str} | {quote_count} {q_label}"
