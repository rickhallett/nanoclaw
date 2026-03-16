"""
memctl enrich — Semantic backlink proposal engine.

Analyses the note corpus and proposes backlinks the tag/entity model
would miss. Outputs a muster-format batch for human approval.

Scoring rubric (5 dimensions, each 0-2, max score 10):

  SEMANTIC_BRIDGE (0-2)
    Does this link connect ideas that share meaning but not metadata?
    0 = already connected by shared tags/entities (redundant)
    1 = partial metadata overlap but the link adds a non-obvious axis
    2 = no metadata overlap; connection is purely semantic

  CROSS_TYPE (0-2)
    Do the notes have different types?
    0 = same type (fact<->fact, decision<->decision)
    1 = related types (fact<->reference, decision<->fact)
    2 = distant types (person<->decision, project<->vulnerability)

  CAUSAL_DIRECTION (0-2)
    Is there a causal or temporal relationship?
    0 = no directionality (both just co-exist)
    1 = weak direction (one informs the other)
    2 = clear causal chain (problem->solution, diagnosis->correction, principle->application)

  CLUSTER_VALUE (0-2)
    Does this link form or strengthen a meaningful cluster?
    0 = isolated pair, doesn't connect to anything else
    1 = extends an existing cluster by one hop
    2 = bridges two previously disconnected clusters

  RECALL_UTILITY (0-2)
    Would a future query benefit from traversing this link?
    0 = unlikely to be traversed (decorative connection)
    1 = useful in specific contexts
    2 = high probability of improving retrieval (the "I wouldn't have found this otherwise" test)

THRESHOLDS:
  >= 7: strong link, high confidence proposal
  5-6:  moderate link, include in muster with context
  3-4:  weak link, include only if --verbose
  < 3:  skip

FILTERS (applied before scoring):
  - Skip pairs where both notes are type=person (biographical noise)
  - Skip pairs where the only shared entity is "kai" (too generic)
  - Skip pairs already linked
  - Skip pairs where shared_tags >= 3 (already well-connected by metadata)
"""

import json
import os
import sys
from pathlib import Path

from . import config as cfgmod
from . import index as idxmod


def propose_links(cfg: cfgmod.Config, verbose: bool = False) -> list[dict]:
    """Generate link proposals sorted by score descending."""
    idx = idxmod.read(cfg.index_file)
    notes = idx.notes

    # Build existing backlink set for dedup
    existing_links = set()
    notes_dir = Path(cfg.memory_dir) / "notes"
    if notes_dir.exists():
        from . import note as notemod
        for f in notes_dir.iterdir():
            if f.suffix != ".md":
                continue
            try:
                n = notemod.parse(f.read_text())
                for bl in n.backlinks:
                    existing_links.add((n.id, bl))
                    existing_links.add((bl, n.id))
            except Exception:
                continue

    proposals = []

    for i, a in enumerate(notes):
        for b in notes[i + 1:]:
            if a.id == b.id:
                continue

            # Filter: both person = skip
            if a.type == "person" and b.type == "person":
                continue

            # Filter: already linked
            if (a.id, b.id) in existing_links:
                continue

            # Exclude tags/entities that are too broad to signal real connection
            noise_tags = set(cfg.enrich.noise_tags)
            noise_ents = set(cfg.enrich.noise_entities)
            shared_tags = set(a.tags) & set(b.tags) - noise_tags
            shared_ents = set(a.entities) & set(b.entities) - noise_ents

            # Filter: already well-connected by metadata
            if len(shared_tags) >= 3:
                continue

            # Score: semantic bridge
            # Zero overlap usually means no connection (not a deep hidden one).
            # The sweet spot is SOME overlap (proves relevance) but not full
            # overlap (which means tags already handle the connection).
            metadata_overlap = len(shared_tags) + len(shared_ents)
            if metadata_overlap == 0:
                semantic_bridge = 0  # no evidence of connection
            elif metadata_overlap <= 2:
                semantic_bridge = 2  # sweet spot: related but not redundant
            else:
                semantic_bridge = 1  # heavily overlapping, link adds less

            # Score: cross-type
            if a.type == b.type:
                cross_type = 0
            elif {a.type, b.type} & {"person", "project"} and {a.type, b.type} & {"decision", "fact"}:
                cross_type = 2
            else:
                cross_type = 1

            # Score: cluster value (does this note already have backlinks?)
            a_degree = a.backlink_count
            b_degree = b.backlink_count
            if a_degree > 0 and b_degree > 0:
                cluster_value = 2  # bridges two connected nodes
            elif a_degree > 0 or b_degree > 0:
                cluster_value = 1  # extends a cluster
            else:
                cluster_value = 0  # isolated pair

            # Causal direction and recall utility require semantic understanding.
            # Without LLM, use heuristics:
            # - decision -> fact/vulnerability = likely causal (principle -> observation)
            # - reference -> fact = likely useful for recall
            # - same-cluster tags suggest recall utility
            causal = 0
            if a.type == "decision" and b.type in ("fact", "reference"):
                causal = 1
            elif b.type == "decision" and a.type in ("fact", "reference"):
                causal = 1
            if "vulnerability" in (a.tags + b.tags) and "standing-order" in (a.tags + b.tags):
                causal = 2  # vulnerability <-> guard

            recall = 0
            if shared_ents:
                recall += 1
            if cross_type >= 1 and semantic_bridge >= 1:
                recall += 1

            total = semantic_bridge + cross_type + causal + cluster_value + recall

            threshold = cfg.enrich.verbose_threshold if verbose else cfg.enrich.default_threshold
            if total >= threshold:
                proposals.append({
                    "score": total,
                    "from_id": a.id,
                    "from_title": a.title,
                    "from_type": a.type,
                    "to_id": b.id,
                    "to_title": b.title,
                    "to_type": b.type,
                    "dimensions": {
                        "semantic_bridge": semantic_bridge,
                        "cross_type": cross_type,
                        "causal": causal,
                        "cluster_value": cluster_value,
                        "recall_utility": recall,
                    },
                    "shared_tags": sorted(shared_tags),
                    "shared_entities": sorted(shared_ents),
                })

    proposals.sort(key=lambda x: -x["score"])
    return proposals


def print_muster(proposals: list[dict], json_out: bool = False) -> None:
    """Print proposals in muster format for human approval."""
    if json_out:
        json.dump(proposals, sys.stdout, indent=2)
        print()
        return

    if not proposals:
        print("No link proposals above threshold.")
        return

    print(f"LINK PROPOSALS ({len(proposals)} candidates)")
    print("=" * 64)
    print()
    print("Dimensions: SB=semantic_bridge CT=cross_type CA=causal CL=cluster RE=recall")
    print()

    for i, p in enumerate(proposals, 1):
        d = p["dimensions"]
        dims = f"SB={d['semantic_bridge']} CT={d['cross_type']} CA={d['causal']} CL={d['cluster_value']} RE={d['recall_utility']}"
        ft = p["from_type"][:4].upper()
        tt = p["to_type"][:4].upper()
        shared = ""
        if p["shared_tags"]:
            shared += f" tags: {', '.join(p['shared_tags'])}"
        if p["shared_entities"]:
            shared += f" ents: {', '.join(p['shared_entities'])}"

        print(f"{i:3}. score={p['score']:2}  {dims}")
        print(f"     [{ft}] {p['from_title'][:50]}")
        print(f"     [{tt}] {p['to_title'][:50]}")
        if shared:
            print(f"    {shared}")
        print()
