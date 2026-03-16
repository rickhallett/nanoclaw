"""Interactive memory graph visualisation.

Builds a NetworkX DiGraph from the memctl index, then renders it as:
- html: interactive pyvis force-directed graph (default)
- dot:  Graphviz DOT → SVG/PNG
- text: the original ASCII tree (no extra deps)
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import index as idxmod


def build_graph(idx: idxmod.Index, include_entities: bool = True,
                noise_entities: set[str] | None = None):
    """Build a NetworkX DiGraph from the index.

    Nodes: notes (keyed by ID)
    Edges:
      - backlinks (solid, directional)
      - shared entities (dashed, undirected — added as two directed edges)
    """
    try:
        import networkx as nx
    except ImportError:
        print("networkx is required: uv pip install networkx", file=sys.stderr)
        sys.exit(1)

    G = nx.DiGraph()

    # Add note nodes
    id_to_entry: dict[str, idxmod.Entry] = {}
    for n in idx.notes:
        id_to_entry[n.id] = n
        style = style_node(n.type, n.backlink_count)
        G.add_node(
            n.id,
            label=n.title,
            title=_tooltip(n),
            note_type=n.type,
            **style,
        )

    # Backlink edges
    for n in idx.notes:
        # backlink_count is in the index, but actual backlink IDs are in the
        # note files.  We need to parse them from disk for edge data.
        pass  # handled by _add_backlink_edges below

    _add_backlink_edges(G, idx)

    if include_entities:
        _add_entity_edges(G, idx, noise_entities=noise_entities)

    return G


def _add_backlink_edges(G, idx: idxmod.Index):
    """Parse note files to extract actual backlink IDs and add edges."""
    from . import note as notemod

    for entry in idx.notes:
        p = Path(entry.file)
        if not p.exists():
            continue
        try:
            n = notemod.parse(p.read_text())
        except Exception:
            continue
        for bl_id in n.backlinks:
            if bl_id in {node for node in G.nodes}:
                G.add_edge(bl_id, entry.id, edge_type="backlink", color="#888888", width=2)


def _add_entity_edges(G, idx: idxmod.Index, noise_entities: set[str] | None = None):
    """Add dashed edges between notes sharing non-trivial entities."""
    NOISE = noise_entities or {"kai", "the-pit", "nanoclaw"}

    entity_to_ids: dict[str, list[str]] = {}
    for n in idx.notes:
        for e in n.entities:
            if e.lower() not in NOISE:
                entity_to_ids.setdefault(e, []).append(n.id)

    for entity, ids in entity_to_ids.items():
        if len(ids) < 2 or len(ids) > 8:
            # Skip singletons and overly-common entities (noise)
            continue
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if not G.has_edge(a, b) and not G.has_edge(b, a):
                    G.add_edge(
                        a, b,
                        edge_type="entity",
                        label=entity,
                        color="#cccccc",
                        width=1,
                        dashes=True,
                    )


def style_node(note_type: str, backlink_count: int) -> dict:
    """Map note type and connectivity to visual properties.

    TODO: Rick — this is the function to customise.
    Returns a dict consumed by pyvis: color, size, shape, font.
    """
    # ── Colour palette (muted, legible on dark and light backgrounds) ──
    palette = {
        "person":    "#6fa8dc",  # soft blue
        "project":   "#93c47d",  # sage green
        "decision":  "#e06666",  # muted red — decisions stand out
        "fact":      "#f6b26b",  # warm amber
        "reference": "#8e7cc3",  # lavender
        "event":     "#76a5af",  # teal
    }

    # ── Shape: persons are dots, decisions are diamonds ──
    shapes = {
        "person":    "dot",
        "project":   "dot",
        "decision":  "diamond",
        "fact":      "dot",
        "reference": "square",
        "event":     "triangle",
    }

    # ── Size: base 15, +5 per backlink, cap at 40 ──
    base = 15
    size = min(base + backlink_count * 5, 40)

    return {
        "color": palette.get(note_type, "#999999"),
        "size": size,
        "shape": shapes.get(note_type, "dot"),
    }


def _tooltip(entry: idxmod.Entry) -> str:
    """Build an HTML tooltip for pyvis hover."""
    lines = [
        f"<b>{entry.title}</b>",
        f"Type: {entry.type}",
        f"Tags: {', '.join(entry.tags)}",
    ]
    if entry.entities:
        lines.append(f"Entities: {', '.join(entry.entities)}")
    if entry.backlink_count:
        lines.append(f"Backlinks: {entry.backlink_count}")
    lines.append(f"<i>{entry.summary[:80]}</i>")
    return "<br>".join(lines)


# ── Renderers ────────────────────────────────────────────────


def render_html(G, output: str = "memory-graph.html") -> str:
    """Render an interactive HTML file using pyvis."""
    try:
        from pyvis.network import Network
    except ImportError:
        print("pyvis is required: uv pip install pyvis", file=sys.stderr)
        sys.exit(1)

    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="#e0e0e0",
        directed=True,
        select_menu=False,
        filter_menu=False,
    )

    net.from_nx(G)

    # Physics: Barnes-Hut is fast and good for medium graphs
    net.barnes_hut(
        gravity=-3000,
        central_gravity=0.3,
        spring_length=150,
        spring_strength=0.04,
        damping=0.09,
    )

    net.show_buttons(filter_=["physics"])
    net.save_graph(output)

    return output


def render_dot(G, output: str = "memory-graph.svg") -> str:
    """Render a static SVG/PNG using Graphviz."""
    try:
        import graphviz
    except ImportError:
        print("graphviz is required: uv pip install graphviz", file=sys.stderr)
        print("Also install the system package: sudo pacman -S graphviz", file=sys.stderr)
        sys.exit(1)

    fmt = "svg" if output.endswith(".svg") else "png"
    dot = graphviz.Digraph(format=fmt)
    dot.attr(bgcolor="#1a1a2e", fontcolor="#e0e0e0", rankdir="LR")
    dot.attr("node", style="filled", fontcolor="white", fontsize="10")

    for node_id, data in G.nodes(data=True):
        label = data.get("label", node_id)
        if len(label) > 30:
            label = label[:28] + "…"
        dot.node(
            node_id,
            label=label,
            fillcolor=data.get("color", "#999999"),
            shape=_dot_shape(data.get("shape", "dot")),
        )

    for u, v, data in G.edges(data=True):
        style = "dashed" if data.get("dashes") else "solid"
        dot.edge(u, v, style=style, color=data.get("color", "#888888"))

    out_path = output.rsplit(".", 1)[0]
    dot.render(out_path, cleanup=True)
    return output


def _dot_shape(pyvis_shape: str) -> str:
    """Map pyvis shape names to Graphviz shape names."""
    mapping = {
        "dot": "ellipse",
        "diamond": "diamond",
        "square": "box",
        "triangle": "triangle",
    }
    return mapping.get(pyvis_shape, "ellipse")


def render_text(idx: idxmod.Index):
    """The original ASCII tree renderer (no extra deps)."""
    by_type: dict[str, list[idxmod.Entry]] = {}
    entities: dict[str, list[str]] = {}
    for n in idx.notes:
        by_type.setdefault(n.type, []).append(n)
        for e in n.entities:
            entities.setdefault(e, []).append(n.title)

    bl_total = sum(n.backlink_count for n in idx.notes)

    print(f"{'═' * 64}")
    print(f"  MEMORY GRAPH  ·  {idx.note_count} notes  ·  {len(entities)} entities  ·  {bl_total} backlinks")
    print(f"{'═' * 64}")

    for t in ["person", "project", "decision", "fact", "reference", "event"]:
        items = by_type.get(t, [])
        if not items:
            continue
        print(f"\n  ┌─ {t.upper()} ({len(items)})")
        for i, n in enumerate(items):
            is_last = i == len(items) - 1
            prefix = "  └─" if is_last else "  ├─"
            detail = "    " if is_last else "  │ "
            ents = ", ".join(n.entities) if n.entities else ""
            tags = ", ".join(n.tags)
            print(f"{prefix} {n.title}")
            if ents:
                print(f"{detail}   ⤷ [{ents}]  #{tags}")
            else:
                print(f"{detail}   ⤷ #{tags}")

    print()
    print("  ┌─ ENTITY INDEX")
    sorted_ents = sorted(entities.items())
    for i, (e, titles) in enumerate(sorted_ents):
        is_last = i == len(sorted_ents) - 1
        prefix = "  └─" if is_last else "  ├─"
        print(f"{prefix} {e:22s} ({len(titles)} notes)")

    print()
    print(f"{'═' * 64}")
