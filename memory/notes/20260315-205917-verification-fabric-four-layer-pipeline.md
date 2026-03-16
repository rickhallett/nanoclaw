---
id: 20260315-205917
title: Verification fabric - four-layer pipeline
type: decision
tags:
- verification
- the-pit
- governance
- decision
entities:
- kai
- the-pit
backlinks:
- 20260315-205915
- 20260316-071747-177
- 20260316-133401-345
- 20260316-143309-091
confidence: high
created: '2026-03-15T20:59:17Z'
modified: '2026-03-16T14:33:21Z'
expires: null
---

Defect survival probability = product of survival probability at each independent gate. Four layers: (1) local quality gate (typecheck+lint+test, primary authority, CI is backstop), (2) adversarial review (3 independent models, structured YAML, convergence builds confidence), (3) human walkthrough (catches 'not wrong', cannot be automated), (4) post-merge verification. Same-model agreement is consistency, not validation. True independent signal requires different model families.
