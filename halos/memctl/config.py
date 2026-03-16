import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DEFAULT_TYPES = ["decision", "fact", "reference", "project", "person", "event"]
_DEFAULT_CONFIDENCE = ["high", "medium", "low"]


@dataclass
class NoteConfig:
    tags: list[str] = field(default_factory=list)
    valid_types: list[str] = field(default_factory=lambda: list(_DEFAULT_TYPES))
    valid_confidence: list[str] = field(default_factory=lambda: list(_DEFAULT_CONFIDENCE))


@dataclass
class IndexConfig:
    max_summary_chars: int = 120
    hash_algorithm: str = "sha256"


@dataclass
class EnrichConfig:
    noise_tags: list[str] = field(default_factory=lambda: [
        "decision", "person", "nanoclaw", "the-pit", "identity", "standing-order",
    ])
    noise_entities: list[str] = field(default_factory=lambda: [
        "kai", "the-pit",
    ])
    default_threshold: int = 7
    verbose_threshold: int = 5


@dataclass
class PruneConfig:
    half_life_days: int = 30
    min_score: float = 0.15
    min_backlinks_to_exempt: int = 1
    dry_run: bool = True
    tombstone_retention_days: int = 90


@dataclass
class Config:
    memory_dir: str = "./memory"
    index_file: str = "./memory/INDEX.md"
    archive_dir: str = ""
    backlink_dir: str = ""
    note: NoteConfig = field(default_factory=NoteConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
    enrich: EnrichConfig = field(default_factory=EnrichConfig)
    prune: PruneConfig = field(default_factory=PruneConfig)

    def __post_init__(self):
        if not self.archive_dir:
            self.archive_dir = os.path.join(self.memory_dir, "archive")
        if not self.backlink_dir:
            self.backlink_dir = os.path.join(self.memory_dir, "backlinks")


def load(path: str = "") -> Config:
    if not path:
        path = os.environ.get("MEMCTL_CONFIG", "memctl.yaml")

    p = Path(path)
    if not p.exists():
        raise SystemExit(
            f"config not found: {path}\n\n"
            "Run from a directory containing memctl.yaml, or pass --config <path>"
        )

    raw = yaml.safe_load(p.read_text())
    if not raw:
        return Config()

    note_raw = raw.get("note", {})
    note = NoteConfig(
        tags=note_raw.get("tags", []),
        valid_types=note_raw.get("valid_types", _DEFAULT_TYPES),
        valid_confidence=note_raw.get("valid_confidence", _DEFAULT_CONFIDENCE),
    )

    idx_raw = raw.get("index", {})
    index = IndexConfig(
        max_summary_chars=idx_raw.get("max_summary_chars", 120),
        hash_algorithm=idx_raw.get("hash_algorithm", "sha256"),
    )

    enrich_raw = raw.get("enrich", {})
    enrich_defaults = EnrichConfig()
    enrich = EnrichConfig(
        noise_tags=enrich_raw.get("noise_tags", enrich_defaults.noise_tags),
        noise_entities=enrich_raw.get("noise_entities", enrich_defaults.noise_entities),
        default_threshold=enrich_raw.get("default_threshold", enrich_defaults.default_threshold),
        verbose_threshold=enrich_raw.get("verbose_threshold", enrich_defaults.verbose_threshold),
    )

    prune_raw = raw.get("prune", {})
    prune = PruneConfig(
        half_life_days=prune_raw.get("half_life_days", 30),
        min_score=prune_raw.get("min_score", 0.15),
        min_backlinks_to_exempt=prune_raw.get("min_backlinks_to_exempt", 1),
        dry_run=prune_raw.get("dry_run", True),
        tombstone_retention_days=prune_raw.get("tombstone_retention_days", 90),
    )

    return Config(
        memory_dir=raw.get("memory_dir", "./memory"),
        index_file=raw.get("index_file", "./memory/INDEX.md"),
        archive_dir=raw.get("archive_dir", ""),
        backlink_dir=raw.get("backlink_dir", ""),
        note=note,
        index=index,
        enrich=enrich,
        prune=prune,
    )
