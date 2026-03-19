# Adversarial Review: Behavioral Smoke Suite v3

Date: 2026-03-19

Scope: static adversarial review of the current behavioral smoke implementation in [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py) and CLI wiring in [cli.py](/home/mrkai/code/nanoclaw/halos/halctl/cli.py).

Method: assume the suite is trying to look correct while leaving broken behavior undetected. This review focuses only on residual adversarial gaps after the v2 fixes.

## Findings

1. `M2` still does not prove durable retrieval because it crosses sender identity but not necessarily chat-context identity. In [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L990) through [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L1066), the store and query use different senders, but both messages are injected into the same `chat_jid`. If the agent’s retrieval path can inspect recent shared-chat history, it can still answer from conversation context rather than durable memory. The query also includes the same marker, which makes the stored exchange easier to locate from chat history. Severity: high.

2. `O2` can still pass on state alone even if the documented strike sequence was not followed. In [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L1891) through [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L1924), the first success branch is `if state in deferred_states:`. That branch bypasses the later checks that strikes 1 and 2 both carried Likert prompts. So a system that defers too early, or mutates onboarding state incorrectly while not actually following the three-strike interaction contract, can still pass. Severity: high.

3. Blocking scenarios still only fail the suite at 0%, which is weaker than the likely intent for critical behaviors. In [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L151) through [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L177), blocking failures are defined only as blocking scenarios with `success_rate == 0.0`. `A2` and `O2` are marked blocking in [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L1524) and [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L1753), but neither has a nonzero `min_pass_rate`. That means a critical scenario can fail 50% of the time and the suite can still go green if the global threshold is met. Severity: medium.

4. `C1` still does not prove shell execution specifically; it proves access to current time. In [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L1292) through [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L1361), the suite asks for `date +%s` and accepts any plausible epoch inside a time window. That is better than `echo`, but it can still pass if the agent has another way to obtain current time or infer it closely enough. Severity: medium.

5. Cleanup is safer than earlier versions, but it still relies on broad end-of-suite cleanup in a live environment. In [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L1939) through [behavioral_smoke.py](/home/mrkai/code/nanoclaw/halos/halctl/behavioral_smoke.py#L2036), cleanup still runs mainly at suite end, and the group cleanup keeps a pattern-based fallback on `folder LIKE 'telegram_smoke-test-%'`. That is much better than the older name-based delete, but it still leaves mid-suite crash residue and some pattern-based deletion risk. Severity: low.

## Assumptions

- This review assumes the agent may use shared chat history, not just sender-specific history, when answering prompts in the same `chat_jid`.
- This review did not execute the suite, so it does not confirm whether the runtime actually scopes context by sender, chat, both, or something else.

## Cleared From v2

- Response correlation by `inputMsgIds` appears consistently wired through `_wait_for_response`.
- `T2` no longer treats IPC-only cancellation as success.
- `T1` now validates weekday as well as hour/type.
- `M2` now performs an actual retrieval query instead of only rechecking note creation.
- `O2` no longer uses the old `any()` shortcut for the first two strikes.
- Suite gating now supports blocking scenarios and per-scenario minimums.

## Assessment

The suite is substantially stronger than the v2-reviewed version. The remaining concerns are narrower and mostly about proving the exact capability claimed, rather than the earlier broad false-positive factories.

I would treat the current suite as credible diagnostic infrastructure, but not yet as a hard behavioral gate until:

- `M2` crosses a true conversation boundary, not just a sender boundary within one chat
- `O2` requires both interaction sequencing and terminal state, rather than allowing terminal state alone to pass
- critical scenarios get explicit nonzero `min_pass_rate` requirements
- `C1` is replaced with a command test that proves shell/tool invocation rather than time access
