# Session Dump: Fleet Launch, Eval Harness, and Test Pilot 001
<!-- 2026-03-18T13:10:00Z -->

## Decisions Made
- [fleet] Accept personality variance as data, not bugs. Dad 5/8 vs Money 8/8. Review threshold: 4/8.
- [governance] Three-strike relent OVERRIDES Likert MUST-deliver. Explicit precedence language required — implicit priority doesn't work with LLMs.
- [governance] User-initiated resume is allowed after deferral. Ban on re-raising is about agent pushing, not user pulling.
- [governance] Anti-fold directive for Ben: do not validate vague claims. Ask for specificity.
- [governance] Anti-romanticise directive for Ben: do not reframe dysfunction as strategy.
- [governance] AI slop detection for Ben: flag pasted AI output, test claims against reality.
- [governance] Decompose big asks: break vague instructions into collaborative steps, don't guess.
- [fleet] Hardcode operator Telegram ID (tg:5967394003) in halctl create. Every instance goes through Rick first.
- [fleet] templates/ added to lock list in fleet-config.yaml. Welcome messages and personality blocks flow via halctl push.
- [fleet] store/ added to exclude list. Stale sessions from prime were being copied to new instances.
- [infra] CONTAINER_PROXY_PORT upstreamed to prime source. No more brittle post-copy source patching.
- [infra] Main group containers get write access to project root (AFK sysadmin mode).
- [infra] Fleet mount at /workspace/fleet/ gives prime read-only visibility into all microHAL deployments.
- [observability] logctl fleet --conversations pairs user messages (SQLite) with agent responses (pm2 logs). Reverse-matching for burst senders.
- [docs] Briefings are d1 (operational), not d2 (architectural). Completed plans archive to d3.
- [docs] README rewritten for fork reality. No longer describes upstream generic chatbot.

## Patterns Discovered
- [provisioning] Every manual post-provision step is a bug in the provisioning system. Six steps automated during this session.
- [testing] Assert on absence of error signals, not presence of specific keywords. LLM response space is infinite; error space is enumerable.
- [testing] Multi-turn eval needs pm2 restart between scenarios to flush in-memory session cache. DB-only cleanup is insufficient.
- [testing] pm2 log timestamps are HH:MM:SS.mmm (no date). SQLite timestamps are ISO. Cross-source comparison requires date inference.
- [testing] Container logs only capture initial spawn input. Piped messages (via IPC stdin) are invisible in container logs.
- [testing] Agent responses go to Telegram, not back to SQLite. Monitoring requires pm2 log parsing, not DB queries.
- [governance] LLMs resolve competing instructions by weight (position, emphasis, labelling). OVERRIDES must be explicit.
- [governance] RLHF trains models to defer to users. Anti-sycophancy directives must be specific and repeated — "don't fold", "don't romanticise", "ask for evidence".
- [ben] Burst messaging pattern: 5:1 user-to-agent message ratio. Forward-walking pairing exhausts agent responses early.
- [ben] "Drift into ambiguity" is a cognitive defence. LLMs reinforce it every time they agree with unfalsifiable claims.
- [ben] Pastes large blocks of AI output as his own messages. Agent must detect this by prose style and test claims against reality.
- [ben] Feedback loop is asynchronous and unpredictable. Absence of signal is not absence of activity.
- [push] halctl push + container kill + pm2 restart has race conditions. Container death mid-session leaves queue in dead state. Needs atomic lifecycle (night train).

