#!/usr/bin/env python3
"""Day 3: logging — real SRE patterns.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-03-04/day03_logging_patterns.py
"""
from IPython import embed
import logging
import logging.handlers
import json
import sys
import os
import tempfile

def reset_logging():
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    logging.root.setLevel(logging.WARNING)

# ============================================================================
# PATTERN 1: JSON structured logging
# ============================================================================

reset_logging()

print("=" * 60)
print("CHECKPOINT 1: JSON structured logging")
print("=" * 60)
print()
print("In production, logs go to Elasticsearch/Loki/CloudWatch.")
print("These systems parse JSON, not free text.")
print()
print("TRY — build a JSON formatter:")
print()
print("  class JSONFormatter(logging.Formatter):")
print("      def format(self, record):")
print("          log_entry = {")
print("              'ts': self.formatTime(record),")
print("              'level': record.levelname,")
print("              'logger': record.name,")
print("              'message': record.getMessage(),")
print("          }")
print("          if record.exc_info and record.exc_info[0]:")
print("              log_entry['exception'] = self.formatException(record.exc_info)")
print("          return json.dumps(log_entry)")
print()
print("  logger = logging.getLogger('jsonlog')")
print("  logger.setLevel(logging.DEBUG)")
print("  logger.handlers.clear()")
print("  h = logging.StreamHandler(sys.stdout)")
print("  h.setFormatter(JSONFormatter())")
print("  logger.addHandler(h)")
print()
print("  logger.info('Pod %s started', 'musashi')")
print("  logger.error('Connection refused on port %d', 4222)")
print("  try:")
print("      1/0")
print("  except:")
print("      logger.exception('Division failed')")
print()

embed(header="Checkpoint 1: type out the JSON formatter")

# ============================================================================
# PATTERN 2: RotatingFileHandler
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 2: RotatingFileHandler — logs that don't fill disks")
print("=" * 60)
print()
print("In production, logs can grow to gigabytes. RotatingFileHandler")
print("rotates when the file hits a size limit.")
print()
print("TRY:")
print("  logdir = tempfile.mkdtemp(prefix='sre_logs_')")
print("  logfile = os.path.join(logdir, 'app.log')")
print()
print("  logger = logging.getLogger('rotating')")
print("  logger.setLevel(logging.DEBUG)")
print("  logger.handlers.clear()")
print()
print("  # maxBytes=500 means rotate after 500 bytes (tiny, for demo)")
print("  # backupCount=3 means keep 3 old files")
print("  rh = logging.handlers.RotatingFileHandler(")
print("      logfile, maxBytes=500, backupCount=3")
print("  )")
print("  rh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))")
print("  logger.addHandler(rh)")
print()
print("  # Write enough to trigger rotation")
print("  for i in range(50):")
print("      logger.info('Event %d: processing request from client', i)")
print()
print("  # Check what files exist:")
print("  for f in sorted(os.listdir(logdir)):")
print("      size = os.path.getsize(os.path.join(logdir, f))")
print("      print(f'  {f}: {size} bytes')")
print()
print("  # You should see: app.log, app.log.1, app.log.2, app.log.3")
print()

logdir = tempfile.mkdtemp(prefix='sre_logs_')
embed(header="Checkpoint 2: RotatingFileHandler — try it, inspect the files")

# ============================================================================
# PATTERN 3: Context with extra fields
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 3: Adding context to log messages")
print("=" * 60)
print()
print("SRE logs need context: request ID, pod name, user, etc.")
print("Three ways to add context:")
print()
print("TRY EACH:")
print()
print("  logger = logging.getLogger('context')")
print("  logger.setLevel(logging.DEBUG)")
print("  logger.handlers.clear()")
print("  h = logging.StreamHandler(sys.stdout)")
print("  h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))")
print("  logger.addHandler(h)")
print()
print("  # Way 1: just put it in the message (simple, works)")
print("  logger.info('[pod=medici] Restart count: %d', 5)")
print()
print("  # Way 2: LoggerAdapter (adds fields automatically)")
print("  adapter = logging.LoggerAdapter(logger, {'pod': 'medici'})")
print("  adapter.info('Restart count: %d', 5)")
print("  # Note: extra fields appear in the LogRecord but NOT in output")
print("  # unless the formatter references them")
print()
print("  # Way 3: extra dict (per-message)")
print("  logger.info('Restart count: %d', 5, extra={'pod': 'medici'})")
print()
print("Way 1 is the most common in practice. Way 2 is cleanest for")
print("per-module context. Way 3 is for structured/JSON logging.")
print()

