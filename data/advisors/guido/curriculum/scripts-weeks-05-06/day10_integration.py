#!/usr/bin/env python3
"""Day 10: Capstone — config file parser + log timestamp analyser.

Combines: pathlib, closures/decorators, datetime/timezone, regex, f-strings.
All stdlib. The full Weeks 5-6 toolkit.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-05-06/day10_integration.py
"""
from IPython import embed
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
from functools import wraps
import re
import json
import time
import tempfile

# ============================================================================
# PHASE 1: Config file parser
# ============================================================================

print("=" * 60)
print("PHASE 1: Build a config file parser")
print("=" * 60)
print()
print("Parse an INI-style config into a nested dict.")
print("Uses: pathlib (read), regex (parse), closures (validators).")
print()
print("TYPE THIS OUT:")
print()
print("  # Regex patterns")
print("  SECTION = re.compile(r'^\\[(?P<name>[\\w.-]+)\\]$')")
print("  KEYVAL = re.compile(r'^(?P<key>[\\w.-]+)\\s*=\\s*(?P<value>.+)$')")
print("  COMMENT = re.compile(r'^[#;]')")
print()
print("  def parse_config(text):")
print("      config = {}")
print("      section = 'default'")
print("      config[section] = {}")
print("      for line_no, line in enumerate(text.strip().split('\\n'), 1):")
print("          line = line.strip()")
print("          if not line or COMMENT.match(line):")
print("              continue")
print("          m = SECTION.match(line)")
print("          if m:")
print("              section = m.group('name')")
print("              config.setdefault(section, {})")
print("              continue")
print("          m = KEYVAL.match(line)")
print("          if m:")
print("              config[section][m.group('key')] = m.group('value')")
print("              continue")
print("          raise ValueError(f'Line {line_no}: unparseable: {line!r}')")
print("      return config")
print()

config_text = """# Halo Fleet Configuration
; Generated 2026-04-08

[server]
host = 0.0.0.0
port = 8080
workers = 4
debug = false

[database]
host = postgres.halo-fleet.svc.cluster.local
port = 5432
name = halo_prod
pool_size = 10

[nats]
url = nats://nats.halo-fleet.svc.cluster.local:4222
max_reconnects = 10
reconnect_wait = 2s

[logging]
level = INFO
format = json
file = /var/log/halo/app.log
rotation = 10MB
"""

embed(header="Phase 1: parse_config — regex + pathlib. config_text is ready.")

# ============================================================================
# PHASE 2: Config validator using closures
# ============================================================================

print()
print("=" * 60)
print("PHASE 2: Validate config with closure-based validators")
print("=" * 60)
print()
print("Build validator factories (closures!) and apply them.")
print()
print("TYPE THIS OUT:")
print()
print("  def in_range(low, high):")
print("      def validator(value):")
print("          n = int(value)")
print("          if not (low <= n <= high):")
print("              raise ValueError(f'{n} not in range [{low}, {high}]')")
print("          return n")
print("      return validator")
print()
print("  def one_of(*choices):")
print("      def validator(value):")
print("          if value not in choices:")
print("              raise ValueError(f'{value!r} not in {choices}')")
print("          return value")
print("      return validator")
print()
print("  def as_bool(value):")
print("      if value.lower() in ('true', '1', 'yes'): return True")
print("      if value.lower() in ('false', '0', 'no'): return False")
print("      raise ValueError(f'{value!r} is not a boolean')")
print()
print("  SCHEMA = {")
print("      'server': {")
print("          'port': in_range(1, 65535),")
print("          'workers': in_range(1, 32),")
print("          'debug': as_bool,")
print("      },")
print("      'database': {")
print("          'port': in_range(1, 65535),")
print("          'pool_size': in_range(1, 100),")
print("      },")
print("      'logging': {")
print("          'level': one_of('DEBUG', 'INFO', 'WARNING', 'ERROR'),")
print("          'format': one_of('json', 'text'),")
print("      },")
print("  }")
print()
print("  def validate_config(config, schema):")
print("      errors = []")
print("      for section, validators in schema.items():")
print("          for key, validator in validators.items():")
print("              value = config.get(section, {}).get(key)")
print("              if value is None:")
print("                  errors.append(f'[{section}].{key}: missing')")
print("                  continue")
print("              try:")
print("                  config[section][key] = validator(value)")
print("              except ValueError as e:")
print("                  errors.append(f'[{section}].{key}: {e}')")
print("      return errors")
print()

embed(header="Phase 2: closure validators — type out the schema and validate")

# ============================================================================
# PHASE 3: Log timestamp analyser
# ============================================================================

print()
print("=" * 60)
print("PHASE 3: Log timestamp analyser")
print("=" * 60)
print()
print("Parse log timestamps, normalise to UTC, analyse time gaps.")
print("Uses: datetime/timezone, regex, f-string formatting.")
print()
print("TYPE THIS OUT:")
print()
print("  # Multi-format timestamp parser")
print("  FORMATS = [")
print("      (re.compile(r'(\\d{4}-\\d{2}-\\d{2}T[\\d:]+)Z'), '%Y-%m-%dT%H:%M:%S', timezone.utc),")
print("      (re.compile(r'(\\d{4}-\\d{2}-\\d{2}T[\\d:]+)\\+(\\d{2}):(\\d{2})'), '%Y-%m-%dT%H:%M:%S', None),")
print("      (re.compile(r'(\\d{2}:\\d{2}:\\d{2})'), '%H:%M:%S', None),")
print("  ]")
print()
print("  def parse_timestamp(s):")
print("      '''Parse a timestamp string into an aware UTC datetime.'''")
print("      # ISO with Z")
print("      m = re.match(r'(\\d{4}-\\d{2}-\\d{2}T[\\d:.]+)Z', s)")
print("      if m:")
print("          dt = datetime.fromisoformat(m.group(1))")
print("          return dt.replace(tzinfo=timezone.utc)")
print()
print("      # ISO with offset")
print("      m = re.match(r'(\\d{4}-\\d{2}-\\d{2}T[\\d:.]+[+-]\\d{2}:\\d{2})', s)")
print("      if m:")
print("          return datetime.fromisoformat(m.group(1)).astimezone(timezone.utc)")
print()
print("      # Time only (assume today, UTC)")
print("      m = re.match(r'(\\d{2}:\\d{2}:\\d{2})', s)")
print("      if m:")
print("          t = datetime.strptime(m.group(1), '%H:%M:%S')")
print("          today = datetime.now(timezone.utc).date()")
print("          return datetime.combine(today, t.time(), tzinfo=timezone.utc)")
print()
print("      return None")
print()

