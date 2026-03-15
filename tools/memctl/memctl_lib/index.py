import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import note as notemod


@dataclass
class Entry:
    id: str = ""
    file: str = ""
    title: str = ""
    type: str = ""
    tags: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    summary: str = ""
    hash: str = ""
    backlink_count: int = 0
    modified: str = ""
    expires: str | None = None

    def to_dict(self) -> dict:
        d = {
            "id": self.id, "file": self.file, "title": self.title,
            "type": self.type, "tags": self.tags,
        }
        if self.entities:
            d["entities"] = self.entities
        d["summary"] = self.summary
        d["hash"] = self.hash
        d["backlink_count"] = self.backlink_count
        d["modified"] = self.modified
        d["expires"] = self.expires
        return d


@dataclass
class Index:
    generated: str = ""
    note_count: int = 0
    entities: list[str] = field(default_factory=list)
    tag_vocabulary: list[str] = field(default_factory=list)
    notes: list[Entry] = field(default_factory=list)


@dataclass
class VerifyResult:
    id: str
    file: str
    status: str  # MATCH, DRIFT, MISSING


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: str) -> str:
    return hash_bytes(Path(path).read_bytes())


LOOKUP_PROTOCOL = """# MEMORY INDEX
<!-- AUTO-MAINTAINED BY memctl — DO NOT HAND-EDIT THE YAML BLOCK -->
<!-- Run: memctl index verify   to check for drift              -->
<!-- Run: memctl index rebuild  to regenerate from notes corpus -->

## LOOKUP PROTOCOL

When answering a question that may depend on stored memory:

1. Parse MEMORY_INDEX below. Identify candidate notes by:
   a. entity intersection (does the query mention a known entity?)
   b. tag intersection (does the query map to known tags?)
   c. type filter (decisions? facts? people?)

2. For each candidate, check: does the hash in the index match
   the file? If not, flag drift and re-read the file directly.
   Run `memctl index verify` to surface all drift.

3. Load only the matching note files. Do not load the full corpus.

4. If no candidates match, say so. Do not hallucinate memory.

5. To write a new note: call `memctl new` with structured args.
   Do not write to memory files directly.

6. A note with type=decision is treated as authoritative.
   A note with confidence=low should be stated with uncertainty.
   A note with an expires date in the past should be treated as stale.

## HOW TO USE MEMORY

### Writing a note
Always use memctl. Never write to memory files directly.

```
memctl new \\
  --title "Short factual title" \\
  --type [decision|fact|reference|project|person|event] \\
  --tags tag1,tag2 \\
  --entities entity1,entity2 \\
  --confidence [high|medium|low] \\
  --body "Single claim. One sentence if possible."
```

One claim per note. If you need to record two things, run memctl new twice.
Use --link-to <id> if the new note references an existing one.

### What you must not do
- Do not hand-edit CLAUDE.md or any note file
- Do not invent backlinks — use memctl link
- Do not prune or archive notes — that is a scripted job
- Do not write notes with multiple claims

"""


def write(path: str, idx: Index) -> None:
    idx.generated = notemod.now_iso()
    index_dict = {
        "generated": idx.generated,
        "note_count": idx.note_count,
    }
    if idx.entities:
        index_dict["entities"] = idx.entities
    if idx.tag_vocabulary:
        index_dict["tag_vocabulary"] = idx.tag_vocabulary
    index_dict["notes"] = [n.to_dict() for n in idx.notes]

    yaml_block = yaml.dump(index_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)

    content = LOOKUP_PROTOCOL + "## MEMORY_INDEX\n```yaml\n" + yaml_block + "```\n"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content)


def read(path: str) -> Index:
    if not Path(path).exists():
        return Index()

    content = Path(path).read_text()
    start = content.find("```yaml\n")
    if start == -1:
        return Index()
    start += len("```yaml\n")

    end = content.find("```", start)
    if end == -1:
        raise ValueError(f"unterminated YAML block in {path}")

    raw = yaml.safe_load(content[start:end])
    if not raw:
        return Index()

    entries = []
    for n in raw.get("notes", []):
        entries.append(Entry(
            id=str(n.get("id", "")),
            file=n.get("file", ""),
            title=n.get("title", ""),
            type=n.get("type", ""),
            tags=n.get("tags", []) or [],
            entities=n.get("entities", []) or [],
            summary=n.get("summary", ""),
            hash=n.get("hash", ""),
            backlink_count=n.get("backlink_count", 0),
            modified=n.get("modified", ""),
            expires=n.get("expires"),
        ))

    return Index(
        generated=raw.get("generated", ""),
        note_count=raw.get("note_count", 0),
        entities=raw.get("entities", []) or [],
        tag_vocabulary=raw.get("tag_vocabulary", []) or [],
        notes=entries,
    )


def verify(entries: list[Entry]) -> list[VerifyResult]:
    results = []
    for e in entries:
        if not Path(e.file).exists():
            results.append(VerifyResult(e.id, e.file, "MISSING"))
            continue
        h = hash_file(e.file)
        status = "MATCH" if h == e.hash else "DRIFT"
        results.append(VerifyResult(e.id, e.file, status))
    return results


def collect_entities(entries: list[Entry]) -> list[str]:
    seen = set()
    result = []
    for e in entries:
        for ent in e.entities:
            if ent not in seen:
                seen.add(ent)
                result.append(ent)
    return result


def rebuild_from_notes(notes_dir: str, max_summary: int) -> list[Entry]:
    entries = []
    notes_path = Path(notes_dir)
    if not notes_path.exists():
        return entries

    for f in sorted(notes_path.iterdir()):
        if f.suffix != ".md":
            continue
        try:
            data = f.read_text()
            n = notemod.parse(data)
            summary = n.body[:max_summary] + "..." if len(n.body) > max_summary else n.body
            rel_path = str(f)
            entries.append(Entry(
                id=n.id, file=rel_path, title=n.title, type=n.type,
                tags=n.tags, entities=n.entities, summary=summary,
                hash=hash_bytes(f.read_bytes()),
                backlink_count=len(n.backlinks), modified=n.modified,
                expires=n.expires,
            ))
        except Exception:
            continue  # skip unparseable files
    return entries
