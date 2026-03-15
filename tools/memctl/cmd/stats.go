package cmd

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"time"

	"github.com/rickhallett/nanoclaw/tools/memctl/internal/config"
	"github.com/rickhallett/nanoclaw/tools/memctl/internal/index"
	"github.com/spf13/cobra"
)

var statsCmd = &cobra.Command{
	Use:   "stats",
	Short: "Corpus health report",
	RunE:  runStats,
}

func init() {
	rootCmd.AddCommand(statsCmd)
}

func runStats(cmd *cobra.Command, args []string) error {
	cfg, err := config.Load(cfgFile)
	if err != nil {
		return err
	}

	idx, err := index.Read(cfg.IndexFile)
	if err != nil {
		return err
	}

	// Count archived
	var archivedCount int
	if entries, err := os.ReadDir(cfg.ArchiveDir); err == nil {
		for _, e := range entries {
			if filepath.Ext(e.Name()) == ".md" {
				archivedCount++
			}
		}
	}

	// Count orphans
	notesDir := filepath.Join(cfg.MemoryDir, "notes")
	var orphanCount int
	if entries, err := os.ReadDir(notesDir); err == nil {
		indexed := make(map[string]bool)
		for _, n := range idx.Notes {
			indexed[filepath.Base(n.File)] = true
		}
		for _, e := range entries {
			if !e.IsDir() && filepath.Ext(e.Name()) == ".md" && !indexed[e.Name()] {
				orphanCount++
			}
		}
	}

	// Type counts
	typeCounts := make(map[string]int)
	for _, n := range idx.Notes {
		typeCounts[n.Type]++
	}

	// Score distribution
	now := time.Now()
	var healthy, ok, pruneZone int
	for _, n := range idx.Notes {
		mod, _ := time.Parse(time.RFC3339, n.Modified)
		days := now.Sub(mod).Hours() / 24
		recency := math.Exp(-days / float64(cfg.Prune.HalfLifeDays))
		score := float64(n.BacklinkCount) * recency
		if n.BacklinkCount == 0 {
			score = recency * 0.5
		}

		switch {
		case score > 0.50:
			healthy++
		case score >= cfg.Prune.MinScore:
			ok++
		default:
			pruneZone++
		}
	}

	// Unique entities and tags
	entitySet := make(map[string]bool)
	tagSet := make(map[string]bool)
	for _, n := range idx.Notes {
		for _, e := range n.Entities {
			entitySet[e] = true
		}
		for _, t := range n.Tags {
			tagSet[t] = true
		}
	}

	if jsonOut {
		data := map[string]any{
			"notes": idx.NoteCount, "archived": archivedCount,
			"orphaned": orphanCount, "types": typeCounts,
			"entities": len(entitySet), "tags": len(tagSet),
		}
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(data)
		return nil
	}

	fmt.Printf("Notes:          %d\n", idx.NoteCount)
	fmt.Printf("Archived:       %d\n", archivedCount)
	fmt.Printf("Orphaned:       %d\n", orphanCount)
	fmt.Println()
	fmt.Println("By type:")
	for _, t := range cfg.Note.ValidTypes {
		if c := typeCounts[t]; c > 0 {
			fmt.Printf("  %-14s %d\n", t, c)
		}
	}
	fmt.Println()
	fmt.Println("Score distribution:")
	fmt.Printf("  > 0.50   (healthy):    %d\n", healthy)
	fmt.Printf("  0.15-0.50 (ok):        %d\n", ok)
	fmt.Printf("  < 0.15   (prune zone): %d\n", pruneZone)
	fmt.Println()
	fmt.Printf("Entities: %d unique\n", len(entitySet))
	fmt.Printf("Tags:     %d unique\n", len(tagSet))

	return nil
}
