"""Tests for Event envelope and serialisation."""

import json

from halos.eventsource.core import Event


class TestEvent:
    def test_create_sets_ids(self):
        e = Event.create(
            type="track.movement.logged",
            source="musashi",
            payload={"domain": "movement", "duration_mins": 30, "entry_id": 1},
        )
        assert e.id.startswith("evt_")
        assert e.correlation_id.startswith("cor_")
        assert e.version == 1
        assert e.source == "musashi"
        assert e.type == "track.movement.logged"

    def test_create_custom_correlation(self):
        e = Event.create(
            type="track.zazen.logged",
            source="musashi",
            payload={},
            correlation_id="cor_custom",
        )
        assert e.correlation_id == "cor_custom"

    def test_roundtrip_json(self):
        original = Event.create(
            type="night.item.created",
            source="seneca",
            payload={"item_id": "abc", "title": "Do the thing", "quadrant": "q2"},
        )
        serialised = original.to_json()
        restored = Event.from_json(serialised, stream_seq=42)

        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.version == original.version
        assert restored.source == original.source
        assert restored.timestamp == original.timestamp
        assert restored.correlation_id == original.correlation_id
        assert restored.payload == original.payload
        assert restored.stream_seq == 42

    def test_from_json_bytes(self):
        e = Event.create(type="test.event", source="test", payload={"x": 1})
        restored = Event.from_json(e.to_json().encode(), stream_seq=0)
        assert restored.id == e.id

    def test_frozen(self):
        e = Event.create(type="test.event", source="test", payload={})
        try:
            e.type = "mutated"  # type: ignore
            assert False, "Should have raised"
        except AttributeError:
            pass

    def test_json_structure(self):
        e = Event.create(
            type="track.movement.logged",
            source="musashi",
            payload={"domain": "movement", "duration_mins": 45, "entry_id": 7},
        )
        d = json.loads(e.to_json())
        assert set(d.keys()) == {
            "id", "type", "version", "source",
            "timestamp", "correlation_id", "payload",
        }
        assert d["payload"]["duration_mins"] == 45
