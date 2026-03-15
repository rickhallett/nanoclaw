package prune

import (
	"math"
	"testing"
)

func TestPruneScore(t *testing.T) {
	// Recent note with backlinks = high score
	s := Score(2, 1.0, 30)
	if s < 1.0 {
		t.Errorf("recent note with 2 backlinks should score > 1.0, got %f", s)
	}

	// Old note with no backlinks = low score
	s = Score(0, 60.0, 30)
	if s > 0.15 {
		t.Errorf("60-day-old note with 0 backlinks should score < 0.15, got %f", s)
	}

	// Zero-day note = max recency
	s = Score(0, 0.0, 30)
	if math.Abs(s-0.5) > 0.01 {
		t.Errorf("zero-day note with 0 backlinks should score ~0.5, got %f", s)
	}
}

func TestExemptions(t *testing.T) {
	if !IsExempt("decision", 0, 1) {
		t.Error("decisions should always be exempt")
	}
	if !IsExempt("person", 0, 1) {
		t.Error("persons should always be exempt")
	}
	if !IsExempt("fact", 5, 1) {
		t.Error("note with 5 backlinks (threshold 1) should be exempt")
	}
	if IsExempt("fact", 0, 1) {
		t.Error("fact with 0 backlinks should not be exempt")
	}
}
