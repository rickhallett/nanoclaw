#!/usr/bin/env python3
"""Day 1: pathlib — Path objects, suffix/stem/parent, the dot convention.

You got Q13 and Q16 wrong. suffix includes the dot. stem strips only the last suffix.
Fix that today.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-05-06/day01_pathlib_fundamentals.py
"""
from IPython import embed
from pathlib import Path

# ============================================================================
# LESSON: Path objects
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: Creating Path objects")
print("=" * 60)
print()
print("pathlib.Path replaces os.path for everything. Cleaner, object-oriented.")
print()
print("TRY:")
print("  p = Path('/Users/kai/code/halo/data/notes/file.md')")
print("  print(type(p))")
print("  print(p)")
print()
print("  # From current directory")
print("  cwd = Path.cwd()")
print("  print(cwd)")
print()
print("  # Home directory")
print("  home = Path.home()")
print("  print(home)")
print()
print("  # Joining paths (use / operator — yes, really)")
print("  base = Path('/Users/kai')")
print("  full = base / 'code' / 'halo' / 'data'")
print("  print(full)")
print()
print("  # From string")
print("  s = '/tmp/logs/app.log'")
print("  p = Path(s)")
print("  print(p, type(p))")
print()

embed(header="Checkpoint 1: creating Paths — the / operator is key")

# ============================================================================
# LESSON: The anatomy of a path
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: Parts of a path (exam Q13 + Q16)")
print("=" * 60)
print()
print("THIS IS WHAT YOU GOT WRONG. Study each attribute carefully.")
print()
print("TRY with this path:")
print("  p = Path('/Users/kai/code/halo/data/notes/file.md')")
print()
print("  print(p.name)      — 'file.md'        (filename with extension)")
print("  print(p.stem)      — 'file'            (filename WITHOUT last extension)")
print("  print(p.suffix)    — '.md'             (last extension, WITH the dot)")
print("  print(p.suffixes)  — ['.md']           (list of ALL extensions)")
print("  print(p.parent)    — .../data/notes    (directory containing the file)")
print("  print(p.parent.name) — 'notes'         (just the directory name)")
print("  print(p.parts)     — tuple of all components")
print()
print("THE DOT CONVENTION: suffix ALWAYS includes the dot.")
print("  '.md' not 'md'")
print("  '.py' not 'py'")
print("  '.tar.gz' — suffix is '.gz', NOT '.tar.gz'")
print()

embed(header="Checkpoint 2: path anatomy — suffix HAS the dot")

# ============================================================================
# LESSON: The tar.gz trap (exam Q16)
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: The tar.gz trap")
print("=" * 60)
print()
print("This was exam Q16. You got all three wrong.")
print()
print("TRY:")
print("  p = Path('somefile.tar.gz')")
print()
print("  print(p.suffix)    — PREDICT first, then run")
print("  print(p.suffixes)  — PREDICT first, then run")
print("  print(p.stem)      — PREDICT first, then run")
print()
print("ANSWERS:")
print("  suffix   = '.gz'           (LAST extension only, with dot)")
print("  suffixes = ['.tar', '.gz'] (ALL extensions, each with dot)")
print("  stem     = 'somefile.tar'  (strips ONLY the last suffix)")
print()
print("Now try more:")
print("  p2 = Path('archive.backup.2026.tar.bz2')")
print("  print(p2.suffix)")
print("  print(p2.suffixes)")
print("  print(p2.stem)")
print()
print("  p3 = Path('Makefile')  # no extension")
print("  print(p3.suffix)   — ''")
print("  print(p3.suffixes) — []")
print("  print(p3.stem)     — 'Makefile'")
print()

embed(header="Checkpoint 3: tar.gz — suffix is .gz, stem is somefile.tar")

# ============================================================================
# LESSON: parent chain
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: Navigating with parent and parents")
print("=" * 60)
print()
print("TRY:")
print("  p = Path('/Users/kai/code/halo/data/notes/file.md')")
print()
print("  print(p.parent)          — .../data/notes")
print("  print(p.parent.parent)   — .../data")
print("  print(p.parent.parent.parent)  — .../halo")
print()
print("  # .parents is a sequence of all ancestors:")
print("  for i, ancestor in enumerate(p.parents):")
print("      print(f'  [{i}] {ancestor}')")
print()
print("  # Useful: find a specific ancestor")
print("  # 'Is this file inside a code directory?'")
print("  print('code' in p.parts)  — True")
print()
print("  # The root")
print("  print(p.root)    — '/'")
print("  print(p.anchor)  — '/' (root + drive on Windows)")
print()
print("  # Relative path has no root")
print("  r = Path('data/notes/file.md')")
print("  print(r.root)       — ''")
print("  print(r.is_absolute())  — False")
print("  print(p.is_absolute())  — True")
print()

