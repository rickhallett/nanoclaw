package note

import (
	"bytes"
	"fmt"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

type Note struct {
	ID         string    `yaml:"id"`
	Title      string    `yaml:"title"`
	Type       string    `yaml:"type"`
	Tags       []string  `yaml:"tags"`
	Entities   []string  `yaml:"entities,omitempty"`
	Backlinks  []string  `yaml:"backlinks,omitempty"`
	Confidence string    `yaml:"confidence"`
	Created    time.Time `yaml:"created"`
	Modified   time.Time `yaml:"modified"`
	Expires    *string   `yaml:"expires"`
	Body       string    `yaml:"-"`
}

func Parse(data []byte) (*Note, error) {
	parts := bytes.SplitN(data, []byte("---"), 3)
	if len(parts) < 3 {
		return nil, fmt.Errorf("missing YAML frontmatter delimiters")
	}

	var n Note
	if err := yaml.Unmarshal(parts[1], &n); err != nil {
		return nil, fmt.Errorf("parse frontmatter: %w", err)
	}

	n.Body = strings.TrimSpace(string(parts[2]))
	return &n, nil
}

func Marshal(n *Note) []byte {
	var buf bytes.Buffer
	buf.WriteString("---\n")

	enc := yaml.NewEncoder(&buf)
	enc.SetIndent(2)
	enc.Encode(n)
	enc.Close()

	buf.WriteString("---\n")
	if n.Body != "" {
		buf.WriteString("\n")
		buf.WriteString(n.Body)
		buf.WriteString("\n")
	}
	return buf.Bytes()
}

func Validate(n *Note, validTypes, validConfidence []string) []string {
	var errs []string

	if n.Title == "" {
		errs = append(errs, "title is required")
	}
	if n.Type == "" {
		errs = append(errs, "type is required")
	} else if !contains(validTypes, n.Type) {
		errs = append(errs, fmt.Sprintf("invalid type %q, valid: %v", n.Type, validTypes))
	}
	if len(n.Tags) == 0 {
		errs = append(errs, "at least one tag is required")
	}
	if n.Confidence == "" {
		errs = append(errs, "confidence is required")
	} else if !contains(validConfidence, n.Confidence) {
		errs = append(errs, fmt.Sprintf("invalid confidence %q, valid: %v", n.Confidence, validConfidence))
	}
	if n.Body == "" {
		errs = append(errs, "body is required")
	}

	return errs
}

func Filename(id, title string) string {
	return id + "-" + Slugify(title) + ".md"
}

func contains(ss []string, s string) bool {
	for _, v := range ss {
		if v == s {
			return true
		}
	}
	return false
}
