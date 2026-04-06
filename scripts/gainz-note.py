#!/usr/bin/env python3
"""
Generate Apple Notes for GainzRoshi training days.

Usage:
    python3 scripts/gainz-note.py A          # Create Day A note
    python3 scripts/gainz-note.py B          # Create Day B note
    python3 scripts/gainz-note.py C          # Create Day C note
    python3 scripts/gainz-note.py D          # Create Day D note
    python3 scripts/gainz-note.py E          # Create Day E note
    python3 scripts/gainz-note.py A B        # Create both
    python3 scripts/gainz-note.py all        # Create all five
    python3 scripts/gainz-note.py today      # Auto-pick based on weekday (Mon=A, Tue=B, ...)
    python3 scripts/gainz-note.py tomorrow   # Tomorrow's session
"""

import subprocess, sys, json
from datetime import datetime, timedelta

FOLDER = "GainzRoshi"
ROTATION = ["A", "B", "C", "D", "E"]

DAYS = {
    "A": {
        "title": "Day A // Pull",
        "subtitle": "Vest on. Koan underneath.",
        "exercises": [
            ("Dead hangs", "3x45s", None),
            (None, None, "Lizard pose 45s each side"),
            ("Pull-ups", "4x submaximal (1 from failure)", None),
            (None, None, "Deep lunge twist"),
            ("Chest-to-bar or slow eccentric", "3x5 (4s down)", None),
            (None, None, "Lizard pose"),
            ("Band pull-aparts", "4x15 (heaviest band)", None),
            ("Gravity boot rows or shrugs", "3x8", None),
        ],
        "trackctl": 'trackctl add movement --duration 30 --notes "A: pull"',
    },
    "B": {
        "title": "Day B // Push",
        "subtitle": "Vest on. Koan underneath.",
        "exercises": [
            ("Hindu push-ups", "3x20 (vested)", None),
            (None, None, "Cobra to upward dog, 5 breaths"),
            ("Dips", "4x submaximal (vested, full depth)", None),
            (None, None, "Cobra to upward dog, 5 breaths"),
            ("Parallette push-ups", "feet elevated 3x12", None),
            (None, None, "Cobra to upward dog, 5 breaths"),
            ("Handstand wall hold", "3x30-45s (vest off)", None),
            ("Handstand push-up negatives", "3x3, 5s eccentric (vest off)", None),
            ("Band press-outs", "3x15 (heavy band, full extension)", None),
        ],
        "trackctl": 'trackctl add movement --duration 30 --notes "B: push"',
    },
    "C": {
        "title": "Day C // Legs + KB",
        "subtitle": "Vest on for bodyweight, off for KB.",
        "exercises": [
            ("KB swings", "5x20, 24kg (100 total, non-negotiable)", None),
            (None, None, "Pigeon pose 45s each side"),
            ("Goblet squats", "4x12 (24kg)", None),
            (None, None, "Warrior III hold 30s each side"),
            ("Pistol squat practice", "4x5 each (try raw first)", None),
            (None, None, "Pigeon pose 45s each side"),
            ("KB Romanian deadlift", "3x12 (single leg if stable)", None),
            ("Walking lunges", "3x12 each (vest on)", None),
        ],
        "trackctl": 'trackctl add movement --duration 30 --notes "C: legs+kb"',
    },
    "D": {
        "title": "Day D // Flow + Skill",
        "subtitle": "Vest optional. Follow the body. Explore at intensity.",
        "exercises": [
            ("Parallette L-sit hold", "max hold, 4 rounds", None),
            ("Crow pose", "45s (or press to handstand)", None),
            ("Wall HSPU negatives", "x3", None),
            ("Wheel pose", "x3 reps (hold top 3 breaths)", None),
            ("KB Turkish get-up", "x1 each side (24kg, slow)", None),
            (None, None, "Freeform hatha flow between rounds, 2 min minimum"),
        ],
        "trackctl": 'trackctl add movement --duration 30 --notes "D: flow+skill"',
    },
    "E": {
        "title": "Day E // KB Complex",
        "subtitle": "No vest. The kettlebell is enough.",
        "exercises": [
            ("EMOM 20 min", "odd: clean+press x5 each, even: front rack squat x8", None),
            (None, None, "Warrior I/II, triangle, half moon"),
            ("KB snatch practice", "3x5 each (or high pull 3x8)", None),
            ("KB farmers carry", "3x60s (crush grip, shoulders packed)", None),
            ("Turkish get-up", "x2 each side, slowest thing all week", None),
        ],
        "trackctl": 'trackctl add movement --duration 30 --notes "E: kb complex"',
    },
}


