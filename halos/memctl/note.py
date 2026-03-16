import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import yaml


@dataclass
class Note:
    id: str = ""
    title: str = ""
    type: str = ""
    tags: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    backlinks: list[str] = field(default_factory=list)
    confidence: str = "high"
    created: str = ""
    modified: str = ""
    expires: str | None = None
    body: str = ""


_NON_ALPHA = re.compile(r"[^a-z0-9]+")
_TRIM_DASH = re.compile(r"^-+|-+$")


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = _NON_ALPHA.sub("-", s)
    s = _TRIM_DASH.sub("", s)
    if not s:
        return "untitled"
    if len(s) > 60:
        s = _TRIM_DASH.sub("", s[:60])
    return s


def filename(id: str, title: str) -> str:
    return f"{id}-{slugify(title)}.md"


def parse(data: str) -> Note:
    parts = data.split("---", 2)
    if len(parts) < 3:
        raise ValueError("missing YAML frontmatter delimiters")

    front = yaml.safe_load(parts[1])
    if not front:
        raise ValueError("empty frontmatter")

    return Note(
        id=str(front.get("id", "")),
        title=front.get("title", ""),
        type=front.get("type", ""),
        tags=front.get("tags", []) or [],
        entities=front.get("entities", []) or [],
        backlinks=front.get("backlinks", []) or [],
        confidence=front.get("confidence", "high"),
        created=str(front.get("created", "")),
        modified=str(front.get("modified", "")),
        expires=front.get("expires"),
        body=parts[2].strip(),
    )


def marshal(n: Note) -> str:
    front = {
        "id": n.id,
        "title": n.title,
        "type": n.type,
        "tags": n.tags,
    }
    if n.entities:
        front["entities"] = n.entities
    if n.backlinks:
        front["backlinks"] = n.backlinks
    front["confidence"] = n.confidence
    front["created"] = n.created
    front["modified"] = n.modified
    front["expires"] = n.expires

    text = yaml.dump(front, default_flow_style=False, sort_keys=False, allow_unicode=True)
    lines = ["---", text.rstrip(), "---", "", n.body, ""]
    return "\n".join(lines)


def validate(n: Note, valid_types: list[str], valid_confidence: list[str]) -> list[str]:
    errs = []
    if not n.title:
        errs.append("title is required")
    if not n.type:
        errs.append("type is required")
    elif n.type not in valid_types:
        errs.append(f"invalid type {n.type!r}, valid: {valid_types}")
    if not n.tags:
        errs.append("at least one tag is required")
    if not n.confidence:
        errs.append("confidence is required")
    elif n.confidence not in valid_confidence:
        errs.append(f"invalid confidence {n.confidence!r}, valid: {valid_confidence}")
    if not n.body:
        errs.append("body is required")
    return errs


def now_id() -> str:
    """Generate a unique ID from current timestamp with millisecond precision."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d-%H%M%S") + f"-{now.microsecond // 1000:03d}"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
