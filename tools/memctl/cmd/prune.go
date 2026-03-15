package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/rickhallett/nanoclaw/tools/memctl/internal/config"
	"github.com/rickhallett/nanoclaw/tools/memctl/internal/index"
	"github.com/rickhallett/nanoclaw/tools/memctl/internal/prune"
	"github.com/spf13/cobra"
)

var pruneExecute bool

var pruneCmd = &cobra.Command{
	Use:   "prune",
	Short: "Identify and archive stale/orphaned notes",
	Long:  "Defaults to --dry-run. Pass --execute to actually archive.",
	RunE:  runPrune,
}

func init() {
	pruneCmd.Flags().BoolVar(&pruneExecute, "execute", false, "actually archive candidates (default: dry-run)")
	rootCmd.AddCommand(pruneCmd)
}

type pruneResult struct {
	ID     string  `json:"id"`
	File   string  `json:"file"`
	Score  float64 `json:"score"`
	Status string  `json:"status"` // CANDIDATE, EXEMPT
	Reason string  `json:"reason,omitempty"`
}

func runPrune(cmd *cobra.Command, args []string) error {
	cfg, err := config.Load(cfgFile)
	if err != nil {
		return err
	}

	// Force dry-run unless config AND flag both say execute
	execute := pruneExecute && !cfg.Prune.DryRun
	if os.Getenv("MEMCTL_DRY_RUN") == "true" {
		execute = false
	}

	idx, err := index.Read(cfg.IndexFile)
	if err != nil {
		return err
	}

	now := time.Now()
	var results []pruneResult
	var archived int

	for _, n := range idx.Notes {
		if prune.IsExempt(n.Type, n.BacklinkCount, cfg.Prune.MinBacklinksToExempt) {
			results = append(results, pruneResult{
				ID: n.ID, File: n.File, Status: "EXEMPT",
				Reason: fmt.Sprintf("type=%s backlinks=%d", n.Type, n.BacklinkCount),
			})
			continue
		}

		mod, _ := time.Parse(time.RFC3339, n.Modified)
		days := now.Sub(mod).Hours() / 24
		score := prune.Score(n.BacklinkCount, days, cfg.Prune.HalfLifeDays)

		// Expired notes get halved score
		if n.Expires != nil {
			exp, err := time.Parse(time.RFC3339, *n.Expires)
			if err == nil && now.After(exp) {
				score *= 0.5
			}
		}

		if score < cfg.Prune.MinScore {
			results = append(results, pruneResult{
				ID: n.ID, File: n.File, Score: score, Status: "CANDIDATE",
				Reason: fmt.Sprintf("score=%.3f below threshold=%.3f", score, cfg.Prune.MinScore),
			})

			if execute {
				if err := archiveNote(cfg, n); err != nil {
					fmt.Fprintf(os.Stderr, "archive %s failed: %v\n", n.ID, err)
				} else {
					archived++
				}
			}
		} else {
			results = append(results, pruneResult{
				ID: n.ID, File: n.File, Score: score, Status: "KEEP",
			})
		}
	}

	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(results)
	} else {
		for _, r := range results {
			if r.Status == "KEEP" && !verbose {
				continue
			}
			fmt.Printf("%-10s %s  %s  %s\n", r.Status, r.ID, filepath.Base(r.File), r.Reason)
		}
		if execute {
			fmt.Printf("\nArchived: %d notes\n", archived)
		} else {
			fmt.Println("\nDRY RUN -- pass --execute to archive candidates")
		}
	}

	return nil
}

func archiveNote(cfg *config.Config, entry index.Entry) error {
	os.MkdirAll(cfg.ArchiveDir, 0755)

	src := entry.File
	date := time.Now().Format("20060102")
	dst := filepath.Join(cfg.ArchiveDir, fmt.Sprintf("%s-archived-%s.md", entry.ID, date))

	return os.Rename(src, dst)
}