embed(header="Checkpoint 4: parent chain and ancestry")

# ============================================================================
# LESSON: resolve (exam Q13)
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: resolve — the normaliser")
print("=" * 60)
print()
print("resolve() does TWO things:")
print("  1. Makes the path absolute (prepends cwd if relative)")
print("  2. Resolves .. and symlinks")
print()
print("TRY:")
print("  # Relative path → absolute")
print("  r = Path('data/notes')")
print("  print(r.resolve())")
print()
print("  # Resolving ..")
print("  p = Path('/Users/kai/code/halo/data/../data/notes/file.md')")
print("  print(p)             — still has ..")
print("  print(p.resolve())   — .. is gone")
print()
print("  # EXAM Q13 revisited:")
print("  p = Path('/Users/kai/code/halo/data/../data/notes/file.md')")
print("  resolved = p.resolve()")
print("  print(resolved)                 — /Users/kai/code/halo/data/notes/file.md")
print("  print(resolved.parent.name)     — 'notes' (NOT 'halo')")
print()
print("  # On the exam you said 'halo'. The parent of file.md is notes/,")
print("  # not halo/. resolve() collapsed data/../data to just data.")
print()

embed(header="Checkpoint 5: resolve — normalise paths, collapse ..")

# ============================================================================
# LESSON: Checking path properties
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 6: Path queries")
print("=" * 60)
print()
print("TRY:")
print("  p = Path('/tmp')")
print("  print(p.exists())       — True")
print("  print(p.is_dir())       — True")
print("  print(p.is_file())      — False")
print()
print("  p2 = Path('/etc/hosts')")
print("  print(p2.exists())      — True")
print("  print(p2.is_file())     — True")
print("  print(p2.is_dir())      — False")
print()
print("  p3 = Path('/nonexistent')")
print("  print(p3.exists())      — False")
print("  print(p3.is_file())     — False (not FileNotFoundError!)")
print()
print("  # Useful: stat for size and timestamps")
print("  if p2.exists():")
print("      stat = p2.stat()")
print("      print(f'size: {stat.st_size} bytes')")
print("      import datetime")
print("      mtime = datetime.datetime.fromtimestamp(stat.st_mtime)")
print("      print(f'modified: {mtime}')")
print()

embed(header="Checkpoint 6: exists, is_file, is_dir, stat")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 7: Path anatomy drill")
print("=" * 60)
print()
print("For EACH path below, predict ALL SIX attributes")
print("BEFORE running them. Write your predictions first.")
print()
print("  paths = [")
print("      Path('/var/log/syslog'),")
print("      Path('deploy.yaml'),")
print("      Path('/data/backups/etcd-2026-04-08.tar.gz'),")
print("      Path('.env'),")
print("      Path('/home/kai/.config/nvim/init.lua'),")
print("      Path('Dockerfile'),")
print("  ]")
print()
print("  for p in paths:")
print("      print(f'  path:     {p}')")
print("      print(f'  name:     {p.name}')")
print("      print(f'  stem:     {p.stem}')")
print("      print(f'  suffix:   {p.suffix!r}')   # repr to show the dot")
print("      print(f'  suffixes: {p.suffixes}')")
print("      print(f'  parent:   {p.parent}')")
print("      print()")
print()

paths = [
    Path('/var/log/syslog'),
    Path('deploy.yaml'),
    Path('/data/backups/etcd-2026-04-08.tar.gz'),
    Path('.env'),
    Path('/home/kai/.config/nvim/init.lua'),
    Path('Dockerfile'),
]

embed(header="Checkpoint 7: predict ALL attributes for each path, then verify")

print()
print("DAY 1 COMPLETE.")
print()
print("BURN THIS IN:")
print("  suffix INCLUDES the dot: '.md' not 'md'")
print("  suffix is the LAST extension only: '.gz' not '.tar.gz'")
print("  stem strips ONLY the last suffix: 'file.tar' not 'file'")
print("  resolve() collapses .. and makes paths absolute")
print("  parent.name gives the directory name, not the grandparent")
print()
print("Tomorrow: glob, reading/writing, and real pathlib operations.")
