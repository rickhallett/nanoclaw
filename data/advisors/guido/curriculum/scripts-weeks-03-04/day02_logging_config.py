#!/usr/bin/env python3
"""Day 2: logging — handlers, formatters, multiple loggers.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-03-04/day02_logging_config.py
"""
from IPython import embed
import logging
import sys

def reset_logging():
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    logging.root.setLevel(logging.WARNING)

# ============================================================================
# LESSON: Handlers — where logs go
# ============================================================================

reset_logging()

print("=" * 60)
print("CHECKPOINT 1: StreamHandler — logging to console")
print("=" * 60)
print()
print("A Handler decides WHERE log messages go.")
print("StreamHandler sends to a stream (stdout, stderr, a file object).")
print()
print("TRY:")
print("  logger = logging.getLogger('app')")
print("  logger.setLevel(logging.DEBUG)  # logger accepts all levels")
print()
print("  # Handler to stdout")
print("  handler = logging.StreamHandler(sys.stdout)")
print("  handler.setLevel(logging.INFO)  # handler filters at INFO+")
print("  logger.addHandler(handler)")
print()
print("  logger.debug('debug msg')    — prints? (logger=DEBUG, handler=INFO)")
print("  logger.info('info msg')      — prints?")
print("  logger.error('error msg')    — prints?")
print()
print("KEY: BOTH the logger AND the handler have levels.")
print("The message must pass BOTH filters.")
print("Logger says 'I accept this.' Handler says 'I will show this.'")
print()

embed(header="Checkpoint 1: StreamHandler — logger level vs handler level")

# ============================================================================
# LESSON: Formatters — what logs look like
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 2: Formatters")
print("=" * 60)
print()
print("A Formatter controls the output format of each log line.")
print()
print("TRY:")
print("  logger = logging.getLogger('formatted')")
print("  logger.setLevel(logging.DEBUG)")
print("  logger.handlers.clear()  # remove any old handlers")
print()
print("  handler = logging.StreamHandler(sys.stdout)")
print()
print("  # Basic format")
print("  fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')")
print("  handler.setFormatter(fmt)")
print("  logger.addHandler(handler)")
print()
print("  logger.info('Pod started')")
print("  logger.error('Connection lost')")
print()
print("Common format fields:")
print("  %(asctime)s    — timestamp")
print("  %(levelname)s  — DEBUG/INFO/WARNING/ERROR/CRITICAL")
print("  %(name)s       — logger name")
print("  %(message)s    — the actual message")
print("  %(filename)s   — source file")
print("  %(lineno)d     — line number")
print("  %(funcName)s   — function name")
print()

embed(header="Checkpoint 2: Formatters — customise log output")

# ============================================================================
# LESSON: Multiple handlers
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 3: Multiple handlers — different destinations")
print("=" * 60)
print()
print("One logger can have multiple handlers. Each can have its own")
print("level and formatter. This is how you send INFO to stdout")
print("and ERROR to a file simultaneously.")
print()
print("TRY:")
print("  logger = logging.getLogger('multi')")
print("  logger.setLevel(logging.DEBUG)")
print("  logger.handlers.clear()")
print()
print("  # Handler 1: stdout, INFO+, simple format")
print("  h1 = logging.StreamHandler(sys.stdout)")
print("  h1.setLevel(logging.INFO)")
print("  h1.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))")
print("  logger.addHandler(h1)")
print()
print("  # Handler 2: stderr, ERROR+, detailed format")
print("  h2 = logging.StreamHandler(sys.stderr)")
print("  h2.setLevel(logging.ERROR)")
print("  h2.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))")
print("  logger.addHandler(h2)")
print()
print("  logger.info('Starting up')        — which handler(s)?")
print("  logger.warning('Memory high')     — which handler(s)?")
print("  logger.error('NATS down')         — which handler(s)?")
print()
print("PREDICT: error goes to BOTH handlers. info goes to h1 only.")
print()

embed(header="Checkpoint 3: multiple handlers with different levels")

# ============================================================================
# LESSON: FileHandler
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 4: FileHandler — logging to a file")
print("=" * 60)
print()
print("TRY:")
print("  import tempfile, os")
print("  logfile = os.path.join(tempfile.gettempdir(), 'sre_test.log')")
print()
print("  logger = logging.getLogger('filelog')")
print("  logger.setLevel(logging.DEBUG)")
print("  logger.handlers.clear()")
print()
print("  fh = logging.FileHandler(logfile)")
print("  fh.setLevel(logging.DEBUG)")
print("  fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))")
print("  logger.addHandler(fh)")
print()
print("  logger.info('Written to file')")
print("  logger.error('Also written to file')")
print()
print("  # Read it back:")
print("  with open(logfile) as f:")
print("      print(f.read())")
print()
print("  # Clean up:")
print("  os.unlink(logfile)")
print()

import tempfile, os
embed(header="Checkpoint 4: FileHandler — write and read back")

# ============================================================================
# PATTERN: The SRE logging setup
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 5: The SRE logging setup (copy this pattern)")
print("=" * 60)
print()
print("TYPE THIS OUT — this is the setup you'll use in every script:")
print()
print("  def setup_logging(level=logging.INFO, logfile=None):")
print("      logger = logging.getLogger('sre')")
print("      logger.setLevel(logging.DEBUG)  # accept all; let handlers filter")
print("      logger.handlers.clear()")
print()
print("      # Console handler")
print("      console = logging.StreamHandler(sys.stdout)")
print("      console.setLevel(level)")
print("      console.setFormatter(logging.Formatter(")
print("          '%(asctime)s %(levelname)-8s %(message)s',")
print("          datefmt='%H:%M:%S'")
print("      ))")
print("      logger.addHandler(console)")
print()
print("      # Optional file handler")
print("      if logfile:")
print("          fh = logging.FileHandler(logfile)")
print("          fh.setLevel(logging.DEBUG)  # file gets everything")
print("          fh.setFormatter(logging.Formatter(")
print("              '%(asctime)s %(levelname)-8s %(name)s %(funcName)s:%(lineno)d %(message)s'")
print("          ))")
print("          logger.addHandler(fh)")
print()
print("      return logger")
print()
print("  log = setup_logging(level=logging.DEBUG)")
print("  log.debug('debug test')")
print("  log.info('info test')")
print("  log.error('error test')")
print()

embed(header="Checkpoint 5: type out setup_logging — your reusable pattern")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

reset_logging()

print()
print("=" * 60)
print("CHECKPOINT 6: Build a dual-output logger")
print("=" * 60)
print()
print("Build a script that:")
print("  1. Creates a logger with TWO handlers:")
print("     - Console: shows WARNING+ with short format")
print("     - File (in /tmp): shows DEBUG+ with full format including timestamp")
print("  2. Runs 5 simulated operations, logging at different levels")
print("  3. At the end, reads the file and prints it")
print("  4. The console should show fewer lines than the file")
print()
print("Verify: console shows only warnings and errors.")
print("File shows everything including debug and info.")
print()

embed(header="Checkpoint 6: dual-output logger — console vs file")

print()
print("DAY 2 COMPLETE.")
print()
print("You now know:")
print("  Handler = where logs go (StreamHandler, FileHandler)")
print("  Formatter = what logs look like (%(asctime)s etc)")
print("  Logger level + Handler level = double filter")
print("  One logger, multiple handlers = different views of same events")
print()
print("Tomorrow: real SRE patterns — structured logging, rotation, filtering.")
