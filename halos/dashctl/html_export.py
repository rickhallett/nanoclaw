"""HTML export for the dashctl dashboard.

Renders Rich panels to a self-contained HTML page using
Rich's built-in HTML export with inline styles.
"""

from datetime import datetime, timezone

from rich.console import Console


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NanoClaw Dashboard — {timestamp}</title>
  <style>
    body {{
      background: #1a1a2e;
      color: #e0e0e0;
      margin: 2rem auto;
      max-width: 960px;
      padding: 0 1rem;
    }}
    pre {{
      font-family: 'Geist Mono', 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 14px;
      line-height: 1.4;
    }}
  </style>
</head>
<body>
{rich_html}
</body>
</html>"""


def render_html(panels: list, output_path: str) -> str:
    """Render Rich panels to a self-contained HTML file.

    Args:
        panels: List of Rich renderables (from full_dashboard()).
        output_path: Filesystem path to write the HTML file.

    Returns:
        The absolute path of the written file.
    """
    console = Console(record=True, width=120, force_terminal=True)
    for panel in panels:
        console.print(panel)

    rich_html = console.export_html(inline_styles=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = _HTML_TEMPLATE.format(timestamp=timestamp, rich_html=rich_html)

    from pathlib import Path

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")

    return str(path.resolve())
