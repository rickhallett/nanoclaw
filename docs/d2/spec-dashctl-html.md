# dashctl --html — Static HTML Dashboard Export

**Date:** 2026-03-21
**Status:** SPEC
**Tier:** NOW
**Effort:** ~5 agent-min + ~10 human-min review

---

## Purpose

Export the existing Rich TUI dashboard as a static HTML page. Same data, same layout, viewable in a browser. Useful for sharing, viewing on devices without terminal access, or embedding in briefings.

## CLI Interface

```
dashctl --html [--output PATH]           # render to HTML file
dashctl --html --open                    # render and open in browser
```

Default output: `store/dashboard.html` (overwritten each run).

## Implementation

Rich's `Console` supports HTML export natively:

```python
from rich.console import Console

console = Console(record=True, width=120)
# render all panels to console
for panel in full_dashboard():
    console.print(panel)
html = console.export_html(inline_styles=True)
```

`inline_styles=True` ensures the HTML is self-contained — no external CSS needed.

## Additions to Existing Code

### `halos/dashctl/cli.py`
- Add `--html` flag and optional `--output` path
- Add `--open` flag (calls `webbrowser.open()` after writing)

### `halos/dashctl/panels.py`
- No changes needed — `full_dashboard()` already returns Rich renderables

## HTML Template

Wrap Rich's exported HTML in a minimal page:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>NanoClaw Dashboard — {timestamp}</title>
  <style>
    body { background: #1a1a2e; margin: 2rem auto; max-width: 900px; }
    pre { font-family: 'Geist Mono', 'JetBrains Mono', monospace; }
  </style>
</head>
<body>
{rich_html}
</body>
</html>
```

Dark background to match the terminal aesthetic.

## Dependencies

- None new. Rich already supports HTML export.

## Integration Points

- Briefings could attach the HTML dashboard as a file (via mailctl or channel attachment)
- calctl and statusctl panels (once built) automatically appear in the HTML export since they'll be added to `full_dashboard()`

## Testing

- Verify HTML output is valid and self-contained
- Verify all panels render (no Rich-specific terminal escapes leaking into HTML)
