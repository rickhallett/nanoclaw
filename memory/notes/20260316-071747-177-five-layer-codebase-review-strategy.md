---
id: 20260316-071747-177
title: Five-layer codebase review strategy
type: reference
tags:
- engineering
- architecture
- the-pit
entities:
- kai
confidence: high
created: '2026-03-16T07:17:47Z'
modified: '2026-03-16T07:17:47Z'
expires: null
---

Ordered high-to-low altitude. Layer 1: dependency and boundary map (circular deps, modules that know too much). Layer 2: API surface audit (internal details leaking into public interfaces). Layer 3: error path review (ignore happy path, trace failures, where AI code is weakest). Layer 4: state management audit (where state lives, what mutates it). Layer 5: change impact analysis (pick 3 real future requirements, trace what changes). Each is a repeatable pass.
