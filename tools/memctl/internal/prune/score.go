package prune

import "math"

// Score computes the prune score for a note.
// backlinks: number of backlinks
// daysSinceModified: days since last modification
// halfLife: half-life in days for recency decay
func Score(backlinks int, daysSinceModified float64, halfLife int) float64 {
	recency := math.Exp(-daysSinceModified / float64(halfLife))
	if backlinks == 0 {
		return recency * 0.5
	}
	return float64(backlinks) * recency
}

// IsExempt returns true if a note should never be pruned.
func IsExempt(noteType string, backlinks int, minBacklinksToExempt int) bool {
	if noteType == "decision" || noteType == "person" {
		return true
	}
	return backlinks >= minBacklinksToExempt
}
