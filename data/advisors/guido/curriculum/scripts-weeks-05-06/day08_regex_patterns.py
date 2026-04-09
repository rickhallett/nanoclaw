#!/usr/bin/env python3
"""Day 8: regex — lookahead, substitution, real SRE parsing patterns.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-05-06/day08_regex_patterns.py
"""
from IPython import embed
import re

# ============================================================================
# LESSON: Greedy vs non-greedy
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: Greedy vs non-greedy matching")
print("=" * 60)
print()
print("By default, * and + are GREEDY — they match as much as possible.")
print("Add ? to make them NON-GREEDY — match as little as possible.")
print()
print("TRY:")
print()
print("  html = '<b>bold</b> and <i>italic</i>'")
print()
print("  # Greedy: matches from first < to LAST >")
print("  print(re.findall(r'<.*>', html))")
print("  # PREDICT: ?")
print()
print("  # Non-greedy: matches from < to NEXT >")
print("  print(re.findall(r'<.*?>', html))")
print("  # PREDICT: ?")
print()
print("  # Better approach: match anything except >")
print("  print(re.findall(r'<[^>]+>', html))")
print("  # Same result as non-greedy but more explicit")
print()
print("  # Real example: extract quoted strings")
print("  text = 'key=\"value1\" other=\"value2\"'")
print("  greedy = re.findall(r'\".*\"', text)")
print("  lazy = re.findall(r'\".*?\"', text)")
print("  print(f'greedy: {greedy}')")
print("  print(f'lazy: {lazy}')")
print()

embed(header="Checkpoint 1: greedy (.*) vs non-greedy (.*?) vs explicit ([^>]+)")

# ============================================================================
# LESSON: Lookahead and lookbehind
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: Lookahead and lookbehind")
print("=" * 60)
print()
print("Assertions that match a position, not characters.")
print("They don't consume characters — 'zero-width'.")
print()
print("  (?=...)   positive lookahead  (followed by ...)")
print("  (?!...)   negative lookahead  (NOT followed by ...)")
print("  (?<=...)  positive lookbehind (preceded by ...)")
print("  (?<!...)  negative lookbehind (NOT preceded by ...)")
print()
print("TRY:")
print()
print("  # Positive lookahead: numbers followed by 'GB'")
print("  text = '16GB RAM, 8 CPUs, 512MB disk'")
print("  print(re.findall(r'\\d+(?=GB)', text))")
print("  # PREDICT: ? (matches digits, but only if followed by GB)")
print()
print("  # Negative lookahead: numbers NOT followed by letters")
print("  print(re.findall(r'\\d+(?![A-Za-z])', text))")
print("  # PREDICT: ?")
print()
print("  # Positive lookbehind: text after 'error: '")
print("  log = 'error: disk full, info: ok, error: timeout'")
print("  print(re.findall(r'(?<=error: )\\w+', log))")
print("  # PREDICT: ?")
print()
print("  # Negative lookbehind: words NOT preceded by 'error: '")
print("  print(re.findall(r'(?<!error: )\\b\\w+\\b', log))")
print()

embed(header="Checkpoint 2: lookahead/lookbehind — zero-width assertions")

# ============================================================================
# LESSON: re.sub — search and replace
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: re.sub — substitution")
print("=" * 60)
print()
print("re.sub(pattern, replacement, string)")
print()
print("TRY:")
print()
print("  # Simple replacement")
print("  text = 'pod-web-01 pod-web-02 pod-db-01'")
print("  print(re.sub(r'pod-', 'srv-', text))")
print()
print("  # Replace with group reference")
print("  # Swap 'first-last' to 'last, first'")
print("  names = 'john-doe, jane-smith, kai-ocean'")
print("  print(re.sub(r'(\\w+)-(\\w+)', r'\\2, \\1', names))")
print()
print("  # Replace with a function")
print("  def double_numbers(m):")
print("      return str(int(m.group()) * 2)")
print()
print("  text = 'pod has 4 CPUs and 8GB'")
print("  print(re.sub(r'\\d+', double_numbers, text))")
print()
print("  # Mask sensitive data")
print("  log = 'token=abc123secret key=xyz789private'")
print("  masked = re.sub(r'(token|key)=\\S+', r'\\1=***', log)")
print("  print(masked)")
print()
print("  # re.subn — same as sub but returns (new_string, count)")
print("  result, count = re.subn(r'\\d+', 'N', 'port 8080 and port 443')")
print("  print(f'{result} ({count} replacements)')")
print()

embed(header="Checkpoint 3: re.sub — replace with strings, groups, or functions")

