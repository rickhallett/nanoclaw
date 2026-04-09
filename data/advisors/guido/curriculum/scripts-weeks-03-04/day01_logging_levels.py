#!/usr/bin/env python3
"""Day 1: logging — the level hierarchy.

You got this completely backwards on the exam. Fix that today.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-03-04/day01_logging_levels.py
"""
from IPython import embed
import logging

# ============================================================================
# LESSON: The five levels
# ============================================================================

print("=" * 60)
print("THE LOGGING HIERARCHY (memorise this)")
print("=" * 60)
print()
print("  DEBUG    = 10  ← most verbose, lowest priority")
print("  INFO     = 20")
print("  WARNING  = 30  ← default level")
print("  ERROR    = 40")
print("  CRITICAL = 50  ← least verbose, highest priority")
print()
print("When you set level=WARNING, you see WARNING and ABOVE.")
print("That means WARNING, ERROR, CRITICAL.")
print("You do NOT see DEBUG or INFO.")
print()
print("Think of it as a MINIMUM SEVERITY FILTER.")
print("'Show me everything at WARNING severity or worse.'")
print()

# Reset logging for clean state (important between exercises)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

print("=" * 60)
print("CHECKPOINT 1: Level filtering")
print("=" * 60)
print()
print("TRY:")
print("  logging.basicConfig(level=logging.WARNING, force=True)")
print("  logger = logging.getLogger('test1')")
print()
print("  logger.debug('debug msg')      — will this print?")
print("  logger.info('info msg')        — will this print?")
print("  logger.warning('warn msg')     — will this print?")
print("  logger.error('error msg')      — will this print?")
print("  logger.critical('critical msg') — will this print?")
print()
print("PREDICT which ones print BEFORE you run them.")
print("On the exam you said debug+info+warning print. That was backwards.")
print()

embed(header="Checkpoint 1: predict which messages appear at level=WARNING")

# ============================================================================
# EXERCISE: Different levels
# ============================================================================

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

print()
print("=" * 60)
print("CHECKPOINT 2: Changing the level")
print("=" * 60)
print()
print("TRY EACH (predict first):")
print()
print("  # Level DEBUG — see everything")
print("  logging.basicConfig(level=logging.DEBUG, force=True)")
print("  logger = logging.getLogger('test2')")
print("  logger.debug('debug')    — prints?")
print("  logger.info('info')      — prints?")
print("  logger.warning('warn')   — prints?")
print()
print("  # Level ERROR — only error and critical")
print("  logging.basicConfig(level=logging.ERROR, force=True)")
print("  logger2 = logging.getLogger('test3')")
print("  logger2.warning('warn')  — prints?")
print("  logger2.error('error')   — prints?")
print()
print("  # The numeric values")
print("  print(logging.DEBUG)      — 10")
print("  print(logging.INFO)       — 20")
print("  print(logging.WARNING)    — 30")
print("  print(logging.ERROR)      — 40")
print("  print(logging.CRITICAL)   — 50")
print()
print("  # You can use numbers directly:")
print("  logging.basicConfig(level=25, force=True)  — between INFO and WARNING")
print()

embed(header="Checkpoint 2: try different levels — predict each time")

# ============================================================================
# LESSON: The default format
# ============================================================================

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

print()
print("=" * 60)
print("CHECKPOINT 3: What the output looks like")
print("=" * 60)
print()
print("Default format: LEVEL:logger_name:message")
print()
print("TRY:")
print("  logging.basicConfig(level=logging.DEBUG, force=True)")
print("  logger = logging.getLogger('myapp')")
print("  logger.warning('disk full')")
print("  # Output: WARNING:myapp:disk full")
print()
print("  logger = logging.getLogger('myapp.db')")
print("  logger.error('connection lost')")
print("  # Output: ERROR:myapp.db:connection lost")
print()
print("  # The root logger has no name:")
print("  logging.warning('root message')")
print("  # Output: WARNING:root:root message")
print()
print("Logger names are hierarchical (like Python packages).")
print("'myapp.db' inherits settings from 'myapp' which inherits from root.")
print()

