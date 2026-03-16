"""Tests for session record model."""

from halos.agentctl.session import Session, marshal, parse, filename


def _make_session(**overrides) -> Session:
    defaults = dict(
        id="nanoclaw-telegram-main-1773610015731",
        group="telegram_main",
        started="2026-03-16T09:00:00+00:00",
        finished="2026-03-16T09:05:33+00:00",
        duration_secs=333,
        exit_code=0,
        prompt_length=1250,
        result_length=387,
        status="success",
        source="container",
    )
    defaults.update(overrides)
    return Session(**defaults)


def test_create_session():
    s = _make_session()
    assert s.id == "nanoclaw-telegram-main-1773610015731"
    assert s.group == "telegram_main"
    assert s.duration_secs == 333
    assert s.status == "success"
    assert s.source == "container"


def test_validate_valid():
    s = _make_session()
    assert s.validate() == []


def test_validate_empty_id():
    s = _make_session(id="")
    errors = s.validate()
    assert any("id" in e for e in errors)


def test_validate_bad_status():
    s = _make_session(status="running")
    errors = s.validate()
    assert any("status" in e for e in errors)


def test_validate_bad_source():
    s = _make_session(source="manual")
    errors = s.validate()
    assert any("source" in e for e in errors)


def test_validate_negative_duration():
    s = _make_session(duration_secs=-1)
    errors = s.validate()
    assert any("duration" in e for e in errors)


def test_marshal_and_parse_roundtrip():
    s = _make_session()
    text = marshal(s)
    parsed = parse(text)
    assert parsed.id == s.id
    assert parsed.group == s.group
    assert parsed.started == s.started
    assert parsed.finished == s.finished
    assert parsed.duration_secs == s.duration_secs
    assert parsed.exit_code == s.exit_code
    assert parsed.prompt_length == s.prompt_length
    assert parsed.result_length == s.result_length
    assert parsed.status == s.status
    assert parsed.source == s.source


def test_parse_minimal():
    text = "id: test-1\ngroup: g\nstatus: error\nsource: container\n"
    s = parse(text)
    assert s.id == "test-1"
    assert s.group == "g"
    assert s.status == "error"
    assert s.duration_secs == 0


def test_parse_invalid_yaml():
    import pytest
    with pytest.raises(ValueError):
        parse("just a string, not yaml mapping")


def test_filename_generation():
    s = _make_session()
    assert filename(s) == "nanoclaw-telegram-main-1773610015731.yaml"
