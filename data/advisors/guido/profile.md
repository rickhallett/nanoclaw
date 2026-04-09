# Guido — Kai Profile
Status: DISCOVERY PHASE

## Literacy Exam Results
(to be filled after first exam administration)

### Domain Heat Map
| Domain | Score | Key Gaps |
|--------|-------|----------|
| 1. Data Structures | FOREIGN | defaultdict, deque, Counter API, heapq |
| 2. Iteration & Functional | FRAGILE | itertools entirely, functools partially, generator sum |
| 3. Text & Patterns | FRAGILE | regex group numbering, f-string alignment, pattern precision |
| 4. OS & Process | FRAGILE | subprocess completely unknown, pathlib dot/resolve |
| 5. Concurrency | FRAGILE | threading mechanics, gather order |
| 6. Serialisation | FUNCTIONAL | json datetime — strongest domain |
| 7. Networking | FUNCTIONAL | urlencode +/% distinction |
| 8. Testing & Debugging | FRAGILE | logging levels backwards, mock OK |
| 9. Internals | FRAGILE | property OK, MRO/closures/slots/finally all gaps |
| 10. The Glue | FOREIGN | Enum comparison, datetime tz, hashlib, sys |
| Bonus: SRE Gauntlet | FRAGILE | hashability, integer interning, try/else/finally |

**Overall: FRAGILE. 8/40 correct (20%). Right instinct wrong output: 12/40 (30%).**

Scoring: FLUENT / FUNCTIONAL / FRAGILE / FOREIGN

## Current Python style observations
- Writes real systems (halos CLI tools, agentic pipelines) but relies on AI to produce stdlib patterns
- Intuition-to-knowledge ratio is high — guesses in the right direction more often than not
- Mental model is forming but untested against reality
- Has never formally studied the stdlib or internals

## Study plan (priority order, 30-min daily blocks)
1. **Week 1-2:** subprocess (run, check, capture_output, CalledProcessError) + collections (defaultdict, Counter, deque)
2. **Week 3-4:** logging (level hierarchy, handlers, formatters) + try/except/else/finally flow + itertools (chain, islice, groupby)
3. **Week 5-6:** pathlib details (dot convention, resolve, stem/suffix) + closures/late binding + datetime timezone (naive vs aware)
4. **Week 7-8:** concurrency (GIL, threading.Lock, gather order) + Enum semantics + hashability
5. **Week 9-10:** internals (MRO, __slots__, context managers, descriptor protocol) + testing (mock.patch, doctest)
6. **Week 11-12:** integration — re-take exam, build CLI tools using only stdlib

Each 30-min block: 10 min reading docs/examples, 15 min REPL experimentation in nvim, 5 min writing one small script that uses the concept.

## Curriculum materials produced

### Weeks 1-2: subprocess + collections (10 interactive scripts)
`data/advisors/guido/curriculum/scripts/day01-10*.py`
- Days 1-2: defaultdict (basics, patterns)
- Day 3: Counter
- Day 4: deque
- Day 5: collections integration
- Days 6-9: subprocess (basics, errors, patterns, deep)
- Day 10: capstone — full sysreport

### Weeks 3-4: logging + try/except/else/finally + itertools (10 interactive scripts)
`data/advisors/guido/curriculum/scripts-weeks-03-04/day01-10*.py`
- Days 1-3: logging (levels, handlers/formatters, SRE patterns)
- Days 4-5: try/except/else/finally (full flow, custom exceptions, context managers)
- Days 6-8: itertools (chain/islice/count/cycle, groupby/takewhile/dropwhile, product/combinations/starmap)
- Day 9: generators (yield, expressions, pipelines)
- Day 10: capstone — production log analyser

All scripts use IPython.embed() checkpoints for interactive REPL practice.

### Weeks 5-6: pathlib + closures + datetime + regex + f-strings (10 interactive scripts)
`data/advisors/guido/curriculum/scripts-weeks-05-06/day01-10*.py`
- Days 1-2: pathlib (suffix/stem/parent dot convention, glob, read/write, resolve)
- Days 3-4: closures (LEGB, late binding trap Q30, nonlocal, decorators, @wraps)
- Days 5-6: datetime (types, arithmetic, strftime/strptime, naive vs aware, UTC-everywhere)
- Days 7-8: regex (match/search/findall, groups Q10-11, lookahead, sub, SRE recipes)
- Day 9: f-strings (alignment Q12, numbers, debug =, tables)
- Day 10: capstone — config parser + log timestamp analyser

### drillctl — spaced repetition engine
`halos/drillctl/` — CLI tool with SM-2 scheduling.
- 39 cards covering all exam gaps from Weeks 1-6
- Card deck: `data/advisors/guido/curriculum/drills/deck-weeks-01-06.json`
- Interactive drill mode: `uv run drillctl run`
- Daily due check: `uv run drillctl today`
- Batch log from sessions: `uv run drillctl log dayNN --hit a,b --miss c,d`
- SM-2: fail→1d, pass→double interval (2→4→8→16→30+graduated)
- New decks added as curriculum progresses

## PROJECT RIPPERDOC context (2026-04-07)
- 6-month transformation window
- Python is glue for DevOps/infra/SRE — not the destination, the connective tissue
- Daily target: 30 min Python/SQL practice
- All study in nvim, no browser environments
- Identity: infrastructure engineer who writes Python like a native speaker
- Prediction: frontier AI too expensive for current patterns; engineers who can read and write without AI assistance win
- The exam is the first action. Everything else follows from what it reveals.

## Session log
- 2026-04-07: Seat created. Discovery phase.
- 2026-04-07: Literacy Exam v1 administered and graded. Overall: FRAGILE. 8/40 correct (20%). Strongest: Serialisation (FUNCTIONAL), Networking (FUNCTIONAL). Weakest: Data Structures (FOREIGN), The Glue (FOREIGN). Full graded exam: python-literacy-exam-v1-graded.md. Study plan constructed: 12-week programme, subprocess + collections first. Status upgraded from DISCOVERY to ACTIVE COACHING.