# ============================================================================
# LESSON: re.split
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: re.split — split on patterns")
print("=" * 60)
print()
print("str.split() splits on fixed strings. re.split() splits on patterns.")
print()
print("TRY:")
print()
print("  # Split on multiple delimiters")
print("  text = 'one,two;three four\\tfive'")
print("  print(text.split(','))              — only commas")
print("  print(re.split(r'[,;\\s]+', text))  — commas, semicolons, whitespace")
print()
print("  # Split keeping the delimiter (use group)")
print("  text = 'key1=val1&key2=val2&key3=val3'")
print("  print(re.split(r'&', text))        — splits, delimiter gone")
print("  print(re.split(r'(&)', text))      — splits, delimiter kept")
print()
print("  # Real use: split a log line preserving structure")
print("  line = '2026-04-08T09:15:30Z [ERROR] Pod medici: OOMKilled (restarts: 5)'")
print("  parts = re.split(r'[\\[\\]()]', line)")
print("  print([p.strip() for p in parts if p.strip()])")
print()
print("  # maxsplit — split only N times")
print("  log = 'ERROR Failed to connect: connection refused: timeout after 30s'")
print("  level, rest = re.split(r'\\s+', log, maxsplit=1)")
print("  print(f'level: {level}')")
print("  print(f'message: {rest}')")
print()

embed(header="Checkpoint 4: re.split — split on patterns, keep delimiters")

# ============================================================================
# PATTERN: SRE parsing recipes
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: SRE regex recipes")
print("=" * 60)
print()
print("TYPE EACH ONE OUT:")
print()
print("  # 1. Parse key=value pairs")
print("  KV = re.compile(r'(\\w+)=(\\S+)')")
print("  line = 'host=web-01 port=8080 status=running pid=12345'")
print("  pairs = dict(KV.findall(line))")
print("  print(pairs)")
print()
print("  # 2. Extract IP addresses")
print("  IP = re.compile(r'\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b')")
print("  log = 'Connection from 192.168.1.100 to 10.0.0.1 failed'")
print("  print(IP.findall(log))")
print()
print("  # 3. Parse duration strings")
print("  DUR = re.compile(r'(?:(\\d+)h)?\\s*(?:(\\d+)m)?\\s*(?:(\\d+)s)?')")
print("  m = DUR.match('2h 30m 15s')")
print("  if m:")
print("      h, mn, s = (int(x or 0) for x in m.groups())")
print("      total_s = h*3600 + mn*60 + s")
print("      print(f'{h}h {mn}m {s}s = {total_s}s')")
print()
print("  # 4. Validate YAML-like indentation")
print("  INDENT = re.compile(r'^( *)(\\S.*)', re.MULTILINE)")
print("  yaml = '''name: halo")
print("  replicas: 3")
print("  containers:")
print("    - name: web")
print("      image: nginx'''")
print("  for m in INDENT.finditer(yaml):")
print("      depth = len(m.group(1))")
print("      content = m.group(2)")
print("      print(f'  [{depth}] {content}')")
print()

embed(header="Checkpoint 5: SRE regex recipes — KV, IP, duration, indent")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 6: Build a log line parser")
print("=" * 60)
print()
print("Build a function parse_log_line(line) that handles these formats:")
print()
print("  '2026-04-08T09:15:30Z ERROR NATS connection refused'")
print("  '09:15:30 [ERROR] NATS connection refused'")
print("  'Apr  8 09:15:30 web-01 ERROR: NATS connection refused'")
print()
print("Returns: {'timestamp': str, 'level': str, 'message': str}")
print("or None if no pattern matches.")
print()
print("Use re.compile for each pattern. Try them in order.")
print()

sample_lines = [
    "2026-04-08T09:15:30Z ERROR NATS connection refused",
    "09:15:30 [ERROR] NATS connection refused",
    "Apr  8 09:15:30 web-01 ERROR: NATS connection refused",
    "Just some random text",
    "2026-04-08T10:00:00Z INFO Server started on port 8080",
    "10:00:00 [WARN] Memory at 85%",
]

embed(header="Checkpoint 6: multi-format log parser")

print()
print("DAY 8 COMPLETE.")
print()
print("  Greedy (.*) vs non-greedy (.*?) vs explicit ([^>]+)")
print("  Lookahead (?=...) and lookbehind (?<=...)")
print("  re.sub(pattern, replacement, string)")
print("  re.split(pattern, string) — split on regex")
print("  Group references in replacement: \\1, \\2")
print("  Function as replacement for dynamic substitution")
print()
print("Tomorrow: f-strings — the formatting you got wrong on Q12.")