embed(header="Checkpoint 3: observe the default output format")

# ============================================================================
# EXERCISE: Logger hierarchy
# ============================================================================

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

print()
print("=" * 60)
print("CHECKPOINT 4: Logger hierarchy")
print("=" * 60)
print()
print("TRY:")
print("  logging.basicConfig(level=logging.DEBUG, force=True)")
print()
print("  # These are ALL different loggers:")
print("  root = logging.getLogger()        # root logger")
print("  app = logging.getLogger('app')    # child of root")
print("  db = logging.getLogger('app.db')  # child of app")
print()
print("  root.warning('from root')")
print("  app.warning('from app')")
print("  db.warning('from app.db')")
print()
print("  # getLogger with the same name returns the SAME object:")
print("  a = logging.getLogger('mylogger')")
print("  b = logging.getLogger('mylogger')")
print("  print(a is b)   — True or False?")
print()
print("  # This means you can get the same logger from anywhere in your code.")
print("  # No need to pass it around. Just call getLogger('myapp') again.")
print()

embed(header="Checkpoint 4: logger hierarchy and identity")

# ============================================================================
# EXERCISE: Logging with extra data
# ============================================================================

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

print()
print("=" * 60)
print("CHECKPOINT 5: String formatting in log messages")
print("=" * 60)
print()
print("TRY:")
print("  logging.basicConfig(level=logging.DEBUG, force=True)")
print("  logger = logging.getLogger('sre')")
print()
print("  # Use % style (logging's native format):")
print("  logger.info('Pod %s restarted %d times', 'medici', 5)")
print()
print("  # f-strings work but are LESS efficient:")
print("  name, count = 'medici', 5")
print("  logger.info(f'Pod {name} restarted {count} times')")
print()
print("  # Why % is better: if the message is filtered out (below level),")
print("  # the %-formatting is NEVER executed. f-strings are always evaluated.")
print("  # At scale (millions of log calls), this matters.")
print()
print("  # Exception logging — use exc_info=True or logger.exception():")
print("  try:")
print("      1 / 0")
print("  except ZeroDivisionError:")
print("      logger.error('Division failed', exc_info=True)")
print()
print("  # Or equivalently:")
print("  try:")
print("      1 / 0")
print("  except ZeroDivisionError:")
print("      logger.exception('Division failed')  # always logs at ERROR with traceback")
print()

embed(header="Checkpoint 5: log formatting and exception logging")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

print()
print("=" * 60)
print("CHECKPOINT 6: Build a levelled diagnostic function")
print("=" * 60)
print()
print("Write a function run_diagnostics() that:")
print("  1. Creates a logger named 'diagnostics'")
print("  2. Logs at DEBUG: 'Starting diagnostics'")
print("  3. Logs at INFO: 'Checking disk space'")
print("  4. Logs at WARNING: 'Disk usage at 85%'")
print("  5. Logs at ERROR: 'Failed to reach NATS'")
print("  6. Logs at CRITICAL: 'etcd leader lost'")
print()
print("Then call it three times with different basicConfig levels:")
print("  a) level=DEBUG    — how many messages?")
print("  b) level=WARNING  — how many messages?")
print("  c) level=ERROR    — how many messages?")
print()
print("Predict the count each time BEFORE running.")
print()

embed(header="Checkpoint 6: build and test run_diagnostics()")

print()
print("DAY 1 COMPLETE.")
print()
print("THE HIERARCHY (say it out loud):")
print("  DEBUG < INFO < WARNING < ERROR < CRITICAL")
print("  Setting level = minimum severity to show.")
print("  level=WARNING shows WARNING + ERROR + CRITICAL.")
print("  level=DEBUG shows everything.")
print()
print("You had this backwards. Now you don't. Tomorrow: handlers and formatters.")
