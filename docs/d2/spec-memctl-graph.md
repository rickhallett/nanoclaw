# memctl graph — Knowledge Graph Analysis

**Date:** 2026-03-21
**Status:** SPEC
**Tier:** NOW
**Effort:** ~15 agent-min + ~10 human-min review

---

## Purpose

Add graph analysis capabilities to memctl. The memory corpus already has entity links and cross-references between notes — but there's no way to query the graph structure. This spec adds cluster detection, orphan finding, centrality analysis, and visual graph export.

## Current State

memctl notes have:
- `entities` — list of entity references (people, systems, concepts)
- `tags` — categorisation labels
- `type` — decision, fact, reference, project, person, event
- `link-to` — explicit cross-references to other notes
- `confidence` — high, medium, low

The `memctl graph` command already exists with basic output (`--format {text|html|dot}`). This spec extends it with analytical capabilities.

## CLI Interface

Extend the existing `memctl graph` subcommand:

```
memctl graph                                  # existing: basic graph view
memctl graph --clusters [--min-size N]        # find note clusters by entity co-occurrence
memctl graph --orphans                        # notes with no entity links or cross-references
memctl graph --central [--top N]              # highest-centrality notes (knowledge hubs)
memctl graph --density                        # graph density and connectivity metrics
memctl graph --entity <name>                  # subgraph centered on an entity
memctl graph --suggest-links [--top N]        # propose missing cross-references
memctl graph --format {text|html|dot|json}    # output format (extend existing)
```

## Analysis Algorithms

### Cluster Detection

Build a graph where:
- **Nodes** = notes
- **Edges** = shared entities (two notes that reference the same entity are connected)

Use connected components for basic clustering, then community detection (Louvain or label propagation) for finer grouping:

```python
import networkx as nx

G = nx.Graph()
for note in notes:
    G.add_node(note.id, title=note.title, type=note.type)

# Add edges for shared entities
entity_to_notes = defaultdict(list)
for note in notes:
    for entity in note.entities:
        entity_to_notes[entity].append(note.id)

for entity, note_ids in entity_to_notes.items():
    for a, b in combinations(note_ids, 2):
        if G.has_edge(a, b):
            G[a][b]['weight'] += 1
        else:
            G.add_edge(a, b, weight=1, entities=[entity])
```

Output: clusters with member notes, shared entities, and cluster label (most common entity or tag).

### Orphan Detection

Notes with:
- No entities
- No `link-to` references
- No incoming links from other notes
- Not referenced by entity co-occurrence

These are isolated knowledge fragments — candidates for enrichment or pruning.

### Centrality Analysis

Compute betweenness centrality (which notes connect otherwise-separate clusters):

```python
centrality = nx.betweenness_centrality(G, weight='weight')
top_notes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:N]
```

High-centrality notes are knowledge hubs — removing them would fragment the graph.

### Link Suggestion

Find pairs of notes that:
1. Share multiple entities but have no explicit `link-to` reference
2. Are in the same cluster but not directly connected
3. Have high Jaccard similarity of entity sets

```python
for a, b in combinations(notes, 2):
    if not explicitly_linked(a, b):
        shared = set(a.entities) & set(b.entities)
        if len(shared) >= 2:
            suggestions.append((a, b, shared))
```

### Density Metrics

```python
metrics = {
    "nodes": G.number_of_nodes(),
    "edges": G.number_of_edges(),
    "density": nx.density(G),
    "components": nx.number_connected_components(G),
    "avg_degree": sum(dict(G.degree()).values()) / G.number_of_nodes(),
    "avg_clustering": nx.average_clustering(G),
}
```

## Output Formats

### Text (terminal)

```
Clusters (4 found):
  Cluster 1 — "NanoClaw Architecture" (12 notes)
    Core entities: container-runner, ipc, agent-sdk
    Hub note: 20260315-142030-nanoclaw-container-architecture
    Members: [list of note IDs]

  Cluster 2 — "Personal Metrics" (8 notes)
    Core entities: trackctl, zazen, dashctl
    ...

Orphans (3 notes):
  20260310-091500-random-thought
  20260312-163000-meeting-note
  20260318-200000-book-recommendation

Knowledge Hubs (top 5 by centrality):
  0.42  20260315-142030-nanoclaw-container-architecture
  0.31  20260316-090000-halos-module-design
  ...

Density: 0.23 | Components: 4 | Avg degree: 3.1
```

### JSON

Full graph data as JSON — nodes, edges, clusters, centrality scores, orphans.

### DOT (Graphviz)

Extend the existing DOT output with cluster subgraphs and centrality-based node sizing.

### HTML

Self-contained HTML with an interactive graph visualization (D3.js force-directed graph, embedded inline).

## Module Changes

### New file: `halos/memctl/graph.py`

```python
"""Graph analysis for the memory corpus."""

import networkx as nx
from collections import defaultdict
from itertools import combinations

def build_graph(notes: list) -> nx.Graph: ...
def find_clusters(G: nx.Graph, min_size: int = 2) -> list[dict]: ...
def find_orphans(notes: list, G: nx.Graph) -> list: ...
def compute_centrality(G: nx.Graph, top_n: int = 10) -> list[tuple]: ...
def suggest_links(notes: list, G: nx.Graph, top_n: int = 10) -> list[tuple]: ...
def compute_density(G: nx.Graph) -> dict: ...
def format_text(analysis: dict) -> str: ...
def format_json(analysis: dict) -> str: ...
def format_dot(G: nx.Graph, analysis: dict) -> str: ...
```

### Modify: `halos/memctl/cli.py`

Add new flags to the existing `graph` subcommand parser:
- `--clusters`, `--min-size`
- `--orphans`
- `--central`, `--top`
- `--density`
- `--entity`
- `--suggest-links`

### Briefing Integration

`memctl graph --density --json` output feeds into briefings:
"memory: 147 notes, 4 clusters, 3 orphans, density 0.23 | hub: nanoclaw-container-architecture"

## Dependencies

- `networkx` — graph algorithms (add to pyproject.toml)
- No other new dependencies

## What It Does NOT Do

- Modify notes (analysis is read-only)
- Replace memctl's existing search/prune capabilities
- Require a GUI — all output is text/JSON/DOT, rendered by external tools if needed

## Testing

### test_graph.py — Unit tests

- `build_graph()`: empty corpus, single note, notes with shared entities, notes with explicit links
- `find_clusters()`: single cluster, multiple clusters, min_size filtering
- `find_orphans()`: notes with no entities, notes with entities but no connections
- `compute_centrality()`: known graph topology → expected centrality ordering
- `suggest_links()`: notes with shared entities but no explicit link
- `compute_density()`: known graph → expected metrics
- Edge case: all notes are orphans (empty graph)
- Edge case: all notes share one entity (single complete cluster)

### test_graph_cli.py — Integration tests

- `memctl graph --clusters --json` with fixture notes
- `memctl graph --orphans` output format
- `memctl graph --central --top 3` output format
- `memctl graph --density` output validation
- `memctl graph --suggest-links` with known suggestions

### test_graph_smoke.py — Smoke test

- Run `memctl graph --density` against the real memory corpus
- Verify output contains expected fields
- Verify `memctl graph --orphans` doesn't crash on real data
- Verify `memctl graph --clusters --json` returns valid JSON
