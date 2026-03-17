---
name: critical-path
description: Reusable concept — identify the critical path before parallelising work; everything downstream depends on its interface
type: feedback
---

When planning multi-agent or multi-phase work, always identify the critical path first. The critical path is the component whose interface every downstream consumer depends on. Get it wrong and parallel work produces waste.

**Why:** During nightctl merge planning (2026-03-17), the Item model was identified as the critical path — CLI, plan validator, migration, and container-runner all depended on its interface. Parallelising before stabilising it would have created throwaway code.

**How to apply:** Before proposing parallel workstreams, ask: "what does everything else depend on?" Build that first, sequentially, with full attention. Only parallelise genuinely independent workstreams that touch different files.
