"""IPC message delivery — writes JSON files for NanoClaw to pick up."""
import json
import os
import time
from pathlib import Path

from .config import Config


def deliver_message(cfg: Config, text: str) -> Path:
    """Write an IPC message JSON for NanoClaw to send via Telegram.

    Returns the path of the written file.
    """
    if not cfg.chat_jid:
        raise RuntimeError(
            "No chat_jid configured — set it in briefings.yaml or ensure "
            "a main group is registered in the NanoClaw database"
        )

    messages_dir = cfg.ipc_dir / cfg.ipc_group / "messages"
    messages_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "type": "message",
        "chatJid": cfg.chat_jid,
        "text": text,
    }

    # Timestamped filename to avoid collisions
    filename = f"briefing-{int(time.time() * 1000)}.json"
    filepath = messages_dir / filename

    # Atomic write: write to tmp then rename
    tmp = filepath.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(str(tmp), str(filepath))

    return filepath
