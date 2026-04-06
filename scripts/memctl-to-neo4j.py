#!/usr/bin/env python3
"""Export memctl notes to Neo4j. Read-only mirror, flat files remain canonical."""

from neo4j import GraphDatabase
from halos.memctl.note import parse
from pathlib import Path

BOLT_URL = "bolt://localhost:7687"
AUTH = ("neo4j", "memctl123")
NOTES_DIR = Path(__file__).resolve().parent.parent / "memory" / "notes"


def load(session, note):
    """Merge a single note and all its relationships."""
    # Note node
    session.run(
        """
        MERGE (n:Note {id: $id})
        SET n.title = $title, n.type = $type, n.confidence = $confidence,
            n.created = $created, n.modified = $modified, n.body = $body
        """,
        id=note.id,
        title=note.title,
        type=note.type,
        confidence=note.confidence,
        created=note.created,
        modified=note.modified,
        body=note.body,
    )

    # Tags
    for tag in note.tags:
        session.run(
            """
            MERGE (t:Tag {name: $tag})
            WITH t
            MATCH (n:Note {id: $id})
            MERGE (n)-[:TAGGED_WITH]->(t)
            """,
            tag=tag,
            id=note.id,
        )

    # Entities
    for entity in note.entities:
        session.run(
            """
            MERGE (e:Entity {name: $entity})
            WITH e
            MATCH (n:Note {id: $id})
            MERGE (n)-[:MENTIONS]->(e)
            """,
            entity=entity,
            id=note.id,
        )

    # Backlinks
    for bl in note.backlinks:
        session.run(
            """
            MATCH (src:Note {id: $src})
            MERGE (tgt:Note {id: $tgt})
            MERGE (src)-[:LINKS_TO]->(tgt)
            """,
            src=note.id,
            tgt=bl,
        )


def main():
    driver = GraphDatabase.driver(BOLT_URL, auth=AUTH)

    paths = sorted(NOTES_DIR.glob("*.md"))
    print(f"Found {len(paths)} notes in {NOTES_DIR}")

    loaded = 0
    errors = []

    with driver.session() as session:
        # Constraints (idempotent)
        session.run("CREATE CONSTRAINT note_id IF NOT EXISTS FOR (n:Note) REQUIRE n.id IS UNIQUE")
        session.run("CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE")
        session.run("CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
        print("Constraints ensured")
        for path in paths:
            try:
                note = parse(path.read_text())
                load(session, note)
                loaded += 1
            except Exception as e:
                errors.append((path.name, str(e)))
                print(f"  SKIP {path.name}: {e}")

    driver.close()

    print(f"\nLoaded {loaded}/{len(paths)} notes")
    if errors:
        print(f"Errors: {len(errors)}")


if __name__ == "__main__":
    main()