def build_html(day_key):
    day = DAYS[day_key]
    parts = []
    parts.append(f"<h1>{day['title']}</h1>")
    parts.append(f"<p style='color:gray'>{day['subtitle']}</p>")
    parts.append("<br>")
    parts.append("<h2>Open (5 min)</h2>")
    parts.append("<ul><li>Sun salutation A x5, vested, controlled pace</li></ul>")
    parts.append("<br>")
    parts.append("<h2>Main (25 min)</h2>")
    parts.append("<ul>")
    for name, detail, hold in day["exercises"]:
        if hold:
            parts.append(
                f"<li style='color:gray; margin-left:20px'>{hold}</li>"
            )
        else:
            parts.append(f"<li><b>{name}</b> {detail}</li>")
    parts.append("</ul>")
    parts.append("<br>")
    parts.append("<h2>Close (5-10 min)</h2>")
    parts.append("<ul>")
    parts.append("<li>Gravity boots, 3 min</li>")
    parts.append("<li>Wheel pose, attempts not prep</li>")
    parts.append("<li>Seated forward fold, 10 breaths</li>")
    parts.append("</ul>")
    parts.append("<br>")
    parts.append(f"<p><code>{day['trackctl']}</code></p>")
    return "".join(parts)


def create_note(day_key):
    day = DAYS[day_key]
    html = build_html(day_key)
    # Escape for JXA
    html_escaped = html.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "")
    title = day["title"]
    title_escaped = title.replace('"', '\\"')

    jxa = f"""
var Notes = Application("Notes");
var acc = Notes.defaultAccount();
var folders = acc.folders();
var targetFolder = null;
for (var i = 0; i < folders.length; i++) {{
    if (folders[i].name() === "{FOLDER}") {{ targetFolder = folders[i]; break; }}
}}
if (!targetFolder) {{
    var f = Notes.Folder({{name: "{FOLDER}"}});
    acc.folders.push(f);
    folders = acc.folders();
    for (var i = 0; i < folders.length; i++) {{
        if (folders[i].name() === "{FOLDER}") {{ targetFolder = folders[i]; break; }}
    }}
}}
// Remove existing note with same title
var existing = targetFolder.notes();
for (var i = existing.length - 1; i >= 0; i--) {{
    if (existing[i].name() === "{title_escaped}") {{
        Notes.delete(existing[i]);
    }}
}}
var note = Notes.Note({{name: "{title_escaped}", body: "{html_escaped}"}});
targetFolder.notes.push(note);
"{title_escaped}";
"""
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", jxa],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode == 0:
        print(f"  Created: {title}")
    else:
        print(f"  Failed: {title} -- {result.stderr.strip()}")


def resolve_days(args):
    if not args:
        print(__doc__)
        sys.exit(1)

    days = []
    for arg in args:
        arg = arg.upper().strip()
        if arg == "ALL":
            return list(DAYS.keys())
        elif arg == "TODAY":
            idx = datetime.now().weekday()  # Mon=0
            if idx < 5:
                days.append(ROTATION[idx])
            else:
                print("  Weekend: autonomous session. Pick your own.")
                sys.exit(0)
        elif arg == "TOMORROW":
            idx = (datetime.now() + timedelta(days=1)).weekday()
            if idx < 5:
                days.append(ROTATION[idx])
            else:
                print("  Weekend: autonomous session. Pick your own.")
                sys.exit(0)
        elif arg in DAYS:
            days.append(arg)
        else:
            print(f"  Unknown day: {arg}. Use A/B/C/D/E, all, today, tomorrow.")
            sys.exit(1)
    return days


if __name__ == "__main__":
    targets = resolve_days(sys.argv[1:])
    for day in targets:
        create_note(day)
