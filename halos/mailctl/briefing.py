"""briefing — mailctl integration for morning/nightly briefings.

Produces one-line summaries of inbox state for hal-briefing consumption.
"""

from . import engine
from .engine import HimalayaError


def text_summary() -> str:
    """One-line inbox summary for briefing integration.

    Format: "mailctl: 12 unread (3 from ben, 2 from github) | 247 total"
    """
    try:
        messages = engine.list_messages(folder="INBOX", page_size=100)
    except HimalayaError:
        return "mailctl: unavailable (himalaya error)"

    if not messages:
        return "mailctl: inbox empty"

    total = len(messages)
    unread = [m for m in messages if "Seen" not in m.get("flags", [])]
    unread_count = len(unread)

    # Top senders among unread
    sender_counts: dict[str, int] = {}
    for m in unread:
        sender = m.get("from", {}).get("name") or m.get("from", {}).get("addr", "unknown")
        sender_counts[sender] = sender_counts.get(sender, 0) + 1

    top = sorted(sender_counts.items(), key=lambda x: -x[1])[:3]
    top_str = ", ".join(f"{count} from {name}" for name, count in top)

    parts = [f"mailctl: {unread_count} unread"]
    if top_str:
        parts[0] += f" ({top_str})"
    parts.append(f"{total} in inbox")

    return " | ".join(parts)
