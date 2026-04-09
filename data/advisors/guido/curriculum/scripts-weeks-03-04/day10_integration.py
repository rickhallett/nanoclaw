#!/usr/bin/env python3
"""Day 10: Capstone — log analyser combining logging + exceptions + itertools + generators.

This is the final exercise for Weeks 3-4.
Build a production-quality log analyser using only stdlib.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-03-04/day10_integration.py
"""
from IPython import embed
import logging
import logging.handlers
import json
import sys
import os
import tempfile
from collections import Counter, defaultdict, deque
from itertools import groupby, chain, islice, accumulate
from contextlib import contextmanager
from pathlib import Path

# ============================================================================
# THE CAPSTONE: Production log analyser
# ============================================================================

print("=" * 60)
print("CAPSTONE: Build a production log analyser")
print("=" * 60)
print()
print("You will build a tool that:")
print("  1. Reads and parses log files (generators)")
print("  2. Analyses patterns (itertools + collections)")
print("  3. Handles errors gracefully (try/except/else/finally)")
print("  4. Logs its own operations (logging module)")
print()
print("All stdlib. No external packages.")
print()

# ============================================================================
# PHASE 1: Setup logging for the analyser itself
# ============================================================================

print("=" * 60)
print("PHASE 1: Setup the analyser's own logging")
print("=" * 60)
print()
print("TYPE THIS OUT — your analyser logs its own operations:")
print()
print("  def setup_analyser_logging(verbose=False):")
print("      logger = logging.getLogger('analyser')")
print("      logger.setLevel(logging.DEBUG)")
print("      logger.handlers.clear()")
print()
print("      console = logging.StreamHandler(sys.stderr)")
print("      console.setLevel(logging.DEBUG if verbose else logging.WARNING)")
print("      console.setFormatter(logging.Formatter(")
print("          '%(asctime)s %(levelname)-8s %(message)s', datefmt='%H:%M:%S'))")
print("      logger.addHandler(console)")
print("      return logger")
print()
print("  log = setup_analyser_logging(verbose=True)")
print("  log.info('Analyser started')")
print()

embed(header="Phase 1: setup logging — type out setup_analyser_logging()")

# ============================================================================
# PHASE 2: Generator pipeline for log parsing
# ============================================================================

print()
print("=" * 60)
print("PHASE 2: Generator pipeline")
print("=" * 60)
print()
print("Build four generator stages:")
print()
print("  def read_lines(source):")
print("      '''Yield lines from a string or file path.'''")
print("      if isinstance(source, Path) or os.path.isfile(str(source)):")
print("          try:")
print("              with open(source) as f:")
print("                  yield from f")
print("          except (FileNotFoundError, PermissionError) as e:")
print("              logging.getLogger('analyser').error('Cannot read %s: %s', source, e)")
print("      else:")
print("          yield from source.strip().split('\\n')")
print()
print("  def parse_entries(lines):")
print("      '''Yield {ts, level, message} dicts. Skip unparseable lines.'''")
print("      for line_no, line in enumerate(lines, 1):")
print("          line = line.strip()")
print("          if not line or line.startswith('#'):")
print("              continue")
print("          parts = line.split(None, 2)")
print("          if len(parts) >= 3:")
print("              yield {'ts': parts[0], 'level': parts[1],")
print("                     'message': parts[2], 'line_no': line_no}")
print()
print("  def filter_level(entries, min_level='INFO'):")
print("      '''Yield entries at or above min_level.'''")
print("      levels = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'WARNING': 2,")
print("                'ERROR': 3, 'CRITICAL': 4}")
print("      threshold = levels.get(min_level, 0)")
print("      for entry in entries:")
print("          if levels.get(entry['level'], 0) >= threshold:")
print("              yield entry")
print()
print("  def enrich(entries):")
print("      '''Add computed fields: hour, is_error.'''")
print("      for entry in entries:")
print("          entry['hour'] = entry['ts'].split(':')[0]")
print("          entry['is_error'] = entry['level'] in ('ERROR', 'CRITICAL')")
print("          yield entry")
print()

embed(header="Phase 2: type out the four generator stages")

# ============================================================================
# PHASE 3: Analysis with collections + itertools
# ============================================================================

print()
print("=" * 60)
print("PHASE 3: Analysis functions")
print("=" * 60)
print()
print("Build analysis functions that consume the generator pipeline:")
print()
print("  def analyse(entries):")
print("      '''Consume entries and produce a report dict.'''")
print("      level_counts = Counter()")
print("      by_hour = defaultdict(list)")
print("      error_window = deque(maxlen=10)")
print("      total = 0")
print()
print("      for entry in entries:")
print("          total += 1")
print("          level_counts[entry['level']] += 1")
print("          by_hour[entry['hour']].append(entry)")
print("          if entry['is_error']:")
print("              error_window.append(entry)")
print()
print("      # Group errors by hour for trend")
print("      error_trend = {}")
print("      for hour, events in sorted(by_hour.items()):")
print("          error_trend[hour] = sum(1 for e in events if e['is_error'])")
print()
print("      return {")
print("          'total_entries': total,")
print("          'level_distribution': dict(level_counts.most_common()),")
print("          'entries_per_hour': {h: len(v) for h, v in sorted(by_hour.items())},")
print("          'error_trend': error_trend,")
print("          'recent_errors': [e['message'] for e in error_window],")
print("      }")
print()

