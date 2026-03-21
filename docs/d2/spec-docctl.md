---
title: "docctl — Document Assembly & Template Rendering"
category: spec
status: active
created: 2026-03-21
---

# docctl — Document Assembly & Template Rendering

**Date:** 2026-03-21
**Status:** SPEC
**Tier:** NOW (core) / NEXT (Google Drive export)
**Effort:** ~20 agent-min (core) + ~15 agent-min (Drive integration) + ~15 human-min review

---

## Purpose

Document assembly from structured templates. Write content as Markdown or LaTeX with variable substitution, render to PDF/HTML/PPTX, optionally export to Google Drive as native Docs/Slides. Composes with briefings (report rendering), mailctl (email attachments), and nightctl (status reports).

The agent writes structure and content. Pandoc renders. The human reviews visual output when presentation matters.

## CLI Interface

```
docctl templates                              # list available templates
docctl render --template T [--vars vars.yaml] [--output PATH] [--format pdf|html|docx|pptx]
docctl render --input doc.md [--output PATH] [--format pdf]
docctl slides --template T [--vars vars.yaml] [--output PATH]
docctl export --input PATH --to gdrive [--folder FOLDER_ID]
docctl new-template --name N --type {doc|slides|letter|invoice}
docctl summary                                # one-liner for briefing integration
```

## Template System

Templates live in `templates/docs/`:

```
templates/docs/
  letter.md           # formal letter
  invoice.md          # invoice template
  report.md           # structured report
  slides.md           # Marp slide deck
  proposal.md         # project proposal
```

### Template Format

Markdown with Jinja2-style variable placeholders:

```markdown
---
template: letter
variables:
  - name: recipient
    required: true
  - name: subject
    required: true
  - name: date
    default: "{{ today }}"
  - name: sender
    default: "Kai"
---

# {{ subject }}

Dear {{ recipient }},

{{ body }}

Kind regards,
{{ sender }}
```

### Variables File

`vars.yaml`:
```yaml
recipient: "Jane Smith"
subject: "Project Update"
body: |
  Here is the weekly update on the NanoClaw project.

  Key developments:
  - calctl unified schedule view completed
  - statusctl fleet monitoring operational
```

### Built-in Variables

Available in all templates without explicit definition:
- `{{ today }}` — current date (YYYY-MM-DD)
- `{{ now }}` — current datetime (ISO 8601)
- `{{ year }}`, `{{ month }}`, `{{ day }}`

## Slides Template Flow

Slides use [Marp](https://marp.app/) (Markdown Presentation Ecosystem):

```markdown
---
marp: true
theme: default
paginate: true
---

# {{ title }}

{{ subtitle }}

---

## {{ section_1_title }}

{{ section_1_content }}

---

## {{ section_2_title }}

{{ section_2_content }}
```

### Slides CLI

```bash
# Render slides from template + variables
docctl slides --template pitch --vars pitch-vars.yaml --output pitch.pdf

# Render slides from raw Markdown
docctl slides --input presentation.md --output slides.pdf

# Export to Google Slides (via Drive as PPTX)
docctl slides --template pitch --vars pitch-vars.yaml --format pptx | \
  docctl export --input - --to gdrive --folder PRESENTATIONS_FOLDER_ID
```

### Rendering Pipeline

1. Load template from `templates/docs/`
2. Parse YAML frontmatter for variable definitions
3. Load variables from `--vars` file (or CLI flags)
4. Validate: all required variables present
5. Render Jinja2 template with variables
6. Pass to renderer:
   - **PDF:** `pandoc -o output.pdf` (or `marp --pdf` for slides)
   - **HTML:** `pandoc -o output.html` (or `marp --html` for slides)
   - **DOCX:** `pandoc -o output.docx`
   - **PPTX:** `marp --pptx` for slides, `pandoc -o output.pptx` for docs

## Google Drive Export

### Architecture

Uses the `google_workspace` MCP tools (already available) or direct Google Drive API:

```python
# Via Google Drive API
from googleapiclient.discovery import build

service = build('drive', 'v3', credentials=creds)

# Upload and convert to Google Docs
file_metadata = {
    'name': 'My Document',
    'mimeType': 'application/vnd.google-apps.document',  # or .presentation
    'parents': [folder_id],
}
media = MediaFileUpload('output.docx', mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
file = service.files().create(body=file_metadata, media_body=media, fields='id,webViewLink').execute()
```

### Export Flow

1. Render document to DOCX (for Docs) or PPTX (for Slides)
2. Upload to Google Drive with conversion to native format
3. Return the Google Drive link
4. Optionally move to a specific folder

### Credentials

Same OAuth credentials as the existing Google Workspace MCP integration:
- `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` from `.env`
- Token storage at `~/.google-workspace-mcp/credentials/`

## Diagram Rendering

`docctl` also handles diagram rendering as a convenience:

```bash
docctl diagram --input flow.mmd --output flow.svg      # Mermaid
docctl diagram --input arch.dot --output arch.png       # Graphviz
docctl diagram --input seq.puml --output seq.svg        # PlantUML
```

Detection by file extension: `.mmd` → Mermaid CLI (`mmdc`), `.dot` → Graphviz (`dot`), `.puml` → PlantUML (`plantuml`).

## Module Structure

```
halos/docctl/
  __init__.py
  cli.py          # argparse: templates, render, slides, export, new-template, diagram, summary
  templates.py    # template loading, variable parsing, Jinja2 rendering
  renderer.py     # pandoc/marp wrapper, format detection
  diagrams.py     # mermaid/graphviz/plantuml wrapper
  gdrive.py       # Google Drive upload + conversion
  briefing.py     # text_summary() for briefing integration
```

## Dependencies

**Core (NOW):**
- `jinja2` — template rendering
- `pandoc` — system package for document conversion
- `pyyaml` — already a dependency

**Slides (NOW):**
- `@marp-team/marp-cli` — npm package for Marp rendering

**Diagrams (NOW):**
- `mermaid-cli` (`mmdc`) — npm package
- `graphviz` (`dot`) — system package

**Drive export (NEXT):**
- `google-auth`, `google-api-python-client` — same as calctl

## Integration Points

- pyproject.toml — add `docctl = "halos.docctl.cli:main"`
- briefings — render briefing output as formatted PDF/HTML
- mailctl — `docctl render ... | mailctl send --to X --subject Y --attach -`
- nightctl — generate status reports from nightctl data
- dashctl — render dashboard as PDF (complement to --html)

## What It Does NOT Do

- WYSIWYG editing (the agent writes Markdown; humans review rendered output)
- Template design (templates are created once, used many times)
- Replace Google Docs for collaborative editing (it exports TO Docs, doesn't replace it)

## Testing

- Unit tests for template loading, variable validation, Jinja2 rendering
- Unit tests for renderer format detection and command construction
- Integration test: render a letter template to PDF (requires pandoc)
- Integration test: render slides to HTML (requires marp-cli)
- Diagram rendering with fixture .mmd and .dot files
- Google Drive export: mock API, verify upload parameters
- Smoke test: `docctl templates` lists defaults, `docctl render --template letter` produces output
