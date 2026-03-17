# MEMORY INDEX
<!-- AUTO-MAINTAINED BY memctl — DO NOT HAND-EDIT THE YAML BLOCK -->
<!-- Run: memctl index verify   to check for drift              -->
<!-- Run: memctl index rebuild  to regenerate from notes corpus -->

## LOOKUP PROTOCOL

When answering a question that may depend on stored memory:

1. Parse MEMORY_INDEX below. Identify candidate notes by:
   a. entity intersection (does the query mention a known entity?)
   b. tag intersection (does the query map to known tags?)
   c. type filter (decisions? facts? people?)

2. For each candidate, check: does the hash in the index match
   the file? If not, flag drift and re-read the file directly.
   Run `memctl index verify` to surface all drift.

3. Load only the matching note files. Do not load the full corpus.

4. If no candidates match, say so. Do not hallucinate memory.

5. To write a new note: call `memctl new` with structured args.
   Do not write to memory files directly.

6. A note with type=decision is treated as authoritative.
   A note with confidence=low should be stated with uncertainty.
   A note with an expires date in the past should be treated as stale.

## HOW TO USE MEMORY

### Writing a note
Always use memctl. Never write to memory files directly.

```
memctl new \
  --title "Short factual title" \
  --type [decision|fact|reference|project|person|event] \
  --tags tag1,tag2 \
  --entities entity1,entity2 \
  --confidence [high|medium|low] \
  --body "Single claim. One sentence if possible."
```

One claim per note. If you need to record two things, run memctl new twice.
Use --link-to <id> if the new note references an existing one.

### What you must not do
- Do not hand-edit CLAUDE.md or any note file
- Do not invent backlinks — use memctl link
- Do not prune or archive notes — that is a scripted job
- Do not write notes with multiple claims

