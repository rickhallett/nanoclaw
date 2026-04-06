# memctl Neo4j Explorer

Tech spec for an evening build session. Learning Neo4j by modelling
something real. Pause between each step to explore, query, discuss.

## Context

memctl manages 118 structured notes with YAML frontmatter:
- Fields: id, title, type, tags, entities, backlinks, confidence, created, modified, expires, body
- Types: decision (33), fact (62), reference (13), project (4), person (5), event (1)
- 32 unique entities, 76 unique tags, backlinks between notes
- Existing graph.py builds a NetworkX DiGraph for pyvis rendering

This spec adds a Neo4j layer alongside the existing system. Read-only
export, not a replacement. The existing flat-file notes remain canonical.

## Prerequisites

```bash
# Option A: Docker (recommended)
docker run -d --name memctl-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/memctl123 \
  neo4j:latest

# Option B: Aura Free (cloud, no Docker)
# https://neo4j.com/cloud/aura-free/

# Python driver
uv pip install neo4j
```

Verify: open http://localhost:7474, login with neo4j/memctl123.

## Step 1: Schema Design

PAUSE after implementing. Explore the empty database in the browser.
Run `:schema` to see constraints. Discuss: how does this differ from
the flat-file model? What can you express here that you couldn't before?

### Nodes

```
(:Note {
    id: "20260315-204343",
    title: "Ben - Kai's brother",
    type: "person",
    confidence: "high",
    created: datetime,
    modified: datetime,
    body: "Ben is Kai's brother."
})

(:Tag {name: "family"})

(:Entity {name: "kai"})
```

Three node types. Notes carry content. Tags and Entities are their
own nodes so relationships emerge naturally through shared connections.

### Relationships

```
(note)-[:TAGGED_WITH]->(tag)
(note)-[:MENTIONS]->(entity)
(note)-[:LINKS_TO]->(note)        // backlinks
(entity)-[:APPEARS_IN]->(note)    // reverse index
```

### Constraints (run first)

```cypher
CREATE CONSTRAINT note_id IF NOT EXISTS FOR (n:Note) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;
```

## Step 2: Import Script

Write `scripts/memctl-to-neo4j.py`. Reads all notes from
`memory/notes/*.md`, parses frontmatter, loads into Neo4j.

PAUSE after running. Open the browser. Click around. Drag nodes.
Run `MATCH (n) RETURN n LIMIT 50` to see the graph.

### Pseudocode

```python
from neo4j import GraphDatabase
from halos.memctl.note import parse
from pathlib import Path

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "memctl123"))

notes_dir = Path("memory/notes")

with driver.session() as session:
    # Create constraints first
    session.run("CREATE CONSTRAINT note_id IF NOT EXISTS FOR (n:Note) REQUIRE n.id IS UNIQUE")
    session.run("CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE")
    session.run("CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")

    for path in notes_dir.glob("*.md"):
        note = parse(path.read_text())

        # Merge note
        session.run("""
            MERGE (n:Note {id: $id})
            SET n.title = $title, n.type = $type, n.confidence = $confidence,
                n.created = $created, n.modified = $modified, n.body = $body
        """, id=note.id, title=note.title, type=note.type,
             confidence=note.confidence, created=note.created,
             modified=note.modified, body=note.body)

        # Tags
        for tag in note.tags:
            session.run("""
                MERGE (t:Tag {name: $tag})
                MERGE (n:Note {id: $id})
                MERGE (n)-[:TAGGED_WITH]->(t)
            """, tag=tag, id=note.id)

        # Entities
        for entity in note.entities:
            session.run("""
                MERGE (e:Entity {name: $entity})
                MERGE (n:Note {id: $id})
                MERGE (n)-[:MENTIONS]->(e)
            """, entity=entity, id=note.id)

        # Backlinks
        for bl in note.backlinks:
            session.run("""
                MERGE (src:Note {id: $src})
                MERGE (tgt:Note {id: $tgt})
                MERGE (src)-[:LINKS_TO]->(tgt)
            """, src=note.id, tgt=bl)

driver.close()
```

## Step 3: Exploration Queries

Run these one at a time. Each one reveals something different about
the data. PAUSE after each, discuss what you see.

### 3a: Overview

```cypher
// What do we have?
MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count

// Note types
MATCH (n:Note) RETURN n.type AS type, count(n) AS count ORDER BY count DESC
```

### 3b: Entity hubs

```cypher
// Which entities connect the most notes?
MATCH (e:Entity)<-[:MENTIONS]-(n:Note)
RETURN e.name, count(n) AS mentions
ORDER BY mentions DESC LIMIT 10
```

This answers: what are the gravitational centres of your memory?

### 3c: Tag clusters

```cypher
// Which tags co-occur most?
MATCH (n:Note)-[:TAGGED_WITH]->(t1:Tag),
      (n)-[:TAGGED_WITH]->(t2:Tag)
WHERE t1.name < t2.name
RETURN t1.name, t2.name, count(n) AS shared
ORDER BY shared DESC LIMIT 15
```