## State of the World
- [fleet] 5 instances: ben (active, test-pilot-001), dad (clean, waiting), mum (clean, waiting), gains (test), money (test)
- [fleet] All instances pushed with latest governance including assessment protocol, three-strike rule, anti-slop directives
- [ben] Registered at tg:8660755707, waiver accepted, Likert in progress, Gmail connected
- [ben] 3 memory notes: AI rules, SARS folder overview, smoke test artifact
- [ben] Governance: proactive structuring, interrupt permission, anti-fold, anti-romanticise, AI slop detection, decompose big asks, filesystem boundaries
- [prime] Gmail channel connected. Write access to project root. Fleet mount at /workspace/fleet/
- [prime] HAL-prime CLAUDE.md has full identity, fleet table, operator context, responsibilities
- [eval] 8 scenarios: 5 single-injection, 3 dialogue (tangent-and-resume, deflect-then-resume, edit-response)
- [eval] Money: 8/8. Dad: 5/8. Mum: 1/1 (partial run). Baseline documented in docs/d1/eval-baseline-2026-03-18.md
- [logctl] fleet command works. --conversations pairing fixed with date-aware reverse-matching. trace command WIP.
- [docs] 10 mermaid diagrams. README rewritten. d1/d2/d3 reorganised. docs-audit.py repeatable.
- [git] 33 commits on main, all pushed to origin. Branch: main.

## Open Questions
- [logctl] Correlation ID for cross-source log joining. Needs UUID stamped at message ingestion in index.ts. **Owner:** night train
- [push] Atomic push lifecycle — kill container, clear state, restart as one operation. **Owner:** night train
- [ben] Will the anti-fold and anti-romanticise directives actually change agent behaviour? Need to monitor next session. **Owner:** Rick (observe)
- [ben] Gmail credentials are on host (~/.gmail-mcp/). Shared across all instances using same OAuth. Is per-instance OAuth needed? **Owner:** Rick
- [fleet] Dad and Mum need real users registered (their Telegram IDs). Currently only Rick's ID. **Owner:** Rick (when they start)
- [eval] Mum's full eval suite not yet run. **Owner:** next session
- [kill-switch] halctl freeze/fold/fry untested live. **Owner:** night train

## Contradictions / Extensions
- [templates/microhal/onboarding-instructions.md] Rewritten from agent-only to bot+agent split. Waiver is now bot-level, Likert is agent-level.
- [CLAUDE.md] Key Files section expanded with fleet, governance, data, and docs subsections.
- [docs/README.md] Complete rewrite. No longer describes upstream nanoclaw.
- [groups/telegram_main/CLAUDE.md] HAL-prime identity added. Container mounts table updated with write access and fleet mount.
- [docs/d2/SPEC.md] Original mermaid diagram still shows old architecture. Superseded by docs/d1/architecture-diagrams.md (10 diagrams).
- [halfleet/fleet-config.yaml] templates/ added to lock list. store/ added to exclude list.

## Bus Factor
- Ben is test-pilot-001. His Telegram ID is tg:8660755707. His instance is microhal-ben at ~/code/halfleet/microhal-ben/nanoclaw.
- The push lifecycle is fragile. Kill container → clear sessions → restart pm2 must happen in that order. If the container is mid-response when killed, the queue deadlocks. Manual fix: `docker kill` + `npx pm2 restart`.
- logctl fleet --conversations works but has pairing gaps for burst senders and cross-date messages. Manual monitoring via `tail -f ~/.pm2/logs/microhal-ben-out.log | grep "Agent output"` is more reliable right now.
- Ben's governance profile (templates/microhal/user/ben.md) is the most heavily customised. Five anti-slop directives added during live observation. These are untested against the eval harness — they were written reactively.
- The night train queue is at queue/items/20260318-120000-night-train.yaml. 9 items, prioritised. Top 3: correlation IDs, halctl notify, atomic push.
- Gmail is live on prime and Ben. Credentials at ~/.gmail-mcp/. OAuth project is 184931149104 (Ben's client secret) — Gmail API enabled today.
- 33 commits this session. All on main, all pushed.

## Follow-Up
- [ ] Ben's anti-slop directives should become eval scenarios (test AI output detection, fold resistance, romanticisation resistance)
- [ ] docs/d2/SPEC.md mermaid diagram is stale — point to d1/architecture-diagrams.md or update
- [ ] memctl note candidates: "burst messaging ratio as UX signal", "RLHF anti-patterns in personalised agents", "operator notification pattern via bot API"
- [ ] halctl notify should be a proper subcommand (currently a curl one-liner)
