#!/usr/bin/env python3
"""Day 9: f-strings — alignment, fill, number formatting, debug (exam Q12).

You reversed > and < on the exam. Never again.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-05-06/day09_fstrings_formatting.py
"""
from IPython import embed

# ============================================================================
# LESSON: Alignment — the exam question
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: Alignment (exam Q12 correction)")
print("=" * 60)
print()
print("THE RULE:")
print("  < = left align   (pad RIGHT with fill)")
print("  > = right align  (pad LEFT with fill)")
print("  ^ = center       (pad BOTH sides)")
print()
print("Think of the arrow: > points right, text goes to the RIGHT side.")
print()
print("TRY (predict BEFORE each one):")
print()
print("  name = 'kai'")
print()
print("  print(f'{name:<20}|')    — left align, 20 wide")
print("  print(f'{name:>20}|')    — right align, 20 wide")
print("  print(f'{name:^20}|')    — center, 20 wide")
print()
print("  # With fill character")
print("  print(f'{name:*<20}|')   — left, fill with *")
print("  print(f'{name:*>20}|')   — right, fill with *")
print("  print(f'{name:*^20}|')   — center, fill with *")
print()
print("  # EXAM Q12 was:")
print("  # f'{name:>20}'  → right-aligned (padded left with spaces)")
print("  # f'{name:*^20}' → centered (padded both sides with stars)")
print("  # You reversed them. The > means text goes to the RIGHT.")
print()

embed(header="Checkpoint 1: alignment — > is RIGHT-align. < is LEFT-align.")

# ============================================================================
# LESSON: Number formatting
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: Number formatting")
print("=" * 60)
print()
print("TRY EACH (predict first):")
print()
print("  # Integers")
print("  n = 42")
print("  print(f'{n:d}')       — 42 (decimal, default)")
print("  print(f'{n:05d}')     — 00042 (zero-padded, 5 wide)")
print("  print(f'{n:>10d}')    — '        42' (right-aligned, 10 wide)")
print("  print(f'{n:x}')       — 2a (hexadecimal)")
print("  print(f'{n:b}')       — 101010 (binary)")
print("  print(f'{n:o}')       — 52 (octal)")
print()
print("  # Floats")
print("  pi = 3.14159265")
print("  print(f'{pi:.2f}')    — 3.14 (2 decimal places)")
print("  print(f'{pi:.4f}')    — 3.1416 (4 decimal places, rounded)")
print("  print(f'{pi:10.2f}')  — '      3.14' (10 wide, 2 decimals)")
print()
print("  # Thousands separator")
print("  big = 1234567")
print("  print(f'{big:,}')     — 1,234,567")
print("  print(f'{big:_}')     — 1_234_567 (underscore separator)")
print()
print("  # Percentage")
print("  ratio = 0.85")
print("  print(f'{ratio:.1%}')  — 85.0%")
print("  print(f'{ratio:.0%}')  — 85%")
print()

embed(header="Checkpoint 2: number formatting — d, f, x, b, comma, percent")

# ============================================================================
# LESSON: String formatting details
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: String formatting")
print("=" * 60)
print()
print("TRY:")
print()
print("  # Truncation")
print("  long = 'CrashLoopBackOff'")
print("  print(f'{long:.8}')       — first 8 chars: 'CrashLoo'")
print("  print(f'{long:>20.8}')    — truncate AND right-align")
print()
print("  # repr vs str")
print("  text = 'hello\\nworld'")
print("  print(f'{text}')          — renders newline")
print("  print(f'{text!r}')        — shows escape: 'hello\\\\nworld'")
print("  print(f'{text!s}')        — str() (default)")
print("  print(f'{text!a}')        — ascii() (escape non-ASCII)")
print()
print("  # Dynamic width/precision")
print("  width = 30")
print("  precision = 3")
print("  pi = 3.14159")
print("  print(f'{pi:{width}.{precision}f}')  — 30 wide, 3 decimals")
print()
print("  # Nested f-strings (Python 3.12+)")
print("  items = ['musashi', 'medici', 'bankei']")
print("  print(f\"advisors: {', '.join(items)}\")")
print()