embed(header="Phase 3: type out the analyse() function")

# ============================================================================
# PHASE 4: Putting it all together
# ============================================================================

print()
print("=" * 60)
print("PHASE 4: Full pipeline")
print("=" * 60)
print()
print("Assemble the pipeline and run the analysis.")
print()
print("'sample_log' is ready. Wire up the pipeline:")
print()
print("  pipeline = enrich(filter_level(parse_entries(read_lines(sample_log)), 'INFO'))")
print("  report = analyse(pipeline)")
print("  print(json.dumps(report, indent=2))")
print()
print("Then add error handling:")
print()
print("  try:")
print("      pipeline = enrich(filter_level(parse_entries(read_lines(sample_log))))")
print("      report = analyse(pipeline)")
print("  except Exception as e:")
print("      log.exception('Analysis failed')")
print("      report = {'error': str(e)}")
print("  else:")
print("      log.info('Analysis complete: %d entries', report['total_entries'])")
print("  finally:")
print("      log.info('Pipeline finished')")
print()

sample_log = """# Application log — 2026-04-08
# Format: timestamp level message
09:01:15 INFO Server started on port 8080
09:01:16 INFO Connected to PostgreSQL
09:01:17 DEBUG Health check endpoint registered
09:02:30 DEBUG Periodic health check: OK
09:05:12 WARN Slow query: SELECT * FROM pods WHERE status='pending' (2.3s)
09:06:00 INFO Request: GET /api/pods (200, 45ms)
09:06:30 INFO Request: POST /api/deploy (201, 230ms)
09:07:00 DEBUG GC pause: 12ms
09:08:45 WARN Memory usage at 82%
09:09:00 INFO Request: GET /api/health (200, 8ms)
09:10:00 ERROR Failed to connect to NATS: connection refused
09:10:05 ERROR Retry 1/3: NATS connection failed
09:10:10 ERROR Retry 2/3: NATS connection failed
09:10:15 INFO NATS reconnected after 3 attempts
09:12:00 WARN Disk usage at 88% on /data
09:15:30 CRITICAL etcd leader election failed — entering read-only mode
09:15:31 CRITICAL kubectl apply rejected: cluster is read-only
09:16:00 ERROR Deployment rollback triggered
09:18:00 WARN Pod advisor-gibson memory approaching limit
09:20:00 INFO Recovery: etcd leader elected
09:20:01 INFO Cluster back to read-write mode
09:22:00 INFO Deployment retry succeeded
09:25:00 DEBUG Metrics flush: 847 datapoints
10:01:00 INFO Scheduled maintenance job started
10:05:15 WARN Certificate expires in 7 days
10:10:00 ERROR Backup failed: insufficient disk space
10:15:00 INFO Maintenance job completed with warnings
10:30:00 DEBUG Health check: OK
11:00:00 INFO Shift handoff: no active incidents"""

embed(header="Phase 4: assemble and run the full pipeline")

# ============================================================================
# PHASE 5: Extensions
# ============================================================================

print()
print("=" * 60)
print("PHASE 5: Extend the analyser")
print("=" * 60)
print()
print("If you have time, add these features:")
print()
print("  1. Use accumulate() to show cumulative error count over time")
print()
print("  2. Use groupby() on sorted entries to show entries per level")
print("     (remember: sort first, then groupby)")
print()
print("  3. Add a @contextmanager timer that logs how long analysis took")
print()
print("  4. Write the report to a JSON file using FileHandler")
print()
print("  5. Add a custom AnalysisError exception that carries the report")
print("     so far when something fails mid-analysis")
print()

embed(header="Phase 5: extensions — push further if time permits")

# ============================================================================
# WEEK 3-4 CHECKPOINT QUIZ
# ============================================================================

print()
print("=" * 60)
print("FINAL QUIZ: Answer from memory")
print("=" * 60)
print()
print("  LOGGING:")
print("  1. What does level=WARNING filter? (above or below?)")
print("  2. Name the 5 levels in order.")
print("  3. What's the difference between logger level and handler level?")
print("  4. logging.exception() vs logger.error(exc_info=True)?")
print()
print("  TRY/EXCEPT:")
print("  5. When does else run?")
print("  6. Does finally run if except raises?")
print("  7. What does 'raise from' do?")
print("  8. EAFP vs LBYL — which is Pythonic?")
print()
print("  ITERTOOLS:")
print("  9. groupby on unsorted data — what happens?")
print("  10. takewhile vs dropwhile — which yields the prefix?")
print("  11. product([1,2], [3,4]) — how many results?")
print("  12. Generator expression: sum exhausts it. Second sum returns?")
print()

embed(header="Final quiz — verify answers in REPL")

print()
print("=" * 60)
print("WEEKS 3-4 COMPLETE")
print("=" * 60)
print()
print("You now own:")
print("  logging:    levels, handlers, formatters, dictConfig")
print("  exceptions: try/except/else/finally, custom, context managers")
print("  itertools:  chain, islice, groupby, product, accumulate")
print("  generators: yield, yield from, expressions, pipelines")
print()
print("Combined with Weeks 1-2 (collections + subprocess),")
print("you have the full SRE scripting toolkit.")
print()
print("When ready: summon Guido for the Week 4 checkpoint exam.")
print("Domains 1-4 and 8-9 will be re-tested. The BDFL expects improvement.")
