# Weeks 5–6: pathlib + closures + datetime + regex + f-strings
## Interactive Python curriculum with IPython checkpoints

### How to run

```bash
cd /Users/mrkai/code/halo
uv run python data/advisors/guido/curriculum/scripts-weeks-05-06/day01_pathlib_fundamentals.py
```

### Schedule

| Day | File | Topic |
|-----|------|-------|
| 1 | `day01_pathlib_fundamentals.py` | Path objects, suffix/stem/parent, the dot convention |
| 2 | `day02_pathlib_operations.py` | glob, rglob, reading/writing, resolve, traversal |
| 3 | `day03_closures_scope.py` | LEGB rule, closures, the late binding trap (exam Q30) |
| 4 | `day04_decorators.py` | Decorators as closures, @wraps, parameterised decorators |
| 5 | `day05_datetime_basics.py` | datetime, date, time, timedelta arithmetic |
| 6 | `day06_datetime_timezone.py` | Naive vs aware, timezone, UTC, the production trap (exam Q33) |
| 7 | `day07_regex_fundamentals.py` | re.match/search/findall, groups, compile (exam Q10-11) |
| 8 | `day08_regex_patterns.py` | Lookahead, substitution, real SRE parsing patterns |
| 9 | `day09_fstrings_formatting.py` | Alignment, fill, number formatting, debug (exam Q12) |
| 10 | `day10_integration.py` | Capstone: config file parser + log timestamp analyser |

### Prerequisites

From Weeks 1-4 you should know:
- collections (defaultdict, Counter, deque)
- subprocess.run + error handling
- logging level hierarchy and handlers
- try/except/else/finally flow
- itertools (chain, islice, groupby) and generators
