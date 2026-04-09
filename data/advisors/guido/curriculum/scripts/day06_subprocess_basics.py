#!/usr/bin/env python3
"""Day 6: subprocess.run — the basics.

Run: uv run python data/advisors/guido/curriculum/scripts/day06_subprocess_basics.py
"""
from IPython import embed
import subprocess

# ============================================================================
# LESSON: The one function you need
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: subprocess.run — simplest form")
print("=" * 60)
print()
print("subprocess.run() runs a command and waits for it to finish.")
print("It returns a CompletedProcess object.")
print()
print("TRY:")
print("  result = subprocess.run(['echo', 'hello from subprocess'])")
print("  print(result)")
print("  print(type(result))")
print("  print(result.returncode)")
print()
print("Notice: output went directly to your terminal.")
print("The result object has the returncode but NOT stdout/stderr.")
print("To capture output, you need capture_output=True.")
print()

embed(header="Checkpoint 1: basic subprocess.run")

# ============================================================================
# LESSON: Capturing output
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: capture_output + text")
print("=" * 60)
print()
print("The two flags you will use 90% of the time:")
print("  capture_output=True  — capture stdout and stderr")
print("  text=True            — decode bytes to str")
print()
print("TRY:")
print("  result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)")
print("  print(repr(result.stdout))    — note the \\n at the end")
print("  print(repr(result.stderr))    — empty string")
print("  print(result.returncode)      — 0 means success")
print()
print("Now try WITHOUT text=True:")
print("  result = subprocess.run(['echo', 'hello'], capture_output=True)")
print("  print(type(result.stdout))    — bytes, not str")
print("  print(result.stdout)          — b'hello\\n'")
print()
print("repr() shows escape characters. print() renders them.")
print("repr('hello\\n') → 'hello\\n'")
print("print('hello\\n') → hello")
print("                    (with actual newline)")
print()

embed(header="Checkpoint 2: capture_output and text — the holy duo")

# ============================================================================
# LESSON: Arguments are a list
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: Command as a list")
print("=" * 60)
print()
print("Each element in the list is ONE argument to the command.")
print()
print("TRY:")
print("  # Correct: each arg is separate")
print("  r = subprocess.run(['ls', '-la', '/tmp'], capture_output=True, text=True)")
print("  print(r.stdout[:200])")
print()
print("  # Also correct for echo (echo joins its args with spaces):")
print("  r = subprocess.run(['echo', 'hello', 'world'], capture_output=True, text=True)")
print("  print(repr(r.stdout))")
print()
print("  # Compare: one string arg vs two")
print("  r1 = subprocess.run(['echo', 'hello world'], capture_output=True, text=True)")
print("  r2 = subprocess.run(['echo', 'hello', 'world'], capture_output=True, text=True)")
print("  print(r1.stdout == r2.stdout)  — True or False? Why?")
print()

embed(header="Checkpoint 3: commands as lists")

# ============================================================================
# LESSON: stderr goes somewhere else
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: stdout vs stderr")
print("=" * 60)
print()
print("Commands write normal output to stdout and errors to stderr.")
print("With capture_output=True, they go to different attributes.")
print()
print("TRY:")
print("  # This command will fail — /nonexistent doesn't exist")
print("  r = subprocess.run(['ls', '/nonexistent'], capture_output=True, text=True)")
print("  print(f'stdout: {repr(r.stdout)}')")
print("  print(f'stderr: {repr(r.stderr)}')")
print("  print(f'returncode: {r.returncode}')")
print()
print("  # This command writes to BOTH stdout and stderr:")
print("  r = subprocess.run(")
print("      ['python3', '-c', 'import sys; print(\"out\"); print(\"err\", file=sys.stderr)'],")
print("      capture_output=True, text=True")
print("  )")
print("  print(f'stdout: {repr(r.stdout)}')")
print("  print(f'stderr: {repr(r.stderr)}')")
print()
print("KEY: stderr is where error messages go. stdout is data.")
print("Your SRE scripts must check BOTH.")
print()

embed(header="Checkpoint 4: stdout vs stderr")

# ============================================================================
# LESSON: The CompletedProcess object
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: CompletedProcess attributes")
print("=" * 60)
print()
print("Every run() returns a CompletedProcess. Know its attributes.")
print()
print("TRY:")
print("  r = subprocess.run(['uname', '-a'], capture_output=True, text=True)")
print("  print(r.args)          — the command as passed")
print("  print(r.returncode)    — exit code (0 = success)")
print("  print(r.stdout)        — captured stdout")
print("  print(r.stderr)        — captured stderr")
print()
print("  # returncode is just an int:")
print("  print(type(r.returncode))")
print("  print(r.returncode == 0)   — True if success")
print("  print(bool(r.returncode))  — 0 is falsy, non-zero is truthy")
print()
print("Idiom: if result.returncode: means 'if command FAILED'")
print("       if not result.returncode: means 'if command SUCCEEDED'")
print("  But explicit: if result.returncode == 0: is clearer for scripts.")
print()

embed(header="Checkpoint 5: CompletedProcess attributes")

# ============================================================================
# LESSON: check=True
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 6: check=True — fail loudly")
print("=" * 60)
print()
print("Without check=True, failures are SILENT. You must check returncode.")
print("With check=True, non-zero exit raises CalledProcessError.")
print()
print("TRY:")
print("  # Silent failure (dangerous in scripts):")
print("  r = subprocess.run(['false'], capture_output=True, text=True)")
print("  print(f'returncode: {r.returncode}')  — 1, but no exception")
print()
print("  # Loud failure (safe):")
print("  try:")
print("      subprocess.run(['false'], capture_output=True, text=True, check=True)")
print("  except subprocess.CalledProcessError as e:")
print("      print(f'caught! code={e.returncode}')")
print("      print(f'stdout={repr(e.stdout)}')")
print("      print(f'stderr={repr(e.stderr)}')")
print()
print("  # 'true' always returns 0, 'false' always returns 1")
print("  # These are real Unix commands. Used in shell scripting for testing.")
print()

embed(header="Checkpoint 6: check=True — CalledProcessError")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 7: Build a system info script")
print("=" * 60)
print()
print("Write a function that captures output from these commands:")
print("  ['uname', '-a']")
print("  ['whoami']")
print("  ['uptime']")
print("  ['df', '-h', '/']")
print()
print("Print a clean report like:")
print("  [system]  Darwin kai-mbp 24.0.0 ...")
print("  [user]    kai")
print("  [uptime]  up 3 days, ...")
print("  [disk]    ...")
print()
print("Use capture_output=True, text=True.")
print("Strip trailing newlines with .strip().")
print()

embed(header="Checkpoint 7: system info report")

print()
print("DAY 6 COMPLETE.")
print()
print("The holy trinity:")
print("  subprocess.run(cmd, capture_output=True, text=True)")
print("  subprocess.run(cmd, capture_output=True, text=True, check=True)")
print("  result.stdout, result.stderr, result.returncode")
print()
print("Tomorrow: error handling — the three failure modes.")
