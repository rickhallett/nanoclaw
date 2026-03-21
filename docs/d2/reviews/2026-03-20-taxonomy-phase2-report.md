---
title: "Taxonomy Review Phase 2"
category: review
status: active
created: 2026-03-20
---

# Taxonomy Review Phase 2

Date: 2026-03-20

Scope:
- `SEC.L2`
- `SEC.L3`
- `SEC.L4`
- `SEC.L5`
- `IPC.MSG.01`
- `IPC.TASK.01-04`
- `MCP.AUTH`

## Summary

Phase 2 produced 2 findings.

| Severity | Count |
|----------|-------|
| S1 | 0 |
| S2 | 1 |
| S3 | 1 |
| S4 | 0 |

Reviewed areas with no material findings in this pass:
- host-side IPC task/message authorization in `src/ipc.ts`
- mount allowlist path resolution and readonly enforcement in `src/mount-security.ts`
- container-side MCP task scoping as a defense-in-depth layer

## Findings

### SEC.L2.04 [TC05] S2

The credential proxy injects real credentials for any caller that can reach its listening socket; there is no container identity check beyond network reachability.

Evidence:
- request handling injects `x-api-key` or `authorization` solely based on proxy mode in `src/credential-proxy.ts:152-184`;
- the proxy bind host is chosen as `docker0` on Linux, with fallback to `0.0.0.0` if that interface is missing in `src/container-runtime.ts:18-40`.

Impact:
- any local process or other container that can reach that socket can use the proxy as a credential oracle;
- this turns the credential boundary into a network-placement boundary rather than an authenticated caller boundary.

Why `[TC05]`:
- the layer claims to enforce a secret boundary, but enforcement is not tied to the protected caller identity.

### SEC.L5.03 [TC05] S3

Sender-allowlist read/parse/schema failures all degrade to allow-all.

Evidence:
- missing files, unreadable files, invalid JSON, and invalid schema all return `DEFAULT_CONFIG`, which is `allow: "*"`, in `src/sender-allowlist.ts:17-21` and `src/sender-allowlist.ts:38-66`;
- the tests explicitly lock this behavior in at `src/sender-allowlist.test.ts:35`, `src/sender-allowlist.test.ts:82`, and `src/sender-allowlist.test.ts:89`.

Impact:
- a broken or partially written security config silently disables sender filtering;
- operational misconfiguration fails open rather than fail closed.

Why `[TC05]`:
- the enforcement boundary exists only while config parses correctly; on config failure the protection disappears.

## Coverage Notes

Observed coverage:
- `src/ipc-auth.test.ts` passed.
- `src/sender-allowlist.test.ts` passed.

Notable gaps:
- no test proves that only the intended NanoClaw containers can use the credential proxy;
- the proxy tests exercise header rewriting, not caller authentication.