This shows implicit structure the flat files hide.

### 3d: Shortest path between concepts

```cypher
// How are two notes connected?
MATCH path = shortestPath(
  (a:Note {title: "Process is the product"})-[*]-(b:Note {title: "Engineering stack and experience"})
)
RETURN path
```

Replace titles with any two notes. The visual result in the browser
is the point: you see the connection chain rendered as a graph.

### 3e: Isolated notes (no connections)

```cypher
// Orphans: notes with no tags, no entities, no backlinks
MATCH (n:Note)
WHERE NOT (n)-[:TAGGED_WITH]->() AND NOT (n)-[:MENTIONS]->() AND NOT (n)-[:LINKS_TO]->()
RETURN n.title, n.type
```

These are candidates for enrichment or pruning.

### 3f: Decision chains

```cypher
// All decisions and what they link to
MATCH (d:Note {type: "decision"})-[:LINKS_TO]->(target)
RETURN d.title, collect(target.title) AS informs
```

### 3g: Two hops from an entity

```cypher
// Everything within 2 hops of "the-pit"
MATCH path = (e:Entity {name: "the-pit"})<-[:MENTIONS]-(n:Note)-[*0..1]-(connected)
RETURN path
```

This is the query that makes the case for graph over relational.

## Step 4: Neovis.js Visualisation

A single HTML file. No build step. Serves from file:// or a quick
`python3 -m http.server`.

PAUSE after implementing. Open in browser. Compare to the Neo4j
browser view. Discuss: where does a custom vis add value over the
built-in tool?

### File: `scripts/memctl-graph.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>memctl graph</title>
    <style>
        body { margin: 0; font-family: system-ui; background: #1a1a1a; }
        #viz { width: 100vw; height: 100vh; }
        #controls { position: fixed; top: 10px; left: 10px; z-index: 10;
                    background: #2a2a2a; padding: 12px; border-radius: 6px;
                    color: #ccc; font-size: 13px; }
        select, button { background: #333; color: #ccc; border: 1px solid #555;
                        padding: 4px 8px; border-radius: 3px; margin: 2px; }
    </style>
    <script src="https://unpkg.com/neovis.js@2.1.0"></script>
</head>
<body>
    <div id="controls">
        <b>memctl</b><br>
        <select id="query">
            <option value="full">Full graph</option>
            <option value="decisions">Decisions only</option>
            <option value="entities">Entity hubs</option>
            <option value="tags">Tag clusters</option>
        </select>
        <button onclick="draw()">Render</button>
    </div>
    <div id="viz"></div>
    <script>
        const queries = {
            full: `MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 300`,
            decisions: `MATCH (d:Note {type: "decision"})-[r]-(connected) RETURN d, r, connected`,
            entities: `MATCH (e:Entity)<-[r:MENTIONS]-(n:Note) RETURN e, r, n`,
            tags: `MATCH (n:Note)-[r:TAGGED_WITH]->(t:Tag) RETURN n, r, t`,
        };

        function draw() {
            const q = document.getElementById("query").value;
            const config = {
                containerId: "viz",
                neo4j: {
                    serverUrl: "bolt://localhost:7687",
                    serverUser: "neo4j",
                    serverPassword: "memctl123",
                },
                labels: {
                    Note: { label: "title", size: "pagerank",
                           [NeoVis.NEOVIS_ADVANCED_CONFIG]: {
                               function: { color: (node) => {
                                   const colors = {
                                       decision: "#e74c3c",
                                       fact: "#3498db",
                                       reference: "#2ecc71",
                                       project: "#f39c12",
                                       person: "#9b59b6",
                                       event: "#1abc9c"
                                   };
                                   return colors[node.properties.type] || "#95a5a6";
                               }}
                           }
                    },
                    Tag: { label: "name", color: "#555", size: 1.5 },
                    Entity: { label: "name", color: "#e67e22", size: 2 },
                },
                relationships: {
                    TAGGED_WITH: { color: "#444" },
                    MENTIONS: { color: "#e67e22" },
                    LINKS_TO: { color: "#e74c3c", thickness: 2 },
                },
                initialCypher: queries[q],
            };
            const viz = new NeoVis.default(config);
            viz.render();
        }
        draw();
    </script>
</body>
</html>
```

## Step 5: Observations (fill in during session)

After each step, note:

- What surprised you about the data?
- What relationships were invisible in the flat-file model?
- Where does graph querying feel natural vs forced?
- What would you add, change, or prune based on what you see?
- How would this scale? What changes at 1000 notes? 10,000?

These observations are interview material. Real, first-hand,
formed from building something in the last 24 hours.

## Not in scope (tonight)

- Write path (Neo4j as canonical store)
- Decay scoring in Cypher
- Full memctl CLI integration
- Authentication or multi-user
- Deployment

These are real follow-up work if the graph model proves useful.
Tonight is about seeing your data differently and learning Cypher
by asking questions you actually care about.
