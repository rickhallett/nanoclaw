"""Tests for halos.memctl.prune — score decay and exemption logic."""
import math

import pytest

from halos.memctl.prune import is_exempt, score


# ---------------------------------------------------------------------------
# score()
# ---------------------------------------------------------------------------

class TestScore:
    def test_zero_backlinks_recent(self):
        """0 backlinks, 0 days old => recency=1.0, score = 1.0 * 0.5 = 0.5."""
        result = score(backlinks=0, days_since_modified=0.0, half_life=30)
        assert result == pytest.approx(0.5)

    def test_zero_backlinks_old(self):
        """0 backlinks, 90 days old, half_life=30 => decayed substantially."""
        result = score(backlinks=0, days_since_modified=90.0, half_life=30)
        expected = math.exp(-90.0 / 30) * 0.5
        assert result == pytest.approx(expected)

    def test_with_backlinks_recent(self):
        """3 backlinks, 0 days old => 3 * 1.0 = 3.0."""
        result = score(backlinks=3, days_since_modified=0.0, half_life=30)
        assert result == pytest.approx(3.0)

    def test_with_backlinks_old(self):
        """2 backlinks, 60 days, half_life=30 => 2 * exp(-2) ~ 0.27."""
        result = score(backlinks=2, days_since_modified=60.0, half_life=30)
        expected = 2 * math.exp(-60.0 / 30)
        assert result == pytest.approx(expected)

    def test_score_decreases_with_age(self):
        s1 = score(backlinks=1, days_since_modified=0.0, half_life=30)
        s2 = score(backlinks=1, days_since_modified=30.0, half_life=30)
        s3 = score(backlinks=1, days_since_modified=60.0, half_life=30)
        assert s1 > s2 > s3

    def test_score_increases_with_backlinks(self):
        s0 = score(backlinks=0, days_since_modified=10.0, half_life=30)
        s1 = score(backlinks=1, days_since_modified=10.0, half_life=30)
        s3 = score(backlinks=3, days_since_modified=10.0, half_life=30)
        assert s0 < s1 < s3


# ---------------------------------------------------------------------------
# is_exempt()
# ---------------------------------------------------------------------------

class TestIsExempt:
    def test_decision_always_exempt(self):
        assert is_exempt("decision", backlinks=0, min_backlinks_to_exempt=5) is True

    def test_person_always_exempt(self):
        assert is_exempt("person", backlinks=0, min_backlinks_to_exempt=5) is True

    def test_fact_with_enough_backlinks_exempt(self):
        assert is_exempt("fact", backlinks=2, min_backlinks_to_exempt=2) is True

    def test_fact_with_zero_backlinks_not_exempt(self):
        assert is_exempt("fact", backlinks=0, min_backlinks_to_exempt=1) is False

    def test_fact_below_threshold_not_exempt(self):
        assert is_exempt("fact", backlinks=1, min_backlinks_to_exempt=3) is False

    def test_reference_with_enough_backlinks(self):
        assert is_exempt("reference", backlinks=5, min_backlinks_to_exempt=3) is True

    def test_event_zero_backlinks(self):
        assert is_exempt("event", backlinks=0, min_backlinks_to_exempt=1) is False
