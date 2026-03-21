# Analysis: Google Calendar + Drive Integration for NanoClaw

**Date:** 2026-03-21
**Status:** Recommendation ready
**Scope estimate:** ~20 agent-minutes implementation + ~15 human-minutes credential setup and review

---

## 1. Context

NanoClaw needs read/write access to Google Calendar (events CRUD) and Google Drive (list, search, read files). The system already integrates with Gmail via an MCP server (`@gongrzhe/server-gmail-autoauth-mcp`) running inside agent containers. This precedent is important: the integration pattern is established and working.

**Existing architecture constraints:**

- Agent containers run Claude SDK with MCP servers injected via `mcpServers` config in `container/agent-runner/src/index.ts`
- Gmail MCP credentials live at `~/.gmail-mcp/` on the host, bind-mounted into containers at `/home/node/.gmail-mcp/` (writable, for token refresh)
- Containers never see raw API keys — the credential proxy handles Anthropic auth, but Google OAuth tokens are mounted directly
- The `allowedTools` array in the agent-runner gates which MCP tools the SDK can invoke

**What prompted this:** Natural extension of HAL's capabilities. Calendar awareness enables scheduling, event reminders, availability checks. Drive access enables document search and retrieval without browser automation.

## 2. Options

### Option A: MCP Servers (Community or Official)

**What it looks like:** Add one or two MCP server entries to the `mcpServers` config in `agent-runner/src/index.ts`, exactly like Gmail. The servers run inside the container as child processes of the Claude SDK.

**Candidates evaluated:**

