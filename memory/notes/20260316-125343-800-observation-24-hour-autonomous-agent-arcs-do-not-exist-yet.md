---
id: 20260316-125343-800
title: 'Observation: 24-hour autonomous agent arcs do not exist yet'
type: fact
tags:
- governance
- architecture
- hci
entities:
- kai
confidence: high
created: '2026-03-16T12:53:43Z'
modified: '2026-03-16T12:53:43Z'
expires: null
---

Observation based on direct experience: the narrative of agents working autonomously overnight is actually batch jobs with good prompts on scheduled triggers. Context window saturation (L3), compaction loss, and thread position anchoring (L9) make long autonomous arcs degrade monotonically. What people describe as 'dozens of agents overnight' decomposes to: scheduled short invocations, state written to files, human reviews output in morning. This is nightctl plus cronctl, not autonomy.
