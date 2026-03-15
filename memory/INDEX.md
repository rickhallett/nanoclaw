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
generated: '2026-03-15T21:01:09Z'
note_count: 45
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
  hash: 52bf12294ea4e402f4a6ce45b12eb317f4bcfe62b232e94a9cd79ee44bc4b486
  backlink_count: 0
  modified: '2026-03-15 20:44:17.479416+00:00'
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
  hash: 447cebfcf046870045fb30bd771933afb917eba821dac06da9b9c6c24ce9de0a
  backlink_count: 0
  modified: '2026-03-15 20:44:46.179434+00:00'
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
  hash: 27b29b986f21a3f2fa8d4569a9050d07af119efb04b45661bf824d40b9e28425
  backlink_count: 0
  modified: '2026-03-15T20:59:17Z'
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
  hash: 15d4a0f02cf8dae33b763b54adf2d21780a679e999b7fda5454eead89fd33013
  backlink_count: 0
  modified: '2026-03-15T20:59:18Z'
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
  hash: 38079951d7156c80d16005cc24c3b871a3dff133be75aa63bb6cb7763a21e44d
  backlink_count: 0
  modified: '2026-03-15T20:59:19Z'
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
  hash: 4525fdd9e342af45cb4a8a5c3f553bf75f3af6fc614f8d4b0223ad73287f11b8
  backlink_count: 0
  modified: '2026-03-15T20:59:20Z'
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
  hash: f4f3d0f8f45d2fd3008232a3c045c4595925cf823d5b98677f3a9efacc53b037
  backlink_count: 0
  modified: '2026-03-15T20:59:44Z'
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
  hash: 9fdf87b1033c1c4737394b7623176bb3138d2214633b42dc64c968c1ef83bd26
  backlink_count: 0
  modified: '2026-03-15T21:00:19Z'
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
  hash: 48ae972be7667802106528732f0efc0152d8d72b9ec94ce608ef6ec9465445fc
  backlink_count: 0
  modified: '2026-03-15T21:00:21Z'
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
  hash: 4c4c941450d5ab0d7230a854747964d705aa36f11a1bb60f04aabfc581b77c24
  backlink_count: 0
  modified: '2026-03-15T21:00:22Z'
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
  hash: 3bc796659f4cad903c3575041872f5b37688e58da6712d254460a2c7ea66eadf
  backlink_count: 0
  modified: '2026-03-15T21:00:52Z'
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
```
