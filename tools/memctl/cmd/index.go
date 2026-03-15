package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/rickhallett/nanoclaw/tools/memctl/internal/config"
	"github.com/rickhallett/nanoclaw/tools/memctl/internal/index"
	"github.com/rickhallett/nanoclaw/tools/memctl/internal/note"
	"github.com/spf13/cobra"
)

var indexCmd = &cobra.Command{
	Use:   "index",
	Short: "Index management subcommands",
}

var rebuildCmd = &cobra.Command{
	Use:   "rebuild",
	Short: "Regenerate CLAUDE.md index from notes corpus",
	RunE:  runRebuild,
}

var verifyCmd = &cobra.Command{
	Use:   "verify",
	Short: "Hash-check all index entries; report drift",
	RunE:  runVerify,
}

func init() {
	indexCmd.AddCommand(rebuildCmd, verifyCmd)
	rootCmd.AddCommand(indexCmd)
}

func runRebuild(cmd *cobra.Command, args []string) error {
	cfg, err := config.Load(cfgFile)
	if err != nil {
		return err
	}

	notesDir := filepath.Join(cfg.MemoryDir, "notes")
	entries, err := os.ReadDir(notesDir)
	if err != nil {
		if os.IsNotExist(err) {
			fmt.Println("No notes directory found. Nothing to index.")
			return nil
		}
		return err
	}

	var notes []index.Entry
	var parseErrors int

	for _, e := range entries {
		if e.IsDir() || filepath.Ext(e.Name()) != ".md" {
			continue
		}

		path := filepath.Join(notesDir, e.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			parseErrors++
			continue
		}

		n, err := note.Parse(data)
		if err != nil {
			parseErrors++
			if verbose {
				fmt.Fprintf(os.Stderr, "WARN: parse error in %s: %v\n", e.Name(), err)
			}
			continue
		}

		summary := n.Body
		if len(summary) > cfg.Index.MaxSummaryChars {
			summary = summary[:cfg.Index.MaxSummaryChars] + "..."
		}

		relPath := filepath.Join(cfg.MemoryDir, "notes", e.Name())
		notes = append(notes, index.Entry{
			ID:            n.ID,
			File:          relPath,
			Title:         n.Title,
			Type:          n.Type,
			Tags:          n.Tags,
			Entities:      n.Entities,
			Summary:       summary,
			Hash:          index.HashBytes(data),
			BacklinkCount: len(n.Backlinks),
			Modified:      n.Modified.Format("2006-01-02T15:04:05Z"),
		})
	}

	idx := &index.Index{
		NoteCount:     len(notes),
		Entities:      collectEntities(notes),
		TagVocabulary: cfg.Note.Tags,
		Notes:         notes,
	}

	if dryRun {
		fmt.Printf("DRY RUN: would write %d notes to %s\n", len(notes), cfg.IndexFile)
		return nil
	}

	if err := index.Write(cfg.IndexFile, idx); err != nil {
		return err
	}

	fmt.Printf("Rebuilt index: %d notes, %d parse errors\n", len(notes), parseErrors)
	return nil
}

func runVerify(cmd *cobra.Command, args []string) error {
	cfg, err := config.Load(cfgFile)
	if err != nil {
		return err
	}

	idx, err := index.Read(cfg.IndexFile)
	if err != nil {
		return fmt.Errorf("read index: %w", err)
	}

	results := index.Verify(idx.Notes)

	var driftCount, missingCount int
	for _, r := range results {
		switch r.Status {
		case "DRIFT":
			driftCount++
		case "MISSING":
			missingCount++
		}

		if jsonOut {
			continue
		}
		fmt.Printf("%-8s %s  %s\n", r.Status, r.ID, filepath.Base(r.File))
	}

	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(results)
	}

	// Check for orphans (files not in index)
	notesDir := filepath.Join(cfg.MemoryDir, "notes")
	if entries, err := os.ReadDir(notesDir); err == nil {
		indexed := make(map[string]bool)
		for _, n := range idx.Notes {
			indexed[filepath.Base(n.File)] = true
		}
		for _, e := range entries {
			if !e.IsDir() && filepath.Ext(e.Name()) == ".md" && !indexed[e.Name()] {
				fmt.Printf("%-8s %s\n", "ORPHAN", e.Name())
			}
		}
	}

	if driftCount > 0 || missingCount > 0 {
		fmt.Printf("\n%d drifted, %d missing. Run: memctl index rebuild\n", driftCount, missingCount)
		os.Exit(3)
	}

	return nil
}
