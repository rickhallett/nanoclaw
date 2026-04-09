"""SQLite storage for spaced repetition cards.

Schema:
    cards(slug, domain, prompt, answer, created)
    reviews(id, slug, ts, result, interval_days, streak)

SM-2 simplified:
    - fail → interval = 1, streak = 0
    - pass → interval = prev_interval * 2 (min 1, max 60), streak += 1
    - graduated at interval >= 30 days
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from halos.common.paths import store_dir as _store_dir


def _db_path() -> Path:
    return _store_dir() / "drillctl.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            slug TEXT PRIMARY KEY,
            domain TEXT NOT NULL DEFAULT '',
            prompt TEXT NOT NULL DEFAULT '',
            answer TEXT NOT NULL DEFAULT '',
            created TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL,
            ts TEXT NOT NULL,
            result TEXT NOT NULL CHECK(result IN ('pass', 'fail')),
            interval_days REAL NOT NULL DEFAULT 1,
            streak INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(slug) REFERENCES cards(slug)
        )
    """)
    conn.commit()
    return conn


# ── Card management ─────────────────────────────────────────────

def add_card(slug: str, domain: str = "", prompt: str = "", answer: str = "") -> dict:
    """Add or update a card."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = _connect()
    conn.execute("""
        INSERT INTO cards (slug, domain, prompt, answer, created)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            domain=excluded.domain,
            prompt=excluded.prompt,
            answer=excluded.answer
    """, (slug, domain, prompt, answer, now))
    conn.commit()
    row = conn.execute("SELECT * FROM cards WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    return dict(row)


def list_cards(domain: Optional[str] = None) -> list[dict]:
    conn = _connect()
    if domain:
        rows = conn.execute(
            "SELECT * FROM cards WHERE domain = ? ORDER BY slug", (domain,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cards ORDER BY slug").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remove_card(slug: str) -> bool:
    conn = _connect()
    conn.execute("DELETE FROM reviews WHERE slug = ?", (slug,))
    cur = conn.execute("DELETE FROM cards WHERE slug = ?", (slug,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ── Review logging ──────────────────────────────────────────────

def log_review(slug: str, passed: bool) -> dict:
    """Log a review result. Returns the new review state."""
    conn = _connect()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get previous state
    prev = conn.execute("""
        SELECT interval_days, streak FROM reviews
        WHERE slug = ? ORDER BY id DESC LIMIT 1
    """, (slug,)).fetchone()

    if passed:
        if prev:
            new_interval = min(prev["interval_days"] * 2, 60)
            new_streak = prev["streak"] + 1
        else:
            new_interval = 2
            new_streak = 1
    else:
        new_interval = 1
        new_streak = 0

    conn.execute("""
        INSERT INTO reviews (slug, ts, result, interval_days, streak)
        VALUES (?, ?, ?, ?, ?)
    """, (slug, now, "pass" if passed else "fail", new_interval, new_streak))
    conn.commit()

    state = {
        "slug": slug,
        "result": "pass" if passed else "fail",
        "interval_days": new_interval,
        "streak": new_streak,
        "next_due": (datetime.now(timezone.utc) + timedelta(days=new_interval)).strftime("%Y-%m-%d"),
    }
    conn.close()
    return state


# ── Scheduling ──────────────────────────────────────────────────

def get_card_state(slug: str) -> Optional[dict]:
    """Get current spaced-repetition state for a card."""
    conn = _connect()
    card = conn.execute("SELECT * FROM cards WHERE slug = ?", (slug,)).fetchone()
    if not card:
        conn.close()
        return None

    review = conn.execute("""
        SELECT * FROM reviews WHERE slug = ? ORDER BY id DESC LIMIT 1
    """, (slug,)).fetchone()
    conn.close()

    state = dict(card)
    if review:
        last_ts = datetime.fromisoformat(review["ts"].replace("Z", "+00:00"))
        interval = review["interval_days"]
        due = last_ts + timedelta(days=interval)
        state["last_review"] = review["ts"]
        state["last_result"] = review["result"]
        state["interval_days"] = interval
        state["streak"] = review["streak"]
        state["due"] = due.strftime("%Y-%m-%dT%H:%M:%SZ")
        state["graduated"] = interval >= 30
    else:
        state["last_review"] = None
        state["last_result"] = None
        state["interval_days"] = 0
        state["streak"] = 0
        state["due"] = state["created"]  # due immediately
        state["graduated"] = False

    return state


def due_cards(include_new: bool = True) -> list[dict]:
    """Return cards that are due for review today."""
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = _connect()
    all_cards = conn.execute("SELECT slug FROM cards ORDER BY slug").fetchall()
    conn.close()

    due = []
    for row in all_cards:
        state = get_card_state(row["slug"])
        if not state:
            continue
        if state["graduated"]:
            continue
        # New cards only appear when explicitly requested
        if state["last_review"] is None:
            if include_new:
                due.append(state)
        elif state["due"] <= now_str:
            due.append(state)

    # Sort: fails first, then by due date
    due.sort(key=lambda s: (s["streak"], s["due"]))
    return due


def stats() -> dict:
    """Overall drill statistics."""
    conn = _connect()
    total_cards = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    total_reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    passes = conn.execute("SELECT COUNT(*) FROM reviews WHERE result='pass'").fetchone()[0]
    fails = conn.execute("SELECT COUNT(*) FROM reviews WHERE result='fail'").fetchone()[0]
    conn.close()

    all_cards = list_cards()
    states = [get_card_state(c["slug"]) for c in all_cards]
    states = [s for s in states if s]

    graduated = sum(1 for s in states if s["graduated"])
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    due_count = sum(1 for s in states if not s["graduated"] and s["due"] <= now_str)
    new_count = sum(1 for s in states if s["last_review"] is None)

    return {
        "total_cards": total_cards,
        "total_reviews": total_reviews,
        "passes": passes,
        "fails": fails,
        "pass_rate": round(passes / total_reviews * 100, 1) if total_reviews else 0,
        "graduated": graduated,
        "due_today": due_count,
        "new_unseen": new_count,
    }
