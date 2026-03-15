package cmd

import (
	"fmt"

	"github.com/rickhallett/nanoclaw/tools/memctl/internal/config"
	"github.com/spf13/cobra"
)

var (
	linkFrom string
	linkTo   string
)

var linkCmd = &cobra.Command{
	Use:   "link",
	Short: "Add a backlink between two notes",
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg, err := config.Load(cfgFile)
		if err != nil {
			return err
		}
		if dryRun {
			fmt.Printf("DRY RUN: would link %s -> %s\n", linkFrom, linkTo)
			return nil
		}
		if err := addBacklink(cfg, linkTo, linkFrom); err != nil {
			return err
		}
		fmt.Printf("Linked: %s -> %s\n", linkFrom, linkTo)
		return nil
	},
}

func init() {
	linkCmd.Flags().StringVar(&linkFrom, "from", "", "ID of the referencing note")
	linkCmd.Flags().StringVar(&linkTo, "to", "", "ID of the referenced note")
	linkCmd.MarkFlagRequired("from")
	linkCmd.MarkFlagRequired("to")
	rootCmd.AddCommand(linkCmd)
}