embed(header="Checkpoint 3: context in log messages — three approaches")

# ============================================================================
# PATTERN 4: Filtering
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 4: Filters — fine-grained control")
print("=" * 60)
print()
print("Levels are coarse. Filters let you suppress specific loggers")
print("or messages based on custom logic.")
print()
print("TRY:")
print()
print("  class PodFilter(logging.Filter):")
print("      def __init__(self, pod_name):")
print("          self.pod_name = pod_name")
print("      def filter(self, record):")
print("          # Return True to KEEP the message, False to DROP it")
print("          return self.pod_name in record.getMessage()")
print()
print("  logger = logging.getLogger('filtered')")
print("  logger.setLevel(logging.DEBUG)")
print("  logger.handlers.clear()")
print("  h = logging.StreamHandler(sys.stdout)")
print("  h.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))")
print("  h.addFilter(PodFilter('medici'))  # only show medici messages")
print("  logger.addHandler(h)")
print()
print("  logger.info('Pod medici restarted')")
print("  logger.info('Pod musashi healthy')")
print("  logger.error('Pod medici OOMKilled')")
print("  logger.error('Pod gibson timeout')")
print("  # PREDICT: which lines appear?")
print()

embed(header="Checkpoint 4: custom Filter — only show medici logs")

# ============================================================================
# PATTERN 5: dictConfig (production setup)
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 5: dictConfig — the production way")
print("=" * 60)
print()
print("In production, logging is configured via a dict (or YAML/JSON file).")
print("This is cleaner than building handlers by hand.")
print()
print("TRY:")
print()
print("  import logging.config")
print()
print("  config = {")
print("      'version': 1,")
print("      'disable_existing_loggers': False,")
print("      'formatters': {")
print("          'simple': {'format': '%(levelname)-8s %(message)s'},")
print("          'detailed': {'format': '%(asctime)s %(levelname)-8s %(name)s: %(message)s'},")
print("      },")
print("      'handlers': {")
print("          'console': {")
print("              'class': 'logging.StreamHandler',")
print("              'level': 'WARNING',")
print("              'formatter': 'simple',")
print("              'stream': 'ext://sys.stdout',")
print("          },")
print("      },")
print("      'root': {")
print("          'level': 'DEBUG',")
print("          'handlers': ['console'],")
print("      },")
print("  }")
print()
print("  logging.config.dictConfig(config)")
print("  logger = logging.getLogger('production')")
print("  logger.info('will not show')")
print("  logger.warning('will show')")
print()

import logging.config
embed(header="Checkpoint 5: dictConfig — the production pattern")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 6: Build a complete SRE logging setup")
print("=" * 60)
print()
print("Build a setup_sre_logging() function that creates:")
print("  1. Console handler: WARNING+, short format (time + level + message)")
print("  2. File handler: DEBUG+, detailed format (time + level + name + func + message)")
print("  3. JSON file handler: ERROR+, JSON structured format")
print("  4. RotatingFileHandler for the regular file (maxBytes=10000, backupCount=5)")
print()
print("Then simulate 20 operations at mixed levels and verify:")
print("  - Console shows only warnings and errors")
print("  - Regular file shows everything")
print("  - JSON file shows only errors, in JSON format")
print()

embed(header="Checkpoint 6: capstone — full SRE logging setup")

print()
print("DAY 3 COMPLETE — LOGGING MODULE FINISHED.")
print()
print("You now own:")
print("  Level hierarchy: DEBUG < INFO < WARNING < ERROR < CRITICAL")
print("  Handlers: StreamHandler, FileHandler, RotatingFileHandler")
print("  Formatters: %(asctime)s, %(levelname)s, %(message)s, JSON")
print("  Filters: custom logic per handler")
print("  dictConfig: production configuration")
print()
print("Tomorrow: try/except/else/finally — the control flow you got wrong on Q40.")
