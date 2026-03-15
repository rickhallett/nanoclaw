package cmd

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/rickhallett/nanoclaw/tools/memctl/internal/config"
	"github.com/spf13/cobra"
)

var getCmd = &cobra.Command{
	Use:   "get [id-or-filename]",
	Short: "Print a note by ID or filename",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg, err := config.Load(cfgFile)
		if err != nil {
			return err
		}

		query := args[0]
		notesDir := filepath.Join(cfg.MemoryDir, "notes")
		entries, err := os.ReadDir(notesDir)
		if err != nil {
			return err
		}

		for _, e := range entries {
			if strings.HasPrefix(e.Name(), query) || e.Name() == query {
				data, err := os.ReadFile(filepath.Join(notesDir, e.Name()))
				if err != nil {
					return err
				}
				fmt.Print(string(data))
				return nil
			}
		}

		return fmt.Errorf("note %q not found", query)
	},
}

func init() {
	rootCmd.AddCommand(getCmd)
}