embed(header="Phase 3: timestamp parser — type it out")

# ============================================================================
# PHASE 4: Full pipeline — analyse log timestamps
# ============================================================================

print()
print("=" * 60)
print("PHASE 4: Analyse time gaps and format a report")
print("=" * 60)
print()
print("Given log lines with timestamps and levels:")
print("  1. Parse each timestamp with parse_timestamp()")
print("  2. Calculate gap between consecutive entries")
print("  3. Find the largest gap (potential outage)")
print("  4. Group entries by hour")
print("  5. Format a report with f-string alignment")
print()

log_data = """2026-04-08T09:01:15Z INFO Server started
2026-04-08T09:01:16Z INFO Connected to DB
2026-04-08T09:05:12Z WARN Slow query
2026-04-08T09:06:00Z INFO Request processed
2026-04-08T09:08:45Z WARN Memory at 82%
2026-04-08T09:10:00Z ERROR NATS connection refused
2026-04-08T09:10:05Z ERROR Retry 1/3
2026-04-08T09:10:10Z ERROR Retry 2/3
2026-04-08T09:10:15Z INFO NATS reconnected
2026-04-08T09:45:00Z INFO Health check
2026-04-08T10:01:00Z INFO Scheduled job
2026-04-08T10:05:15Z WARN Cert expires in 7d
2026-04-08T10:10:00Z ERROR Backup failed
2026-04-08T11:00:00Z INFO Shift handoff"""

LOG_LINE = re.compile(r'(?P<ts>\S+)\s+(?P<level>\w+)\s+(?P<msg>.*)')

print("'log_data' and LOG_LINE regex are ready.")
print()
print("Build the analysis:")
print("  1. Parse lines with LOG_LINE.match()")
print("  2. Parse timestamps with parse_timestamp()")
print("  3. Find gaps: [(gap_seconds, line_before, line_after)]")
print("  4. Find the largest gap")
print("  5. Count entries per hour")
print("  6. Format a report like:")
print()
print("  ╔══════════════════════════════════════════╗")
print("  ║ LOG ANALYSIS REPORT                      ║")
print("  ╠══════════════════════════════════════════╣")
print("  ║ Total entries:       14                  ║")
print("  ║ Time span:           1h 58m 45s          ║")
print("  ║ Largest gap:         34m 45s (09:10-09:45║")
print("  ║                                          ║")
print("  ║ Entries per hour:                        ║")
print("  ║   09:00  ████████████████████  9          ║")
print("  ║   10:00  ██████              3          ║")
print("  ║   11:00  ██                  1          ║")
print("  ║                                          ║")
print("  ║ Level distribution:                      ║")
print("  ║   INFO      7  ██████████████            ║")
print("  ║   ERROR     3  ██████                    ║")
print("  ║   WARN      3  ██████                    ║")
print("  ╚══════════════════════════════════════════╝")
print()

embed(header="Phase 4: full analysis — parse, compute, format")

# ============================================================================
# WEEK 5-6 CHECKPOINT QUIZ
# ============================================================================

print()
print("=" * 60)
print("FINAL QUIZ: Answer from memory")
print("=" * 60)
print()
print("  PATHLIB:")
print("  1. Path('file.tar.gz').suffix → ?")
print("  2. Path('file.tar.gz').stem → ?")
print("  3. What does resolve() do?")
print("  4. How do you join paths? (not os.path.join)")
print()
print("  CLOSURES:")
print("  5. [lambda x: x*i for i in range(4)] — what does [f(2) for f in fns] give?")
print("  6. How do you fix it?")
print("  7. What does nonlocal do?")
print()
print("  DATETIME:")
print("  8. datetime.now().tzinfo → ?")
print("  9. datetime.now(timezone.utc).tzinfo → ?")
print("  10. Can you subtract naive from aware?")
print()
print("  REGEX:")
print("  11. re.findall(r'error: (\\d+)', text) — what does it return if groups exist?")
print("  12. group(0) vs group(1)?")
print()
print("  F-STRINGS:")
print("  13. f'{name:>20}' — left or right aligned?")
print("  14. f'{val:.2%}' — what does this format?")
print()

embed(header="Final quiz — verify in REPL")

print()
print("=" * 60)
print("WEEKS 5-6 COMPLETE")
print("=" * 60)
print()
print("You now own:")
print("  pathlib:    anatomy, glob, read/write, resolve")
print("  closures:   LEGB, late binding trap, nonlocal, decorators")
print("  datetime:   naive vs aware, UTC-everywhere, formatting")
print("  regex:      match/search/findall, groups, sub, lookahead")
print("  f-strings:  alignment, numbers, debug, tables")
print()
print("Combined with Weeks 1-4, you now cover Domains 1-4, 8-10")
print("from the original exam. When ready: summon Guido for re-test.")