| Server | Language | Scope | Auth | Maturity |
|---|---|---|---|---|
| [`taylorwilsdon/google_workspace_mcp`](https://github.com/taylorwilsdon/google_workspace_mcp) | Python | Calendar + Drive + Docs + Sheets + Gmail + Forms + Tasks + Chat | OAuth 2.1, multi-user | High — most feature-complete, active development, PyPI package (`workspace-mcp`) |
| [`nspady/google-calendar-mcp`](https://github.com/nspady/google-calendar-mcp) | Node.js | Calendar only | OAuth 2.0 | Moderate — calendar-focused, npm package (`@sudomcp/google-calendar-mcp`) |
| [`@modelcontextprotocol/server-gdrive`](https://github.com/mikegcoleman/google-drive-mcp) | Node.js | Drive only (read) | OAuth 2.0 | Official Anthropic reference, but read-only |
| [`piotr-agier/google-drive-mcp`](https://github.com/piotr-agier/google-drive-mcp) | Node.js | Drive + Docs + Sheets + Slides + Calendar | OAuth 2.0 | Moderate |

**Cost:** ~20 agent-minutes to wire up. One-time ~15 human-minutes for Google Cloud Console OAuth setup. Near-zero ongoing maintenance (upstream handles API changes).

**What it enables:** Immediate access from any agent container. Claude sees Calendar/Drive as native tools. Composable with existing Gmail MCP.

**What it prevents:** Nothing meaningful. MCP servers are swappable — you can replace one with another or with a custom implementation later.

### Option B: Direct Google API Client (googleapis npm or google-api-python-client)

**What it looks like:** Write a custom integration layer — either a Node.js module using `googleapis` npm package or a Python module using `google-api-python-client` in halos/.

**Cost:** ~60-90 agent-minutes to build a reasonable abstraction with error handling, token refresh, pagination. Plus the same OAuth setup as Option A. Ongoing maintenance when Google deprecates API versions.

**What it enables:** Full control over API surface. Custom business logic (e.g., "find my next free 30-minute slot" as a single call rather than multi-tool orchestration).

**What it prevents:** Quick iteration. Every Google API change requires your maintenance. The agent can already compose multi-step workflows from simple MCP tools — building composite operations in code is premature optimization.

### Option C: NanoClaw Skill (Node.js, in-process)

**What it looks like:** A new skill directory under `container/skills/` (like `agent-browser`), providing Bash-callable commands: `gcal list`, `gcal create`, `gdrive search`, etc.

**Cost:** Similar to Option B (~60-90 agent-minutes) plus the complexity of managing OAuth token state from within a Bash-invocable skill. Token refresh race conditions become your problem.

**What it enables:** Agents use it via Bash tool calls, which works but is less ergonomic than native MCP tool calls (no structured input/output, string parsing).

**What it prevents:** Clean integration. Skills are great for stateful tools (browser sessions), but stateless API calls are better served by MCP's structured tool interface.

### Option D: Halos Python Module (CLI tool)

**What it looks like:** A new `halos/gcal/` and `halos/gdrive/` module, installable via `uv sync`, with console_script entry points like `gcal` and `gdrive`.

**Cost:** ~45 agent-minutes. Python has good Google API client libraries. Would follow the halos pattern well.

**What it enables:** CLI access from cron jobs, briefings, and other halos tooling — not just from agent containers. Could feed calendar data into `hal-briefing`.

**What it prevents:** Direct agent integration without also adding the CLI as an MCP server or Bash tool. Two integration surfaces to maintain.

## 3. Tradeoffs

| Dimension | A: MCP Server | B: Direct API | C: Skill | D: Halos Module |
|---|---|---|---|---|
| **Setup time** | ~20 min | ~60-90 min | ~60-90 min | ~45 min |
| **Agent accessibility** | Native (MCP tools) | Requires wrapper | Via Bash | Via Bash |
| **Maintenance** | Low (upstream) | High (yours) | High (yours) | Medium (yours) |
| **Token management** | Handled by server | You build it | You build it | You build it |
| **Halos/cron access** | Requires Bash shim | Direct if Python | Direct | Native |
| **Replaceability** | Swap one line | Rewrite | Rewrite | Rewrite |
| **Fits existing pattern** | Exact Gmail precedent | New pattern | Partial fit | Partial fit |
| **Structured I/O** | Yes (MCP protocol) | Yes (code) | No (string) | No (string) |

The Gmail integration already proved the MCP pattern works in this codebase. Introducing a different pattern for Calendar/Drive would be architectural inconsistency for no gain.

## 4. Recommendation

**Option A: MCP Server, specifically `taylorwilsdon/google_workspace_mcp`.**

Reasoning:

1. **Precedent match.** Gmail already runs as an MCP server in agent containers. Calendar and Drive should follow the identical pattern. The delta in `agent-runner/src/index.ts` is roughly 10 lines.

2. **Scope consolidation.** The `google_workspace_mcp` server covers Calendar, Drive, Docs, Sheets, and more — all under one OAuth consent, one token store, one server process. You don't need separate MCP servers for each Google service. It also covers Gmail, which means you could eventually consolidate the existing `@gongrzhe/server-gmail-autoauth-mcp` into this single server.

3. **OAuth 2.1 with multi-user support.** The server handles token refresh, consent, and scoping internally. Credentials mount the same way as Gmail: host directory bind-mounted into the container.

4. **Reversible.** If `google_workspace_mcp` proves flaky or unmaintained, swapping to individual MCP servers (`nspady/google-calendar-mcp` + `@modelcontextprotocol/server-gdrive`) is a config change, not a rewrite.

**Implementation sketch:**

```typescript
// In container/agent-runner/src/index.ts, mcpServers config:
google_workspace: {
  command: 'uvx',
  args: ['workspace-mcp'],
  env: {
    // Or wherever credentials land after OAuth setup
    GOOGLE_OAUTH_CREDENTIALS: '/home/node/.google-workspace-mcp/credentials.json',
    GOOGLE_OAUTH_TOKEN: '/home/node/.google-workspace-mcp/token.json',
  },
},
```

```typescript
// In container-runner.ts, add credential mount (like Gmail):
const googleWorkspaceDir = path.join(homeDir, '.google-workspace-mcp');
if (fs.existsSync(googleWorkspaceDir)) {
  mounts.push({
    hostPath: googleWorkspaceDir,
    containerPath: '/home/node/.google-workspace-mcp',
    readonly: false, // Token refresh needs write access
  });
}
```

```typescript
// In allowedTools array:
'mcp__google_workspace__*',
```

**Supplementary consideration:** If briefings (`hal-briefing`) need calendar data outside of agent containers, a thin halos wrapper (Option D) that calls the same Google API with shared credentials would be the right second step. But start with the MCP server — it covers the primary use case (agent interactions) with minimal effort.

## 5. Open Questions

1. **Google Cloud project setup.** Does a GCP project with Calendar and Drive API enabled already exist (from the Gmail integration), or does a new one need to be created? Reusing the same project and OAuth consent screen would simplify credential management.

2. **Scope overlap with Gmail MCP.** The `google_workspace_mcp` server includes Gmail. Worth evaluating whether to consolidate (one server for all Google services) or keep Gmail separate (proven, stable). Consolidation reduces token management but introduces a single point of failure.

3. **Container image size.** The `google_workspace_mcp` is Python-based (PyPI: `workspace-mcp`). The agent container currently has Node.js. Either `uvx` needs to be available in the container, or the server needs to be pre-installed in the container image. Check whether `uv`/`uvx` is already in the container.

4. **Token refresh in read-only scenarios.** Google OAuth tokens expire after 1 hour. The mount must be writable for token refresh. The Gmail mount already does this (`readonly: false`), so the pattern is proven, but verify that two separate servers refreshing the same token file don't race.

5. **Scoping.** What Google Drive scopes are needed? `drive.readonly` is safest for initial rollout. Calendar likely needs `calendar.events` (read/write). Start narrow, expand as needed.

---

**Sources:**
- [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) — Comprehensive Google Workspace MCP server
- [nspady/google-calendar-mcp](https://github.com/nspady/google-calendar-mcp) — Calendar-focused MCP server
- [nspady/google-calendar-mcp authentication guide](https://github.com/nspady/google-calendar-mcp/blob/main/docs/authentication.md) — OAuth setup documentation
- [Anthropic Google Drive MCP Server](https://www.pulsemcp.com/servers/modelcontextprotocol-gdrive) — Official reference implementation (read-only)
- [piotr-agier/google-drive-mcp](https://github.com/piotr-agier/google-drive-mcp) — Drive + Docs + Sheets + Calendar MCP
- [Google Cloud MCP announcement](https://cloud.google.com/blog/products/ai-machine-learning/announcing-official-mcp-support-for-google-services) — Official Google MCP support
- [Google Workspace MCP on PyPI](https://pypi.org/project/workspace-mcp/) — Python package for the recommended server
