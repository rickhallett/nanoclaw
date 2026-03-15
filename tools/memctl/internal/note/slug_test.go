package note

import "testing"

func TestSlugify(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"Postgres chosen over MongoDB", "postgres-chosen-over-mongodb"},
		{"Alice's AUTH decision!", "alices-auth-decision"},
		{"   spaces   everywhere   ", "spaces-everywhere"},
		{"UPPER-case-MIX", "upper-case-mix"},
		{"", "untitled"},
	}
	for _, tt := range tests {
		got := Slugify(tt.input)
		if got != tt.want {
			t.Errorf("Slugify(%q) = %q, want %q", tt.input, got, tt.want)
		}
	}
}
