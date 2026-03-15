package note

import (
	"regexp"
	"strings"
)

var (
	nonAlpha = regexp.MustCompile(`[^a-z0-9]+`)
	trimDash = regexp.MustCompile(`^-+|-+$`)
)

func Slugify(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	s = strings.ReplaceAll(s, "'", "")
	s = nonAlpha.ReplaceAllString(s, "-")
	s = trimDash.ReplaceAllString(s, "")
	if s == "" {
		return "untitled"
	}
	if len(s) > 60 {
		s = s[:60]
		s = trimDash.ReplaceAllString(s, "")
	}
	return s
}
