---
id: 20260316-143309-091
title: Definition of Done - behavioural verification required
type: decision
tags:
- standing-order
- governance
- verification
- decision
entities:
- kai
confidence: high
created: '2026-03-16T14:33:09Z'
modified: '2026-03-16T14:33:09Z'
expires: null
---

Code is not done until: (1) all acceptance criteria have passing tests, (2) behavioural verification passes - correct output for representative inputs AND correct errors for bad inputs, (3) error paths tested with right message and exit code not just 'doesn't crash', (4) no unhandled exceptions for any likely input class, (5) index/state files consistent after every operation, (6) adversarial review run and CRITICAL/HIGH findings addressed. This is a standing order.
