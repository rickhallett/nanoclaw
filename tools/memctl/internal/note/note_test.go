package note

import (
	"strings"
	"testing"
	"time"
)

func TestParseNote(t *testing.T) {
	raw := `---
id: "20260315-143022"
title: "Postgres chosen for auth"
type: decision
tags:
  - postgres
  - auth
entities:
  - alice
backlinks: []
confidence: high
created: "2026-03-15T14:30:22Z"
modified: "2026-03-15T14:30:22Z"
expires: null
---
Chose Postgres for auth. Alice owns this.
`
	n, err := Parse([]byte(raw))
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if n.ID != "20260315-143022" {
		t.Errorf("ID = %q, want 20260315-143022", n.ID)
	}
	if n.Type != "decision" {
		t.Errorf("Type = %q, want decision", n.Type)
	}
	if n.Body != "Chose Postgres for auth. Alice owns this." {
		t.Errorf("Body = %q", n.Body)
	}
}

func TestValidateNote(t *testing.T) {
	validTypes := []string{"decision", "fact", "reference", "project", "person", "event"}
	validConf := []string{"high", "medium", "low"}

	n := &Note{
		ID:         "20260315-143022",
		Title:      "Test note",
		Type:       "decision",
		Tags:       []string{"postgres"},
		Confidence: "high",
		Body:       "A claim.",
		Created:    time.Now(),
		Modified:   time.Now(),
	}

	errs := Validate(n, validTypes, validConf)
	if len(errs) > 0 {
		t.Errorf("valid note got errors: %v", errs)
	}

	bad := &Note{Title: "", Type: "invalid", Body: ""}
	errs = Validate(bad, validTypes, validConf)
	if len(errs) < 3 {
		t.Errorf("expected >=3 errors for bad note, got %d: %v", len(errs), errs)
	}
}

func TestNoteRoundTrip(t *testing.T) {
	n := &Note{
		ID:         "20260315-143022",
		Title:      "Roundtrip test",
		Type:       "fact",
		Tags:       []string{"test", "roundtrip"},
		Entities:   []string{"alice"},
		Backlinks:  []string{},
		Confidence: "medium",
		Created:    time.Date(2026, 3, 15, 14, 30, 22, 0, time.UTC),
		Modified:   time.Date(2026, 3, 15, 14, 30, 22, 0, time.UTC),
		Body:       "This is a test claim.",
	}

	data := Marshal(n)
	parsed, err := Parse(data)
	if err != nil {
		t.Fatalf("roundtrip parse: %v", err)
	}
	if parsed.ID != n.ID || parsed.Title != n.Title || parsed.Body != n.Body {
		t.Errorf("roundtrip mismatch: got ID=%q Title=%q Body=%q", parsed.ID, parsed.Title, parsed.Body)
	}
	if !strings.Contains(string(data), "---") {
		t.Error("marshal should produce YAML frontmatter delimiters")
	}
}