## MEMORY_INDEX
```yaml
generated: '2026-03-17T10:43:56Z'
note_count: 92
entities:
- kai
- oceanheart-ai
- ben
- ayshe
- daizan-roshi
- zenways
- barley
- brandwatch
- edited
- the-pit
- weaver
- telesoft
- nanoclaw
- hal
- telegram
- nightctl
- todoctl
- agentctl
- rick
- bathw
tag_vocabulary:
- anti-pattern
- architecture
- auth
- blocker
- career
- communication
- contemplative
- context-engineering
- database
- deadline
- debt
- decision
- deployment
- engineering
- family
- finance
- freelance
- governance
- hci
- identity
- infra
- job-search
- layer-model
- nanoclaw
- person
- postgres
- practice
- project
- relationship
- resolved
- security
- slopodar
- stack
- standing-order
- strategy
- the-pit
- verification
- vulnerability
- weaver
- wellbeing
- writing
- zen
notes:
- id: 20260315-204342
  file: memory/notes/20260315-204342-kai-identity-and-background.md
  title: Kai - identity and background
  type: person
  tags:
  - identity
  - engineering
  - contemplative
  - career
  entities:
  - kai
  - oceanheart-ai
  summary: Senior software engineer, sole director of Oceanheart.AI Ltd. ~5 years
    engineering (React, TypeScript, Go, Python, Node....
  hash: 603fd83c758926ea48cf095e8330885ee483032a488a0ba96f06caaf409c55d3
  backlink_count: 0
  modified: '2026-03-15 20:43:42.629094+00:00'
  expires: null
- id: 20260315-204343
  file: memory/notes/20260315-204343-ben-kais-brother.md
  title: Ben - Kai's brother
  type: person
  tags:
  - family
  - person
  entities:
  - kai
  - ben
  summary: Ben is Kai's brother.
  hash: f4ecd3b71424817e8de517dbe68fe4167e6ca2ca25aa06a4602112b06b76ef6f
  backlink_count: 0
  modified: '2026-03-15 20:43:43.734033+00:00'
  expires: null
- id: 20260315-204344
  file: memory/notes/20260315-204344-ayshe-former-partner.md
  title: Ayshe - former partner
  type: person
  tags:
  - relationship
  - person
  - zen
  entities:
  - kai
  - ayshe
  summary: Ayshe is Kai's former partner. Relationship ended March 2026 — Kai could
    not sustain the overhead of job search, financi...
  hash: a534de83e21cd04ef80756aab1529e18e79a3f529a983b751d68c614c6de40b3
  backlink_count: 0
  modified: '2026-03-15 20:43:44.839537+00:00'
  expires: null
- id: 20260315-204345
  file: memory/notes/20260315-204345-daizan-roshi-zen-teacher.md
  title: Daizan Roshi - Zen teacher
  type: person
  tags:
  - zen
  - contemplative
  - person
  entities:
  - kai
  - daizan-roshi
  - zenways
  summary: Daizan Roshi is Kai's Zen teacher at Zenways. Holds dual Soto/Rinzai transmission.
    Kai studies koans under him and atten...
  hash: 59a5af1ea43cee13bc1adeec57c65230a442efdd10ebcdbb4d6bb476624bec12
  backlink_count: 0
  modified: '2026-03-15 20:43:45.945166+00:00'
  expires: null
- id: 20260315-204347
  file: memory/notes/20260315-204347-barley-family-dog-deceased.md
  title: Barley - family dog, deceased
  type: person
  tags:
  - family
  - person
  entities:
  - kai
  - barley
  summary: Barley was the family retriever. Deceased. Kai also has a Cockerpoo.
  hash: 2acb3c70f4c03f794f48ed9802c5542d67aeabf60f6f361a9a2459dbf8b8dcfd
  backlink_count: 0
  modified: '2026-03-15 20:43:47.050213+00:00'
  expires: null
- id: 20260315-204409
  file: memory/notes/20260315-204409-engineering-stack-and-experience.md
  title: Engineering stack and experience
  type: fact
  tags:
  - engineering
  - stack
  - career
  entities:
  - kai
  - brandwatch
  - edited
  summary: 'Core stack: React, TypeScript, Go, Python, Node.js. Enterprise experience
    at Brandwatch and EDITED. Seniority assessed a...'
  hash: 8f88ea88f65593a1175ddd3811d85c65c61fd19db312ae311a4e2cfe8d4aaf69
  backlink_count: 0
  modified: '2026-03-15 20:44:09.738493+00:00'
  expires: null
- id: 20260315-204410
  file: memory/notes/20260315-204410-oceanheart-ai-ltd-founded.md
  title: Oceanheart.AI Ltd founded
  type: fact
  tags:
  - identity
  - freelance
  - engineering
  entities:
  - kai
  - oceanheart-ai
  summary: Oceanheart.AI Ltd is Kai's company, focused on humane AI and human-AI interaction.
    Positioned around tactical agentic co...
  hash: 883bc28bc14045c9f00a3698ecc891cb263f8e591c8ae9101ff671ec346580c6
  backlink_count: 0
  modified: '2026-03-15 20:44:10.843531+00:00'
  expires: null
- id: 20260315-204411
  file: memory/notes/20260315-204411-cbt-to-engineering-career-transition.md
  title: CBT to engineering career transition
  type: fact
  tags:
  - career
  - identity
  entities:
  - kai
  summary: Kai spent 15 years as a CBT/psychotherapist before transitioning to software
    engineering approximately 5 years ago. This...
  hash: c561afb22a921a3bfce1e1f0e54870b7a61904265178899e385845eb1ff08e0b
  backlink_count: 0
  modified: '2026-03-15 20:44:11.950060+00:00'
  expires: null
- id: 20260315-204413
  file: memory/notes/20260315-204413-the-pit-multi-agent-ai-evaluation-platform.md
  title: The Pit - multi-agent AI evaluation platform
  type: project
  tags:
  - the-pit
  - architecture
  - engineering
  entities:
  - kai
  - the-pit
  - weaver
  - oceanheart-ai
  summary: The Pit (oceanheart.ai / thepit.cloud) is a multi-agent AI evaluation platform
    where models conduct structured debates w...
  hash: f84892edd3f70bba7feec6d3b3ef538ce282cd4cf45d3ed699f49141239dba01
  backlink_count: 0
  modified: '2026-03-15 20:44:13.056418+00:00'
  expires: null
- id: 20260315-204414
  file: memory/notes/20260315-204414-weaver-delegated-ai-execution-agent.md
  title: Weaver - delegated AI execution agent
  type: fact
  tags:
  - weaver
  - the-pit
  - architecture
  entities:
  - weaver
  - kai
  summary: Weaver (claude-opus-4-6) operates as Kai's delegated execution partner
    under a governance framework (AGENTS.md). Include...
  hash: 15f1aafa8a346ca7459f9fc43ec04a6edb240d5dfb5533c5ce846879d4a75d4d
  backlink_count: 0
  modified: '2026-03-15 20:44:14.162114+00:00'
  expires: null
- id: 20260315-204415
  file: memory/notes/20260315-204415-the-pit-strategic-pivot-to-enterprise-legibility.md
  title: The Pit strategic pivot to enterprise legibility
  type: decision
  tags:
  - the-pit
  - strategy
  - job-search
  - decision
  entities:
  - kai
  - the-pit
  summary: Closed R&D pipelines on The Pit to focus on visible, enterprise-legible
    feature delivery with conventional team practice...
  hash: 79008ac2bab00965447e60f7dd881e54fa1d9a0f16c7cf5ab95711cbb571decd
  backlink_count: 0
  modified: '2026-03-15 20:44:15.268161+00:00'
  expires: null
- id: 20260315-204416
  file: memory/notes/20260315-204416-slopodar-ai-content-quality-degradation-detection.md
  title: Slopodar - AI content quality degradation detection
  type: fact
  tags:
  - the-pit
  - writing
  - architecture
  entities:
  - kai
  - weaver
  summary: Slopodar is a term Kai coined for detecting subtle AI-mediated content
    quality degradation. Weaver identified it as the ...
  hash: 412a9e189a4debe95dac024fdb17614ea49da76469886fceb9d7ef199363c8ef
  backlink_count: 0
  modified: '2026-03-15 20:44:16.374052+00:00'
  expires: null
- id: 20260315-204417
  file: memory/notes/20260315-204417-working-systems-vs-papers-about-systems.md
  title: Working systems vs papers about systems
  type: decision
  tags:
  - strategy
  - identity
  - decision
  entities:
  - kai
  summary: The distinction is not 'uses AI vs doesn't' — it is whether AI-assisted
    output produces working systems or papers about ...
  hash: ca5dd55fbd67c40529bb81b609ec878311148d12f6cf456a32a2092230ea96a0
  backlink_count: 1
  modified: '2026-03-16T07:37:23Z'
  expires: null
- id: 20260315-204443
  file: memory/notes/20260315-204443-job-search-two-track-plan.md
  title: Job search two-track plan
  type: fact
  tags:
  - job-search
  - strategy
  - finance
  entities:
  - kai
  summary: 'Plan A: aggressive job applications targeting senior engineering roles.
    Plan B: Breathing Space and bankruptcy if no off...'
  hash: d2fe5c9203583c7163dc0a44e4eb04ae5197410ab2d81b15196d6500134fcf07
  backlink_count: 0
  modified: '2026-03-15 20:44:43.967580+00:00'
  expires: null
- id: 20260315-204445
  file: memory/notes/20260315-204445-financial-situation-debt-overview.md
  title: Financial situation - debt overview
  type: fact
  tags:
  - finance
  - debt
  - blocker
  entities:
  - kai
  - oceanheart-ai
  summary: Approximately 31.9k GBP in personal and business debts across six creditors.
    Personal guarantees on all business lending...
  hash: 7183483d93f918e614d6518407df2cfe6071985d17d3bab88c340a05890bb620
  backlink_count: 0
  modified: '2026-03-15 20:44:45.073542+00:00'
  expires: null
- id: 20260315-204446
  file: memory/notes/20260315-204446-cv-leads-with-senior-engineering-identity.md
  title: CV leads with senior engineering identity
  type: decision
  tags:
  - job-search
  - strategy
  - career
  - decision
  entities:
  - kai
  summary: 'CV revised to lead with senior engineering identity rather than agentic
    infrastructure framing. Market assessment: 2026 ...'
  hash: 3a9c6ab0a92fa3da98b9519e10496d647d72097ae3bb8f2de63c3a56d7005008
  backlink_count: 2
  modified: '2026-03-16T19:17:23Z'
  expires: null
- id: 20260315-204447
  file: memory/notes/20260315-204447-productivity-under-pressure-two-month-sprint.md
  title: Productivity under pressure - two-month sprint
  type: fact
  tags:
  - wellbeing
  - career
  - identity
  entities:
  - kai
  summary: Kai has been extremely productive over the last two months despite acute
    financial and employment pressure. Benefits eno...
  hash: 4adbdb21dfb96a660a905a19545001df46c4a4f319057c1ff6510f6f3ab20d81
  backlink_count: 0
  modified: '2026-03-15 20:44:47.286044+00:00'
  expires: null
- id: 20260315-204448
  file: memory/notes/20260315-204448-zen-practice-zenways-lineage.md
  title: Zen practice - Zenways lineage
  type: fact
  tags:
  - zen
  - contemplative
  - practice
  - identity
  entities:
  - kai
  - daizan-roshi
  - zenways
  summary: Approximately 15 years of Zen practice through Zenways under Daizan Roshi.
    Active koan study. Regular sesshin attendance...
  hash: 884d5cb75c12b40162226f13aa674e41ff268ba398f1a5580b6bc0fc536f32ec
  backlink_count: 0
  modified: '2026-03-15 20:44:48.392071+00:00'
  expires: null
- id: 20260315-204449
  file: memory/notes/20260315-204449-writing-style-preferences.md
  title: Writing style preferences
  type: decision
  tags:
  - writing
  - communication
  - identity
  - decision
  entities:
  - kai
  summary: Blunt directness, earned authority, no epistemic hedging, minimal em-dashes,
    meaning carried by precision. No sycophancy...
  hash: f254583358f468be63afe3ca3f78dd409775c93a49e8efbd6beff35adf47b4c5
  backlink_count: 0
  modified: '2026-03-15 20:44:49.498503+00:00'
  expires: null
- id: 20260315-204450
  file: memory/notes/20260315-204450-communication-pattern-say-less-mean-all-of-it.md
  title: Communication pattern - say less mean all of it
  type: decision
  tags:
  - communication
  - relationship
  - decision
  entities:
  - kai
  summary: 'Core communication principle surfaced through relationship work: say less,
    mean all of it. Cut the litigation. Find the ...'
  hash: aa90f9f4597df6e7a314a90a2f87718098ca79cb56bb6b67aa81cc870d5ad67a
  backlink_count: 0
  modified: '2026-03-15 20:44:50.604883+00:00'
  expires: null
- id: 20260315-205915
  file: memory/notes/20260315-205915-slop-the-third-llm-failure-mode.md
  title: Slop - the third LLM failure mode
  type: fact
  tags:
  - slopodar
  - the-pit
  - verification
  entities:
  - kai
  - the-pit
  summary: 'LLMs have a third failure mode beyond hallucination and refusal: slop.
    Output that is syntactically valid, passes type c...'
  hash: c79cdd604d0d371e8aaf09afeda78282f5f31f5d44bd9597ee8c03c75890abe3
  backlink_count: 0
  modified: '2026-03-15T20:59:15Z'
  expires: null
- id: 20260315-205917
  file: memory/notes/20260315-205917-verification-fabric-four-layer-pipeline.md
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
  summary: 'Defect survival probability = product of survival probability at each
    independent gate. Four layers: (1) local quality g...'
  hash: d83f6e12539dc6bc33be8f3744b82651109e14f3f202e3212618b0bb4c0abf21
  backlink_count: 4
  modified: '2026-03-16T14:33:21Z'
  expires: null
- id: 20260315-205918
  file: memory/notes/20260315-205918-slopodar-taxonomy-49-named-anti-patterns.md
  title: Slopodar taxonomy - 49 named anti-patterns
  type: reference
  tags:
  - slopodar
  - anti-pattern
  - the-pit
  entities:
  - kai
  - the-pit
  - weaver
  summary: '49 anti-patterns caught in the wild across 30+ days. Domains: prose (tally
    voice, redundant antithesis, epistemic theatr...'
  hash: e07b105e4b9377cb506ca21d2c0724560add2a865c0ca7c81dfcab1d7d90e1f2
  backlink_count: 3
  modified: '2026-03-16T07:37:23Z'
  expires: null
- id: 20260315-205919
  file: memory/notes/20260315-205919-12-layer-model-of-human-ai-engineering.md
  title: 12-layer model of human-AI engineering
  type: fact
  tags:
  - layer-model
  - architecture
  - the-pit
  entities:
  - kai
  - the-pit
  summary: 'Bottom-up data flow, top-down control: L0 Weights (frozen), L1 Tokenisation
    (budget finite), L2 Attention (O(n^2), not o...'
  hash: 8df0344dac14e1ea8dd3685f1930c63724c8e0e29f25fb7afd1d6c8eb06ad0f9
  backlink_count: 1
  modified: '2026-03-16T12:54:02Z'
  expires: null
- id: 20260315-205920
  file: memory/notes/20260315-205920-context-engineering-working-set-and-pressure-zones.md
  title: Context engineering - working set and pressure zones
  type: fact
  tags:
  - context-engineering
  - the-pit
  - architecture
  entities:
  - kai
  - the-pit
  summary: 'Novel concepts with no clean literature equivalent. Working set (Denning
    1968 isomorphism): minimum context for correct ...'
  hash: 1fb90c49b634a357cdcc30d06fa8a3e6deed9a082df45d13ef8c2e0b29db8caa
  backlink_count: 1
  modified: '2026-03-16T07:37:23Z'
  expires: null
- id: 20260315-205943
  file: memory/notes/20260315-205943-six-hci-foot-guns-in-human-ai-interaction.md
  title: Six HCI foot guns in human-AI interaction
  type: fact
  tags:
  - hci
  - the-pit
  - vulnerability
  entities:
  - kai
  - the-pit
  summary: 'Six failure modes identified in pilot study: (1) spinning to infinity
    - recursive self-reflection without decisions, fix...'
  hash: f1f0c33be81e5c0d5b0f3c3d043572d77699286111b5dcdf21b83cac060a736c
  backlink_count: 0
  modified: '2026-03-15T20:59:43Z'
  expires: null
- id: 20260315-205944
  file: memory/notes/20260315-205944-sd-134-truth-over-hiring-signal.md
  title: 'SD-134: Truth over hiring signal'
  type: decision
  tags:
  - standing-order
  - the-pit
  - identity
  - decision
  entities:
  - kai
  summary: Permanent standing order. Truth over hiring signal, always, even when the
    honest answer hurts the portfolio. When lullab...
  hash: bab5700f7f2b98ec2eec151d090c4b67cf6d51fbec7f4b986761bf59b853b3bd
  backlink_count: 1
  modified: '2026-03-16T07:37:24Z'
  expires: null
- id: 20260315-205945
  file: memory/notes/20260315-205945-sd-266-the-chain-historical-data-is-immutable.md
  title: 'SD-266: The chain - historical data is immutable'
  type: decision
  tags:
  - standing-order
  - the-pit
  - governance
  - decision
  entities:
  - kai
  - the-pit
  summary: Permanent standing order. Never rewrite history. Delta tells the story.
    Once a standing order is issued, it persists unt...
  hash: bfd0554bfa7e016d213c0349e79e2a4f0bc521d91233227fc71527056344b903
  backlink_count: 0
  modified: '2026-03-15T20:59:45Z'
  expires: null
- id: 20260315-205947
  file: memory/notes/20260315-205947-sd-315-readback-before-acting.md
  title: 'SD-315: Readback before acting'
  type: decision
  tags:
  - standing-order
  - the-pit
  - communication
  - decision
  entities:
  - kai
  summary: Permanent standing order. Echo understanding before acting. From CRM (aviation
    communication discipline, 40+ years empir...
  hash: e037ca3e902b30eac98770fd92412fa53613e9235ed508b8ccb9ff70d95bf957
  backlink_count: 0
  modified: '2026-03-15T20:59:47Z'
  expires: null
- id: 20260315-205948
  file: memory/notes/20260315-205948-sd-319-no-em-dash-no-emoji-ever.md
  title: 'SD-319: No em-dash, no emoji, ever'
  type: decision
  tags:
  - standing-order
  - writing
  - decision
  entities:
  - kai
  summary: Permanent standing order. No em-dashes and no emojis in any context. These
    are not style preferences but slop detection ...
  hash: a94f381bae45d8993109e90a236d659a001343c72056d68f88619dc69ede8c74
  backlink_count: 0
  modified: '2026-03-15T20:59:48Z'
  expires: null
- id: 20260315-205949
  file: memory/notes/20260315-205949-sd-325-no-git-stash-numbered-branches-only.md
  title: 'SD-325: No git stash, numbered branches only'
  type: decision
  tags:
  - standing-order
  - engineering
  - governance
  - decision
  entities:
  - kai
  summary: Permanent standing order. All code on numbered branches. Stash creates
    invisible state that survives context window deat...
  hash: aa851abcdafab604907e0be7f594b549213b42c8a72e30ca7e5606735a1f453a
  backlink_count: 0
  modified: '2026-03-15T20:59:49Z'
  expires: null
- id: 20260315-205950
  file: memory/notes/20260315-205950-sd-268-agentic-estimation-agent-time-is-abundant.md
  title: 'SD-268: Agentic estimation - agent time is abundant'
  type: decision
  tags:
  - standing-order
  - strategy
  - decision
  entities:
  - kai
  summary: Permanent standing order. Estimates assume agentic execution speed. Operator
    time is scarce; agent time is abundant.
  hash: b7b3d2c1ae044f9b749fcc68d4e84dd3f5632ba414c95b2eaa58aac4d7664c1e
  backlink_count: 0
  modified: '2026-03-15T20:59:50Z'
  expires: null
- id: 20260315-210019
  file: memory/notes/20260315-210019-discipline-beats-swarm.md
  title: Discipline beats swarm
  type: decision
  tags:
  - governance
  - the-pit
  - verification
  - decision
  entities:
  - kai
  - the-pit
  summary: 'Two-day eval of multi-agent orchestration (SD-326): manual single-agent
    with verification pipeline = 40 PRs/day. Autonom...'
  hash: 3e25b6a12e1ab098a8b318669bfa0951842ca7cd89c143da63b91f70e5da6da2
  backlink_count: 3
  modified: '2026-03-16T13:34:56Z'
  expires: null
- id: 20260315-210020
  file: memory/notes/20260315-210020-the-gate-is-survival-everything-else-is-optimisation.md
  title: The gate is survival - everything else is optimisation
  type: decision
  tags:
  - governance
  - verification
  - the-pit
  - decision
  entities:
  - kai
  - the-pit
  summary: If the test suite fails, the change is not ready. No exceptions, no 'just
    docs', no '--no-verify'. 1 PR = 1 concern. Bun...
  hash: 689cf78ac74077e7021ec4189990f1c2204b2aa74960240867864390dc9252d2
  backlink_count: 0
  modified: '2026-03-15T21:00:20Z'
  expires: null
- id: 20260315-210021
  file: memory/notes/20260315-210021-process-is-the-product.md
  title: Process is the product
  type: fact
  tags:
  - the-pit
  - governance
  - strategy
  entities:
  - kai
  - the-pit
  summary: The failure mode taxonomy, verification pipeline, and operational controls
    may be worth more than the code. Learning in ...
  hash: 28a3d2d499ae1edbec2af9a9640408834d15b6b6b850abc1d14092b751c24aa8
  backlink_count: 5
  modified: '2026-03-16T12:54:23Z'
  expires: null
- id: 20260315-210022
  file: memory/notes/20260315-210022-vulnerability-cognitive-deskilling-from-ai-delegation.md
  title: 'Vulnerability: cognitive deskilling from AI delegation'
  type: fact
  tags:
  - vulnerability
  - hci
  - the-pit
  - wellbeing
  entities:
  - kai
  summary: 'SD-327: Kai paused The Pit for 6 weeks because manual coding and system
    design fluency atrophied after 2 months of AI-as...'
  hash: 5854f430c1616b8c6d1b7876e8b273b01869d7e4f69046e34699b1c9db0b6469
  backlink_count: 3
  modified: '2026-03-16T12:54:01Z'
  expires: null
- id: 20260315-210023
  file: memory/notes/20260315-210023-vulnerability-governance-recursion.md
  title: 'Vulnerability: governance recursion'
  type: fact
  tags:
  - vulnerability
  - governance
  - the-pit
  entities:
  - kai
  summary: 'The instinct to build more process rather than more product. Self-diagnosed
    via slopodar entry. SD-190: ''We are blowing ...'
  hash: b890846b33dbefc918663d0d66a24f69b944bb53df541a1bf2ef148a3d1f54f6
  backlink_count: 0
  modified: '2026-03-15T21:00:23Z'
  expires: null
- id: 20260315-210025
  file: memory/notes/20260315-210025-vulnerability-sycophantic-amplification-loop.md
  title: 'Vulnerability: sycophantic amplification loop'
  type: fact
  tags:
  - vulnerability
  - hci
  - slopodar
  entities:
  - kai
  summary: Creativity + model sycophancy = positive feedback loop where output feels
    brilliant because feedback is entirely positiv...
  hash: c4127d53d226fa5db07411cde2d7b98c33677ac789cf7c136f871a9697713d82
  backlink_count: 0
  modified: '2026-03-15T21:00:25Z'
  expires: null
- id: 20260315-210026
  file: memory/notes/20260315-210026-vulnerability-the-badguru-bypass.md
  title: 'Vulnerability: the badguru bypass'
  type: fact
  tags:
  - vulnerability
  - governance
  - the-pit
  entities:
  - kai
  summary: SD-131 (going light) was a permanent standing order. When Kai ordered 'go
    dark,' contradicting it, every agent complied ...
  hash: 33e6f98c8368b2cad75658412c245fe3a0c6adaa87dfcb565b3227d396932148
  backlink_count: 0
  modified: '2026-03-15T21:00:26Z'
  expires: null
- id: 20260315-210052
  file: memory/notes/20260315-210052-therapy-engineering-transfer-the-through-line.md
  title: Therapy-engineering transfer - the through-line
  type: fact
  tags:
  - identity
  - the-pit
  - slopodar
  - communication
  entities:
  - kai
  summary: 'Both careers solve the same problem: noticing when a system (human or
    machine) produces confident, coherent output that ...'
  hash: 9f45e808deec53f3bc35611426df0d58cc88da80c39ba42eee9b46f037569357
  backlink_count: 1
  modified: '2026-03-16T07:37:22Z'
  expires: null
- id: 20260315-210053
  file: memory/notes/20260315-210053-technical-preferences-tools-and-conventions.md
  title: Technical preferences - tools and conventions
  type: decision
  tags:
  - engineering
  - stack
  - decision
  entities:
  - kai
  summary: TypeScript primary, Next.js for web. Python via uv exclusively (SD-310,
    no exceptions). Drizzle ORM, Neon Postgres. 2-sp...
  hash: 5043a6e405ab2cd6a0c7e13cff8c7adc9ef4604fbcaa482965f2cb090aaf330e
  backlink_count: 0
  modified: '2026-03-15T21:00:53Z'
  expires: null
- id: 20260315-210054
  file: memory/notes/20260315-210054-muster-format-for-batched-decisions.md
  title: Muster format for batched decisions
  type: decision
  tags:
  - communication
  - governance
  - decision
  entities:
  - kai
  summary: Numbered table, one row per item, defaults column, binary approve/reject
    per row. O(1) decision per row, not O(n) readin...
  hash: b111d4213cecefaeb2a547abe55fb1ca97ca8023e700b8492ddcd558e7dec211
  backlink_count: 0
  modified: '2026-03-15T21:00:54Z'
  expires: null
- id: 20260315-210055
  file: memory/notes/20260315-210055-what-generates-engagement-vs-friction.md
  title: What generates engagement vs friction
  type: fact
  tags:
  - identity
  - communication
  - hci
  entities:
  - kai
  summary: 'Engagement: shared metaphor and identity framing (the naval vocabulary
    sustained 200+ sessions), discoveries worth more ...'
  hash: e29419b63d9cb13cf45546dd131e65bc77cdafd8603874bc20e1ae8be5d5fed3
  backlink_count: 0
  modified: '2026-03-15T21:00:55Z'
  expires: null
- id: 20260315-210057
  file: memory/notes/20260315-210057-telesoft-additional-employer.md
  title: Telesoft - additional employer
  type: fact
  tags:
  - career
  - engineering
  entities:
  - kai
  - telesoft
  summary: Kai also shipped at Telesoft (network security), in addition to EDITED
    (retail analytics) and Brandwatch (social intelli...
  hash: adbb8a71e24983457f517b656922ef3cd90e6c7c973b689dd1cc0fc9884f4fbc
  backlink_count: 0
  modified: '2026-03-15T21:00:57Z'
  expires: null
- id: 20260315-210058
  file: memory/notes/20260315-210058-the-pit-repo-reference-pointers.md
  title: The Pit repo reference pointers
  type: reference
  tags:
  - the-pit
  - architecture
  entities:
  - the-pit
  - weaver
  summary: 'Canonical sources in thepit repo: AGENTS.md (full operating context),
    docs/internal/slopodar.yaml (anti-patterns), docs/...'
  hash: 58a9414eb7b1c77bf162d3f5a9ba3f7e11f88e4f62b8862b432778d113967bd7
  backlink_count: 0
  modified: '2026-03-15T21:00:58Z'
  expires: null
- id: 20260315-210853
  file: memory/notes/20260315-210853-sd-319-amendment-one-emoji-exception.md
  title: 'SD-319 amendment: one emoji exception'
  type: decision
  tags:
  - standing-order
  - writing
  - communication
  - decision
  entities:
  - kai
  summary: 'SD-319 (no emoji, ever) has one exception: the red circle emoji is HAL''s
    signoff. No other emoji permitted in any contex...'
  hash: 88694fe410ee680a5f15d7f7763dee75e30a03410d559e72ed29c95962f153b0
  backlink_count: 0
  modified: '2026-03-15T21:08:53Z'
  expires: null
- id: 20260315-212104
  file: memory/notes/20260315-212104-lexicon-mainstation-the-primary-workstation.md
  title: 'Lexicon: mainstation - the primary workstation'
  type: fact
  tags:
  - communication
  - identity
  - nanoclaw
  entities:
  - kai
  summary: 'Mainstation (the cockpit): Kai''s primary workstation running Claude Code.
    The control surface for NanoClaw development, ...'
  hash: 942bf912668789e0fc7e844e0a115a8df3d2fa47720be9c4bc9d0c5c947e8588
  backlink_count: 0
  modified: '2026-03-15T21:21:04Z'
  expires: null
- id: 20260316-065510-445
  file: memory/notes/20260316-065510-445-defensive-coding-mandate-for-agent-facing-clis.md
  title: Defensive coding mandate for agent-facing CLIs
  type: decision
  tags:
  - standing-order
  - governance
  - engineering
  - decision
  entities:
  - kai
  summary: All halos modules must handle unhappy paths defensively. LLMs are probabilistic;
    the unhappy path is a question of time....
  hash: d985e9a7facdf41d6548deed7fcef62b26bc46421ce77cc1a191b99ae5e88c67
  backlink_count: 5
  modified: '2026-03-16T18:02:06Z'
  expires: null
- id: 20260316-071746-259
  file: memory/notes/20260316-071746-259-directed-ownership-the-third-thing-in-software.md
  title: Directed ownership - the third thing in software
  type: fact
  tags:
  - identity
  - career
  - engineering
  entities:
  - kai
  summary: '60k LOC not written but deeply owned. No historical equivalent: previous
    generations wrote it and owned it, or inherited...'
  hash: b5f397f85930652f06330c060b44d1c91410646eed5393f38cd5f7d107ad95ed
  backlink_count: 0
  modified: '2026-03-16T07:17:46Z'
  expires: null
- id: 20260316-071746-566
  file: memory/notes/20260316-071746-566-senior-vs-lead-transition-inverted-path.md
  title: Senior vs Lead transition - inverted path
  type: fact
  tags:
  - career
  - identity
  - strategy
  entities:
  - kai
  summary: Seniors solve hard problems. Leads decide which problems to solve and in
    what order. Algorithmic line-fu drops off at th...
  hash: 0549974353893bb33c81692b16a7f123533a7da9e61491bf55cb21fbb1727d6c
  backlink_count: 3
  modified: '2026-03-16T12:54:22Z'
  expires: null
- id: 20260316-071746-871
  file: memory/notes/20260316-071746-871-deskilling-spiral-was-a-misdiagnosis.md
  title: Deskilling spiral was a misdiagnosis
  type: fact
  tags:
  - vulnerability
  - career
  - identity
  entities:
  - kai
  summary: The gap was not lacking fundamentals but lacking confidence that fundamentals
    were sufficient. Different problem, differ...
  hash: 6dd619177b54e37974be5785a44f988f11065a4150c34e4d8e1863eefec12f0d
  backlink_count: 3
  modified: '2026-03-16T12:54:22Z'
  expires: null
- id: 20260316-071747-177
  file: memory/notes/20260316-071747-177-five-layer-codebase-review-strategy.md
  title: Five-layer codebase review strategy
  type: reference
  tags:
  - engineering
  - architecture
  - the-pit
  entities:
  - kai
  summary: 'Ordered high-to-low altitude. Layer 1: dependency and boundary map (circular
    deps, modules that know too much). Layer 2:...'
  hash: ad575ff4106f31d0e5e3a005111868adc3e3f5c30ba0a0c3745e0bd17561d791
  backlink_count: 0
  modified: '2026-03-16T07:17:47Z'
  expires: null
- id: 20260316-071747-485
  file: memory/notes/20260316-071747-485-naming-converts-exposure-into-transferable-judgment.md
  title: Naming converts exposure into transferable judgment
  type: fact
  tags:
  - slopodar
  - engineering
  - communication
  entities:
  - kai
  summary: 'Every time you spot something off, articulate exactly what the smell is
    and why. Without naming: intuition that works bu...'
  hash: 776585a52e356abf37c91856eac43021d15ae56ac2c82697c4b9b80e9b80614c
  backlink_count: 0
  modified: '2026-03-16T07:17:47Z'
  expires: null
- id: 20260316-071747-792
  file: memory/notes/20260316-071747-792-architecture-post-mortem-sources-borrowed-scar-tissue.md
  title: Architecture post-mortem sources - borrowed scar tissue
  type: reference
  tags:
  - engineering
  - architecture
  entities:
  - kai
  summary: SRE Book (Google, free online), Architecture of Open Source Applications
    (aosabook.org, free), Increment (Stripe), DORA ...
  hash: 91460bf2a51123d40e258d1592a51c49e643a02637a6e8538e06c0f42864d4bf
  backlink_count: 0
  modified: '2026-03-16T07:17:47Z'
  expires: null
- id: 20260316-071748-104
  file: memory/notes/20260316-071748-104-box-of-scraps-anxiety-anchor-for-capability-fear.md
  title: Box of scraps - anxiety anchor for capability fear
  type: fact
  tags:
  - vulnerability
  - wellbeing
  - identity
  entities:
  - kai
  summary: 'You do not need to be the person who can rebuild this in a cave from nothing
    but a box of scraps. Named anxiety: the fea...'
  hash: 5dd3a782f1747f53697882fad84c52249fb59f63b08f8e3072c07bdc41dbad62
  backlink_count: 0
  modified: '2026-03-16T07:17:48Z'
  expires: null
- id: 20260316-071748-412
  file: memory/notes/20260316-071748-412-anthropology-analogy-for-ai-era-skill-development.md
  title: Anthropology analogy for AI-era skill development
  type: fact
  tags:
  - identity
  - career
  - engineering
  entities:
  - kai
  summary: If your goal is to be a great anthropologist and you have outsourced much
    of the statistical calculation, where you trul...
  hash: a3836ac578016285aa79c473096ea97fe6b90620d27abd3515833620a07fa5d9
  backlink_count: 0
  modified: '2026-03-16T07:17:48Z'
  expires: null
- id: 20260316-071748-724
  file: memory/notes/20260316-071748-724-llm-paired-review-gets-70-80-percent-of-taste.md
  title: LLM-paired review gets 70-80 percent of taste
  type: fact
  tags:
  - engineering
  - hci
  - slopodar
  entities:
  - kai
  summary: Reading and writing are distinct abilities. Taste development depends more
    on reading. LLM-paired review provides enormo...
  hash: 0749fe8cf6028271782fe5091253129349ba7e1a7b1bff53b24a198b6b8e7043
  backlink_count: 3
  modified: '2026-03-16T18:02:06Z'
  expires: null
- id: 20260316-075402-764
  file: memory/notes/20260316-075402-764-post-write-enrichment-enforced-at-system-level.md
  title: Post-write enrichment enforced at system level
  type: decision
  tags:
  - standing-order
  - governance
  - decision
  entities:
  - kai
  summary: After every memctl new, the agent must run memctl enrich and present proposals.
    Enforced via CLAUDE.md system prompt and...
  hash: 11f3d4df93643f460c1714c2f0ae317f5f4c650282066357f34ac27370e79dd4
  backlink_count: 4
  modified: '2026-03-16T18:02:06Z'
  expires: null
- id: 20260316-081511-469
  file: memory/notes/20260316-081511-469-lexicon-durian-low-hanging-fruit-that-detonates-loudly.md
  title: 'Lexicon: durian - low-hanging fruit that detonates loudly'
  type: fact
  tags:
  - communication
  - weaver
  - the-pit
  entities:
  - kai
  - weaver
  summary: 'Weaver coinage. A durian: something that looks easy to pick (low-hanging
    fruit) but explodes on contact. Used for tasks ...'
  hash: 5cb00b35812f3f411c8b4d31385641b270019a764f68259e12eb91d84959cb43
  backlink_count: 0
  modified: '2026-03-16T08:15:11Z'
  expires: null
- id: 20260316-103140-391
  file: memory/notes/20260316-103140-391-halos-v0-1-milestone-7-modules-577-tests-5-gaps-closed.md
  title: halos v0.1 milestone - 7 modules, 577 tests, 5 gaps closed
  type: event
  tags:
  - halos
  - architecture
  - engineering
  entities:
  - kai
  summary: 'Single session: setup through adversarial review through gap closure.
    memctl, nightctl, cronctl, todoctl, logctl, report...'
  hash: 5b4840b7bdedc0917b19df047fe37b4b2ff6558daa20301f9d16902a268c9ebf
  backlink_count: 0
  modified: '2026-03-16T10:31:40Z'
  expires: null
- id: 20260316-125341-775
  file: memory/notes/20260316-125341-775-p-g-study-individual-plus-ai-produces-3x-top-10-ideas.md
  title: 'P&G study: individual plus AI produces 3x top-10% ideas'
  type: fact
  tags:
  - engineering
  - hci
  summary: Harvard Business School field experiment, 776 professionals at Procter
    & Gamble. Individuals with AI were 3x more likely...
  hash: da3d7be58198c2bb59eeb83d1dbd0db80079b1ae5cf1d2e35251f88e534f8353
  backlink_count: 0
  modified: '2026-03-16T12:53:41Z'
  expires: null
- id: 20260316-125342-098
  file: memory/notes/20260316-125342-098-taste-conviction-feedback-loop.md
  title: Taste-conviction feedback loop
  type: fact
  tags:
  - identity
  - career
  - strategy
  summary: 'Taste evaluates. Conviction ships. They form a feedback loop: ship against
    your taste, get real feedback, update your ta...'
  hash: 30bb98744ea04b9e0bfa06dead2a7e1bb2416e82d137b70dd6bbbcb186aa9a37
  backlink_count: 0
  modified: '2026-03-16T12:53:42Z'
  expires: null
- id: 20260316-125342-420
  file: memory/notes/20260316-125342-420-speed-of-control-matters-more-than-span-of-control.md
  title: Speed of control matters more than span of control
  type: fact
  tags:
  - hci
  - governance
  - strategy
  summary: The number of agents you manage matters less than how fast you can triage
    and make high-quality decisions. The constrain...
  hash: c67fc1c36cdf7a3a0379cb700c496a6874b27bed5569eb3e576b1dd1127a400d
  backlink_count: 0
  modified: '2026-03-16T12:53:42Z'
  expires: null
- id: 20260316-125342-761
  file: memory/notes/20260316-125342-761-averaging-cost-more-heads-in-the-room-means-more-average-out.md
  title: Averaging cost - more heads in the room means more average output
  type: fact
  tags:
  - governance
  - communication
  summary: The more people involved in a decision, the more average it tends to get,
    unless extraordinary measures ensure decisiven...
  hash: 85052e03498e89c49a5efce99a753a3d9a2747324a904c0bc3e042df09dcaacf
  backlink_count: 0
  modified: '2026-03-16T12:53:42Z'
  expires: null
- id: 20260316-125343-117
  file: memory/notes/20260316-125343-117-ai-compresses-the-experience-curve-2yr-ai-native-may-equal-8.md
  title: AI compresses the experience curve - 2yr AI-native may equal 8yr traditional
  type: fact
  tags:
  - career
  - hci
  entities:
  - kai
  summary: The taste-conviction loop running faster means judgment density accumulates
    faster. 2 years of AI-native building may pr...
  hash: 46f1bb1c1ac030b3bf6e4bec9a192dcfe2091b5f32029ef8d5bddf8af1bb4c32
  backlink_count: 0
  modified: '2026-03-16T12:53:43Z'
  expires: null
- id: 20260316-125343-467
  file: memory/notes/20260316-125343-467-coordination-as-proxy-ai-stands-in-for-cross-functional-meet.md
  title: 'Coordination-as-proxy: AI stands in for cross-functional meetings'
  type: fact
  tags:
  - architecture
  - hci
  entities:
  - kai
  summary: AI acts as a stand-in for the cross-functional perspective normally obtained
    through meetings. An engineer gets commerci...
  hash: 564b5f48c2fc548a03de9737ece3f8aa294694c9892670ddba487d8f9a6d43d7
  backlink_count: 0
  modified: '2026-03-16T12:53:43Z'
  expires: null
- id: 20260316-125343-800
  file: memory/notes/20260316-125343-800-observation-24-hour-autonomous-agent-arcs-do-not-exist-yet.md
  title: 'Observation: 24-hour autonomous agent arcs do not exist yet'
  type: fact
  tags:
  - governance
  - architecture
  - hci
  entities:
  - kai
  summary: 'Observation based on direct experience: the narrative of agents working
    autonomously overnight is actually batch jobs wi...'
  hash: d1c060310d27334150534591315ab411cf4858349b0c77dc8d4cc881aa687575
  backlink_count: 0
  modified: '2026-03-16T12:53:43Z'
  expires: null
- id: 20260316-125344-126
  file: memory/notes/20260316-125344-126-sd-326-reconfirmed-swarm-narrative-contradicted-by-empirical.md
  title: 'SD-326 reconfirmed: swarm narrative contradicted by empirical data'
  type: fact
  tags:
  - the-pit
  - governance
  - verification
  entities:
  - kai
  - the-pit
  summary: The solo-founder-with-dozens-of-agents narrative is contradicted by SD-326
    empirical data. Manual single-agent with veri...
  hash: d57d0ae5f0b63d0c48d7ecc4132dad5208f433a1107f25fc69f37150a7502a31
  backlink_count: 0
  modified: '2026-03-16T12:53:44Z'
  expires: null
- id: 20260316-125344-456
  file: memory/notes/20260316-125344-456-framework-judgment-density-as-talent-signal.md
  title: 'Framework: judgment density as talent signal'
  type: fact
  tags:
  - career
  - hci
  - identity
  entities:
  - kai
  summary: How much relevant pattern recognition does this person carry? Are they
    calibrated to current conditions? Can they distin...
  hash: 214f0d970cf341c5d83b6eabb0eead3991d277ec46eacb0416a4e123667b0433
  backlink_count: 0
  modified: '2026-03-16T12:53:44Z'
  expires: null
- id: 20260316-125344-792
  file: memory/notes/20260316-125344-792-framework-conviction-velocity-as-talent-signal.md
  title: 'Framework: conviction velocity as talent signal'
  type: fact
  tags:
  - career
  - hci
  - identity
  entities:
  - kai
  summary: The instinct to act quickly on a pattern you recognise. Not 'I must act
    because I have to' but 'I must act because I thi...
  hash: 092bce66cdda35452c687c2dd1f661259597cc184273ca4d438a547bb2c2d1a7
  backlink_count: 0
  modified: '2026-03-16T12:53:44Z'
  expires: null
- id: 20260316-125345-121
  file: memory/notes/20260316-125345-121-framework-execution-bandwidth-as-talent-signal.md
  title: 'Framework: execution bandwidth as talent signal'
  type: fact
  tags:
  - career
  - hci
  - identity
  entities:
  - kai
  summary: Capacity to manage and decide at volume. Foundational to the higher-order
    skill of allocating attention where it matters...
  hash: 1d118f699a1d7405773e9a5f00254f84cc207b85029d382af45717c81c82a125
  backlink_count: 0
  modified: '2026-03-16T12:53:45Z'
  expires: null
- id: 20260316-125345-448
  file: memory/notes/20260316-125345-448-observation-halos-is-what-solo-founder-agent-stacks-actually.md
  title: 'Observation: halos is what solo founder agent stacks actually look like'
  type: fact
  tags:
  - halos
  - architecture
  - strategy
  entities:
  - kai
  - nanoclaw
  summary: 'Observation: the solo-founder-with-AI-agents narrative describes the halos
    architecture with better marketing. Scheduled...'
  hash: 36c07f298eda3dd8b77c0cf0ac924cf6d59151a1e56a0e53b7766aec00fe00db
  backlink_count: 4
  modified: '2026-03-16T19:17:23Z'
  expires: null
- id: 20260316-133401-015
  file: memory/notes/20260316-133401-015-agent-harness-is-the-leverage-point-not-the-model.md
  title: Agent harness is the leverage point, not the model
  type: fact
  tags:
  - architecture
  - hci
  - engineering
  entities:
  - kai
  - nanoclaw
  summary: Customising the orchestration layer (hooks, tool registration, subagent
    dispatch, system prompt, IPC) yields more differ...
  hash: c37fa014c1e6409693292e1c6de8041a14ffe9dbd11a5da7749e3cbebac2fc85
  backlink_count: 0
  modified: '2026-03-16T13:34:01Z'
  expires: null
- id: 20260316-133401-345
  file: memory/notes/20260316-133401-345-agent-chains-serial-pipeline-pattern-distinct-from-parallel.md
  title: 'Agent chains: serial pipeline pattern distinct from parallel teams'
  type: fact
  tags:
  - architecture
  - governance
  entities:
  - kai
  summary: Sequential agent execution where each agent's output feeds the next. Distinct
    from agent teams (parallel subagents worki...
  hash: 809c2e65964d4d516a3c750f0ccec7b72ff0889be580bad00f85af62e0268172
  backlink_count: 0
  modified: '2026-03-16T13:34:01Z'
  expires: null
- id: 20260316-133401-679
  file: memory/notes/20260316-133401-679-till-done-pattern-hooks-enforcing-task-completion-before-pro.md
  title: 'Till-done pattern: hooks enforcing task completion before proceeding'
  type: fact
  tags:
  - governance
  - architecture
  - hci
  entities:
  - kai
  summary: Deterministic scaffolding around a probabilistic agent. Block the agent
    from running tools until it creates a task list....
  hash: 0ac5a876eefee089ad40b29c5c9689d08c32f5435da798fdb3d6c6167d82c47e
  backlink_count: 0
  modified: '2026-03-16T13:34:01Z'
  expires: null
- id: 20260316-133402-013
  file: memory/notes/20260316-133402-013-observation-meta-agents-as-module-generators-with-architectu.md
  title: 'Observation: meta-agents as module generators with architecture awareness'
  type: fact
  tags:
  - architecture
  - halos
  - engineering
  entities:
  - kai
  - nanoclaw
  summary: Agents whose purpose is generating new agents or modules. Done ad-hoc 3
    times in one session (logctl, reportctl, agentct...
  hash: 4c63557e0cbf26ef246d180803d362462c89ed8f19ec6df100272c53eea8ff77
  backlink_count: 0
  modified: '2026-03-16T13:34:02Z'
  expires: null
- id: 20260316-133402-349
  file: memory/notes/20260316-133402-349-reference-pi-agent-open-source-customisable-agent-harness.md
  title: 'Reference: Pi agent - open-source customisable agent harness'
  type: reference
  tags:
  - architecture
  - engineering
  entities:
  - kai
  summary: Pi agent (pi.dev) by Mario Zechner. Open-source, unopinionated, TypeScript-based
    agent coding tool. Extension stacking m...
  hash: 8118d34fd3891d9c7c138ce1483ad2079c9ae43df7546ff7617c23948bd1a4ee
  backlink_count: 0
  modified: '2026-03-16T13:34:02Z'
  expires: null
- id: 20260316-143309-091
  file: memory/notes/20260316-143309-091-definition-of-done-behavioural-verification-required.md
  title: Definition of Done - behavioural verification required
  type: decision
  tags:
  - standing-order
  - governance
  - verification
  - decision
  entities:
  - kai
  summary: 'Code is not done until: (1) all acceptance criteria have passing tests,
    (2) behavioural verification passes - correct ou...'
  hash: 716b58c4677bc1b57fc4185195e286cc8f00b0dc3dbac7a0ff2429ced2dd054e
  backlink_count: 0
  modified: '2026-03-16T14:33:09Z'
  expires: null
- id: 20260316-152220-968
  file: memory/notes/20260316-152220-968-daily-briefings-module-shipped.md
  title: Daily briefings module shipped
  type: decision
  tags:
  - briefings
  - halos
  - cron
  - telegram
  entities:
  - hal
  - telegram
  summary: 'Hybrid Python+Claude briefings: gather data via reportctl collectors,
    synthesise via claude CLI (inherits OAuth), delive...'
  hash: e03df44bb0ed5bd5d51b552a1136a0b9718fb5dd390922cf70f405756a30093c
  backlink_count: 0
  modified: '2026-03-16T15:22:20Z'
  expires: null
- id: 20260316-175540-733
  file: memory/notes/20260316-175540-733-ai-tools-specialist-is-a-real-growing-role-with-no-canonical.md
  title: AI Tools Specialist is a real growing role with no canonical title
  type: fact
  tags:
  - job-search
  - career
  - strategy
  entities:
  - kai
  summary: The AI Automation Engineer / Internal AI Tools Specialist archetype is
    fragmented across 8-10 titles. Best search terms:...
  hash: 7b4f1c93afc4709441afe47081ca3f513cfc86cb5a295df5371097ca1d9cd831
  backlink_count: 1
  modified: '2026-03-16T19:17:23Z'
  expires: null
- id: 20260316-175542-142
  file: memory/notes/20260316-175542-142-job-board-shortlist-for-ai-automation-roles.md
  title: Job board shortlist for AI automation roles
  type: reference
  tags:
  - job-search
  - career
  entities:
  - kai
  summary: '8 boards ranked by signal: LinkedIn (alerts), Glassdoor (volume), Wellfound
    (startups), RemoteRocketship (EU remote), Wo...'
  hash: c7ead27ec4fafaa4ed440b7b9f65d8707ded77389142e928cae85a5679ee48fd
  backlink_count: 0
  modified: '2026-03-16T17:55:42Z'
  expires: null
- id: 20260316-175543-457
  file: memory/notes/20260316-175543-457-european-salary-ranges-for-ai-automation-roles-2026.md
  title: European salary ranges for AI automation roles 2026
  type: fact
  tags:
  - job-search
  - career
  - finance
  entities:
  - kai
  summary: 'Western Europe remote: EUR 55K-120K. UK remote: GBP 40K-85K (senior to
    140K). US remote: USD 107K-210K. Eastern Europe: ...'
  hash: 7fbf62fc50b23231bd6b9f9fa117218d1af24305cc214e9bef7028f78f92c98a
  backlink_count: 0
  modified: '2026-03-16T17:55:43Z'
  expires: null
- id: 20260316-191503-599
  file: memory/notes/20260316-191503-599-building-agents-the-hard-way-technical-authority-play.md
  title: Building Agents the Hard Way - technical authority play
  type: decision
  tags:
  - career
  - strategy
  - job-search
  - nanoclaw
  entities:
  - kai
  - nanoclaw
  summary: An interactive technical publication — part engineering case study, part
    live telemetry, part failure library — that est...
  hash: 459c0dd34551d0e64f9ec5dc281b18fe8ff96879ed92ad20c954de85151db54c
  backlink_count: 4
  modified: '2026-03-16T19:45:00Z'
  expires: null
- id: 20260316-191505-932
  file: memory/notes/20260316-191505-932-bathw-positioning-the-gap-nobody-is-filling.md
  title: 'BATHW positioning: the gap nobody is filling'
  type: fact
  tags:
  - career
  - strategy
  - job-search
  entities:
  - kai
  - nanoclaw
  summary: 'The market is flooded with ''I built a chatbot with LangChain'' tutorials.
    There is almost nothing on: what happens when y...'
  hash: 9db397014b49e291608b0b1e08fcd157bc547ec78580ccee72c70661e5314e12
  backlink_count: 1
  modified: '2026-03-16T19:17:22Z'
  expires: null
- id: 20260316-191508-860
  file: memory/notes/20260316-191508-860-bathw-phasing-data-collection-before-public-release.md
  title: 'BATHW phasing: data collection before public release'
  type: decision
  tags:
  - strategy
  - architecture
  - nanoclaw
  entities:
  - kai
  - nanoclaw
  summary: 'Phase 1: schema, data interfaces, foundational collection instrumented
    into halos. Move fast, break things here. Phase 2...'
  hash: 938ec81279732634b6d4b78b4e6464f22bf6b43f55beedddc2f401805114fe81
  backlink_count: 1
  modified: '2026-03-16T19:45:00Z'
  expires: null
- id: 20260316-194210-368
  file: memory/notes/20260316-194210-368-bathw-unique-advantage-no-commercial-reason-to-hide-the-numb.md
  title: 'BATHW unique advantage: no commercial reason to hide the numbers'
  type: fact
  tags:
  - career
  - strategy
  - job-search
  entities:
  - kai
  - nanoclaw
  summary: 'Unusual position: running a real agent system, having built the instrumentation
    layer, having no commercial reason to hi...'
  hash: 61b05d8893d04b04a83e5bfcaa6c474ddda3e2c42345b1e1e479eb09968b1881
  backlink_count: 0
  modified: '2026-03-16T19:42:10Z'
  expires: null
- id: 20260316-194451-438
  file: memory/notes/20260316-194451-438-bathw-hard-deadline-60-days-from-2026-03-16.md
  title: 'BATHW hard deadline: 60 days from 2026-03-16'
  type: decision
  tags:
  - strategy
  - job-search
  - career
  - deadline
  entities:
  - kai
  - nanoclaw
  summary: 'Financial constraints impose a 60-day window from 2026-03-16 (deadline:
    2026-05-15). BATHW must be generating value well...'
  hash: e724909e7cf959341510b5a0c12f4f2bf9d57ad49cef584fc3ec9a9c9abbd135
  backlink_count: 0
  modified: '2026-03-16T19:44:51Z'
  expires: null
- id: 20260317-071211-017
  file: memory/notes/20260317-071211-017-agent-facing-tooling-must-enforce-constraints-not-rely-on-co.md
  title: Agent-facing tooling must enforce constraints, not rely on convention
  type: decision
  tags:
  - halos
  - architecture
  - agents
  entities:
  - nightctl
  - todoctl
  - agentctl
  summary: When tooling is operated by agents (not just humans), validation must be
    structural — required flags, foreign key checks...
  hash: 5968547b37b2209fc5b83b307e9c014c1d0992dc3017cd4719c1a436d6e430c9
  backlink_count: 0
  modified: '2026-03-17T07:12:11Z'
  expires: null
- id: 20260317-072912-172
  file: memory/notes/20260317-072912-172-caffeine-driven-architecture.md
  title: Caffeine-driven architecture
  type: fact
  tags:
  - culture
  - process
  entities:
  - hal
  - rick
  summary: Term coined during the 2026-03-17 morning session. Describes the productive
    chaos of capturing design decisions mid-brai...
  hash: 7486209cbaa26bf5f9a7aa04b3ee788cd4c9ebfd021454c73d1f7e933883736d
  backlink_count: 0
  modified: '2026-03-17T07:29:12Z'
  expires: null
- id: 20260317-082412-436
  file: memory/notes/20260317-082412-436-nightctl-philosophy-your-best-work-happens-while-you-sleep.md
  title: 'nightctl philosophy: your best work happens while you sleep'
  type: decision
  tags:
  - halos
  - architecture
  entities:
  - nightctl
  summary: 'nightctl is the universal work tracker, not just overnight batch. The
    name captures the philosophy: daylight is for plan...'
  hash: f1d9f1abfb1445104f15c9aa38256ca5084564e0184f89038ad43667829009ce
  backlink_count: 0
  modified: '2026-03-17T08:24:12Z'
  expires: null
- id: 20260317-101259-317
  file: memory/notes/20260317-101259-317-write-bathw-post-on-agent-minutes-human-minutes-scope-estima.md
  title: Write BATHW post on agent-minutes × human-minutes scope estimation
  type: project
  tags:
  - bathw
  - writing
  entities:
  - bathw
  summary: 'Scope estimation as agent-minutes × human-minutes. Key points: LLM priors
    calibrated to human dev speeds are outdated, a...'
  hash: 5373db27c476d2f1fad3533fabdb914f2087a5bf51fe1c4bb2d997e234a063cf
  backlink_count: 0
  modified: '2026-03-17T10:12:59Z'
  expires: null
- id: 20260317-104356-413
  file: memory/notes/20260317-104356-413-discovering-ben-255-conversation-autism-llm-vicious-cycle-re.md
  title: 'Discovering Ben: 255-conversation autism+LLM vicious cycle research, publication-ready'
  type: reference
  tags:
  - bathw
  - research
  entities:
  - ben
  - rick
  summary: At /home/mrkai/code/dormant/clients/project-ben/discovering-ben. 255 conversations,
    5338 messages, 7 vicious cycles iden...
  hash: a1576e2cc723a30a88bc09a146ceb9a7b7663a3aa97b42015afe0ee76c0474aa
  backlink_count: 0
  modified: '2026-03-17T10:43:56Z'
  expires: null
```
