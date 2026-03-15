package cmd

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestNewCommand(t *testing.T) {
	dir := t.TempDir()
	notesDir := filepath.Join(dir, "memory", "notes")
	os.MkdirAll(notesDir, 0755)

	// Write minimal config
	cfgContent := `memory_dir: ` + filepath.Join(dir, "memory") + `
index_file: ` + filepath.Join(dir, "CLAUDE.md") + `
note:
  tags: [postgres, auth, test]
  valid_types: [decision, fact, reference, project, person, event]
  valid_confidence: [high, medium, low]
index:
  max_summary_chars: 120
  hash_algorithm: sha256
`
	cfgPath := filepath.Join(dir, "memctl.yaml")
	os.WriteFile(cfgPath, []byte(cfgContent), 0644)

	// Run new command
	rootCmd.SetArgs([]string{
		"new",
		"--config", cfgPath,
		"--title", "Test decision",
		"--type", "decision",
		"--tags", "postgres,auth",
		"--confidence", "high",
		"--body", "Chose Postgres for auth.",
	})

	err := rootCmd.Execute()
	if err != nil {
		t.Fatalf("new command failed: %v", err)
	}

	// Verify note file was created
	entries, _ := os.ReadDir(notesDir)
	if len(entries) != 1 {
		t.Fatalf("expected 1 note file, got %d", len(entries))
	}

	noteContent, _ := os.ReadFile(filepath.Join(notesDir, entries[0].Name()))
	if !strings.Contains(string(noteContent), "Test decision") {
		t.Error("note file missing title")
	}
	if !strings.Contains(string(noteContent), "Chose Postgres for auth.") {
		t.Error("note file missing body")
	}

	// Verify index was updated
	indexContent, _ := os.ReadFile(filepath.Join(dir, "CLAUDE.md"))
	if !strings.Contains(string(indexContent), "Test decision") {
		t.Error("index missing note entry")
	}
}
