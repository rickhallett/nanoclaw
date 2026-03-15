package cmd

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFullWorkflow(t *testing.T) {
	dir := t.TempDir()
	notesDir := filepath.Join(dir, "memory", "notes")
	archiveDir := filepath.Join(dir, "memory", "archive")
	os.MkdirAll(notesDir, 0755)
	os.MkdirAll(archiveDir, 0755)

	cfgContent := `memory_dir: ` + filepath.Join(dir, "memory") + `
index_file: ` + filepath.Join(dir, "CLAUDE.md") + `
archive_dir: ` + archiveDir + `
note:
  tags: [postgres, auth, security, database]
  valid_types: [decision, fact, reference, project, person, event]
  valid_confidence: [high, medium, low]
index:
  max_summary_chars: 120
prune:
  half_life_days: 30
  min_score: 0.15
  min_backlinks_to_exempt: 1
  dry_run: true
`
	cfgPath := filepath.Join(dir, "memctl.yaml")
	os.WriteFile(cfgPath, []byte(cfgContent), 0644)

	// 1. Create two notes
	rootCmd.SetArgs([]string{"new", "--config", cfgPath,
		"--title", "Postgres for auth", "--type", "decision",
		"--tags", "postgres,auth", "--confidence", "high",
		"--body", "Chose Postgres."})
	if err := rootCmd.Execute(); err != nil {
		t.Fatalf("new #1: %v", err)
	}

	rootCmd.SetArgs([]string{"new", "--config", cfgPath,
		"--title", "Security review pending", "--type", "fact",
		"--tags", "security", "--confidence", "medium",
		"--body", "Review not done yet."})
	if err := rootCmd.Execute(); err != nil {
		t.Fatalf("new #2: %v", err)
	}

	// 2. Verify index has 2 notes
	indexContent, _ := os.ReadFile(filepath.Join(dir, "CLAUDE.md"))
	if !strings.Contains(string(indexContent), "note_count: 2") {
		t.Error("index should have note_count: 2")
	}

	// 3. Verify notes directory has 2 files
	entries, _ := os.ReadDir(notesDir)
	if len(entries) != 2 {
		t.Errorf("expected 2 note files, got %d", len(entries))
	}

	// 4. Rebuild should be idempotent
	rootCmd.SetArgs([]string{"index", "rebuild", "--config", cfgPath})
	if err := rootCmd.Execute(); err != nil {
		t.Fatalf("rebuild: %v", err)
	}

	// 5. Stats should run without error
	rootCmd.SetArgs([]string{"stats", "--config", cfgPath})
	if err := rootCmd.Execute(); err != nil {
		t.Fatalf("stats: %v", err)
	}

	// 6. Search by tag
	rootCmd.SetArgs([]string{"search", "--config", cfgPath, "--tags", "postgres"})
	if err := rootCmd.Execute(); err != nil {
		t.Fatalf("search: %v", err)
	}
}
