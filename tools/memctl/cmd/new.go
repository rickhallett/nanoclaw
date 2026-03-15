package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/rickhallett/nanoclaw/tools/memctl/internal/config"
	"github.com/rickhallett/nanoclaw/tools/memctl/internal/index"
	"github.com/rickhallett/nanoclaw/tools/memctl/internal/note"
	"github.com/spf13/cobra"
)

var (
	newTitle      string
	newType       string
	newTags       string
	newEntities   string
	newConfidence string
	newBody       string
	newExpires    string
	newLinkTo     string
)

var newCmd = &cobra.Command{
	Use:   "new",
	Short: "Write a new atomic note (validates schema)",
	RunE:  runNew,
}

func init() {
	newCmd.Flags().StringVar(&newTitle, "title", "", "note title (required)")
	newCmd.Flags().StringVar(&newType, "type", "", "note type (required)")
	newCmd.Flags().StringVar(&newTags, "tags", "", "comma-separated tags (required)")
	newCmd.Flags().StringVar(&newEntities, "entities", "", "comma-separated entities")
	newCmd.Flags().StringVar(&newConfidence, "confidence", "high", "high|medium|low")
	newCmd.Flags().StringVar(&newBody, "body", "", "single-claim body (required)")
	newCmd.Flags().StringVar(&newExpires, "expires", "", "ISO8601 expiry date")
	newCmd.Flags().StringVar(&newLinkTo, "link-to", "", "ID of note to backlink")

	newCmd.MarkFlagRequired("title")
	newCmd.MarkFlagRequired("type")
	newCmd.MarkFlagRequired("tags")
	newCmd.MarkFlagRequired("body")

	rootCmd.AddCommand(newCmd)
}

type newOutput struct {
	ID       string   `json:"id"`
	File     string   `json:"file"`
	Warnings []string `json:"warnings,omitempty"`
}

func runNew(cmd *cobra.Command, args []string) error {
	cfg, err := config.Load(cfgFile)
	if err != nil {
		return fmt.Errorf("config: %w", err)
	}

	now := time.Now().UTC()
	id := now.Format("20060102-150405")

	tags := splitTrim(newTags)
	entities := splitTrim(newEntities)

	n := &note.Note{
		ID:         id,
		Title:      newTitle,
		Type:       newType,
		Tags:       tags,
		Entities:   entities,
		Backlinks:  []string{},
		Confidence: newConfidence,
		Created:    now,
		Modified:   now,
		Body:       newBody,
	}

	if newExpires != "" {
		n.Expires = &newExpires
	}

	// Validate
	errs := note.Validate(n, cfg.Note.ValidTypes, cfg.Note.ValidConfidence)
	if len(errs) > 0 {
		return fmt.Errorf("validation failed:\n  %s", strings.Join(errs, "\n  "))
	}

	// Tag warnings
	var warnings []string
	knownTags := make(map[string]bool)
	for _, t := range cfg.Note.Tags {
		knownTags[t] = true
	}
	for _, t := range tags {
		if !knownTags[t] {
			warnings = append(warnings, fmt.Sprintf("unknown tag %q", t))
		}
	}

	// Write note
	notesDir := filepath.Join(cfg.MemoryDir, "notes")
	os.MkdirAll(notesDir, 0755)

	filename := note.Filename(id, newTitle)
	filePath := filepath.Join(notesDir, filename)

	if dryRun {
		fmt.Printf("DRY RUN: would write %s\n", filePath)
		return nil
	}

	data := note.Marshal(n)
	if err := os.WriteFile(filePath, data, 0644); err != nil {
		return fmt.Errorf("write note: %w", err)
	}

	// Handle backlink
	if newLinkTo != "" {
		if err := addBacklink(cfg, newLinkTo, id); err != nil {
			warnings = append(warnings, fmt.Sprintf("backlink failed: %v", err))
		}
	}

	// Update index
	hash := index.HashBytes(data)
	summary := n.Body
	if len(summary) > cfg.Index.MaxSummaryChars {
		summary = summary[:cfg.Index.MaxSummaryChars] + "..."
	}

	relPath := filepath.Join(cfg.MemoryDir, "notes", filename)
	entry := index.Entry{
		ID:            id,
		File:          relPath,
		Title:         n.Title,
		Type:          n.Type,
		Tags:          n.Tags,
		Entities:      n.Entities,
		Summary:       summary,
		Hash:          hash,
		BacklinkCount: 0,
		Modified:      now.Format(time.RFC3339),
	}

	idx, err := index.Read(cfg.IndexFile)
	if err != nil {
		idx = &index.Index{}
	}

	idx.Notes = append(idx.Notes, entry)
	idx.NoteCount = len(idx.Notes)
	idx.Entities = collectEntities(idx.Notes)
	idx.TagVocabulary = cfg.Note.Tags

	if err := index.Write(cfg.IndexFile, idx); err != nil {
		return fmt.Errorf("update index: %w", err)
	}

	out := newOutput{ID: id, File: relPath, Warnings: warnings}
	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(out)
	} else {
		fmt.Printf("Created: %s\n", relPath)
		fmt.Printf("ID:      %s\n", id)
		for _, w := range warnings {
			fmt.Printf("WARNING: %s\n", w)
		}
	}

	return nil
}

func splitTrim(s string) []string {
	if s == "" {
		return nil
	}
	parts := strings.Split(s, ",")
	var result []string
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			result = append(result, p)
		}
	}
	return result
}

func collectEntities(notes []index.Entry) []string {
	seen := make(map[string]bool)
	var result []string
	for _, n := range notes {
		for _, e := range n.Entities {
			if !seen[e] {
				seen[e] = true
				result = append(result, e)
			}
		}
	}
	return result
}

func addBacklink(cfg *config.Config, targetID, sourceID string) error {
	notesDir := filepath.Join(cfg.MemoryDir, "notes")
	entries, err := os.ReadDir(notesDir)
	if err != nil {
		return err
	}

	for _, e := range entries {
		if !strings.HasPrefix(e.Name(), targetID) {
			continue
		}
		path := filepath.Join(notesDir, e.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		n, err := note.Parse(data)
		if err != nil {
			return err
		}
		for _, bl := range n.Backlinks {
			if bl == sourceID {
				return nil // already linked
			}
		}
		n.Backlinks = append(n.Backlinks, sourceID)
		n.Modified = time.Now().UTC()
		return os.WriteFile(path, note.Marshal(n), 0644)
	}

	return fmt.Errorf("note %q not found", targetID)
}