embed(header="Checkpoint 3: truncation, !r, dynamic width")

# ============================================================================
# LESSON: Debug format (= sign)
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: The = debug shorthand (Python 3.8+)")
print("=" * 60)
print()
print("The = sign after an expression prints both the expression and value.")
print()
print("TRY:")
print()
print("  x = 42")
print("  name = 'kai'")
print("  items = [1, 2, 3]")
print()
print("  print(f'{x=}')          — 'x=42'")
print("  print(f'{name=}')       — \"name='kai'\"")
print("  print(f'{len(items)=}') — 'len(items)=3'")
print("  print(f'{x=:05d}')      — 'x=00042' (= with format spec)")
print()
print("  # Incredibly useful for debugging:")
print("  pod = {'name': 'medici', 'status': 'CrashLoopBackOff', 'restarts': 7}")
print("  print(f\"{pod['name']=}, {pod['status']=}, {pod['restarts']=}\")")
print()
print("  # Quick variable dump")
print("  a, b, c = 10, 20, 30")
print("  print(f'{a=} {b=} {c=} {a+b+c=}')")
print()

embed(header="Checkpoint 4: f'{x=}' — the debug shorthand")

# ============================================================================
# LESSON: Building tables and reports
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: Formatted tables")
print("=" * 60)
print()
print("TRY — build a formatted pod status table:")
print()
print("  pods = [")
print("      ('advisor-musashi', 'Running', 0, '5d'),")
print("      ('advisor-medici', 'CrashLoopBackOff', 7, '5d'),")
print("      ('advisor-bankei', 'Running', 0, '5d'),")
print("      ('advisor-gibson', 'OOMKilled', 3, '2d'),")
print("      ('nginx-deploy', 'Running', 0, '12d'),")
print("  ]")
print()
print("  # Header")
print("  print(f'{\"NAME\":<25} {\"STATUS\":<20} {\"RESTARTS\":>8} {\"AGE\":>5}')")
print("  print('-' * 60)")
print()
print("  # Rows")
print("  for name, status, restarts, age in pods:")
print("      print(f'{name:<25} {status:<20} {restarts:>8} {age:>5}')")
print()
print("  # Conditional formatting")
print("  for name, status, restarts, age in pods:")
print("      marker = '!!' if status != 'Running' else '  '")
print("      print(f'{marker} {name:<25} {status:<20} {restarts:>8}')")
print()

embed(header="Checkpoint 5: formatted tables — alignment in practice")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 6: Build a metric dashboard formatter")
print("=" * 60)
print()
print("Build a function format_dashboard(metrics) that takes a dict of")
print("metric_name → value and produces a clean dashboard like:")
print()
print("  ╔══════════════════════════════════╗")
print("  ║ SYSTEM DASHBOARD                 ║")
print("  ╠══════════════════════════════════╣")
print("  ║ CPU Usage        ████████░░  85% ║")
print("  ║ Memory           ██████░░░░  62% ║")
print("  ║ Disk /           █████████░  92% ║")
print("  ║ Pods Running     8/10            ║")
print("  ║ Uptime           14d 3h 22m      ║")
print("  ╚══════════════════════════════════╝")
print()
print("Use f-string alignment for columns.")
print("Use block characters (█ and ░) for progress bars.")
print("Conditionally colour critical metrics (or just mark with !!).")
print()

metrics = {
    'CPU Usage': 0.85,
    'Memory': 0.62,
    'Disk /': 0.92,
    'Disk /data': 0.44,
    'Pods Running': (8, 10),
    'NATS Lag': 12,
    'Error Rate': 0.03,
}

embed(header="Checkpoint 6: metric dashboard — f-string mastery")

print()
print("DAY 9 COMPLETE.")
print()
print("  < left   > right   ^ center")
print("  > means text goes to the RIGHT. Arrow points where text goes.")
print("  {val:.2f}  — 2 decimal places")
print("  {val:,}    — thousands separator")
print("  {val:.0%}  — percentage")
print("  {val:05d}  — zero-padded")
print("  {val!r}    — repr")
print("  {val=}     — debug (shows name=value)")
print()
print("Tomorrow: capstone — config parser + log timestamp analyser.")
