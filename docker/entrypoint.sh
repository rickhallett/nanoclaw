#!/bin/bash
# Halo container entrypoint — wraps upstream Hermes without modification.
# All Halo-specific logic (prompt loading, heartbeat, WAL mode) lives here
# or in halos modules, never in patched Hermes source.
set -e

HERMES_HOME="${HERMES_HOME:-/opt/data}"
INSTALL_DIR="/opt/hermes"

# --- Directory bootstrap ---
# Create mutable directories if not present (PVC may be empty on first run)
mkdir -p "$HERMES_HOME"/{sessions,memories,logs,skills,store,cron,hooks}

# --- Restore from backup on empty PVC ---
if [ ! -f "$HERMES_HOME/state.db" ] && [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    echo "Empty PVC detected. Attempting restore from backup..." >&2
    python3 /opt/hermes/docker/restore-from-s3.py "$BACKUP_S3_BUCKET" "$HERMES_HOME" \
        && echo "Restore successful." >&2 \
        || echo "WARNING: Restore failed. Bootstrapping fresh instance." >&2
fi

# --- Default config bootstrap (local Docker dev only) ---
# In K8s, ConfigMaps mount config.yaml/SOUL.md directly — these conditionals
# never trigger. If a ConfigMap is missing, the pod fails at mount time before
# this script runs. These exist for: docker run -v empty-vol:/opt/data
[ ! -f "$HERMES_HOME/.env" ]        && cp /opt/defaults/.env.example "$HERMES_HOME/.env"
[ ! -f "$HERMES_HOME/config.yaml" ] && cp /opt/defaults/config.yaml "$HERMES_HOME/config.yaml"
[ ! -f "$HERMES_HOME/SOUL.md" ]     && cp "$INSTALL_DIR/docker/SOUL.md" "$HERMES_HOME/SOUL.md"

# --- System prompt injection (safe — no shell interpretation) ---
# system-prompt.md is client-authored content. We load it via Python to avoid
# shell injection from backticks, $(), or unbalanced quotes in prompt text.
if [ -f "$HERMES_HOME/system-prompt.md" ]; then
    HERMES_EPHEMERAL_SYSTEM_PROMPT="$(python3 -c "
import sys, os
p = os.path.join(os.environ.get('HERMES_HOME', '/opt/data'), 'system-prompt.md')
sys.stdout.buffer.write(open(p, 'rb').read())
")"
    export HERMES_EPHEMERAL_SYSTEM_PROMPT
fi

# --- WAL mode enforcement ---
# Ensure all SQLite databases use WAL journal mode for crash resilience on
# block storage. Runs once at startup — idempotent.
python3 -c "
import glob, sqlite3, os
home = os.environ.get('HERMES_HOME', '/opt/data')
dbs = glob.glob(os.path.join(home, '**', '*.db'), recursive=True)
for db_path in dbs:
    try:
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.close()
    except Exception as e:
        print(f'WARNING: WAL mode failed for {db_path}: {e}', flush=True)
" 2>&1 || echo "WARNING: WAL enforcement failed — continuing" >&2

# --- Skill sync (local file copy, no network) ---
if [ -d "$INSTALL_DIR/skills" ]; then
    python3 "$INSTALL_DIR/tools/skills_sync.py" \
        || echo "WARNING: skills_sync failed — bot will run without bundled skill updates" >&2
fi

# --- Working directory ---
# Halos modules expect store/ and memory/ relative to cwd.
cd "$HERMES_HOME"

# --- Heartbeat wrapper ---
# Upstream Hermes doesn't write a heartbeat file. Rather than patching Hermes,
# we wrap it: a background loop touches the heartbeat file every 30s ONLY if
# the main process (Hermes) is alive AND responsive.
#
# How it works:
#   1. Start Hermes in the background
#   2. Background loop checks /proc/$PID/status every 30s
#   3. If Hermes is alive, touch heartbeat
#   4. If Hermes dies, the loop exits and we propagate the exit code
#   5. K8s liveness probe checks heartbeat staleness (120s threshold)
#
# Limitation: this detects process death but NOT asyncio deadlocks.
# A true deadlock detector requires an in-process health endpoint.
# Acceptable for Phase 1 — revisit with an HTTP health check sidecar if needed.

hermes "$@" &
HERMES_PID=$!

# Write initial heartbeat after Hermes process starts (not before)
touch "$HERMES_HOME/heartbeat"

# Heartbeat loop — runs until Hermes exits
(
    while kill -0 "$HERMES_PID" 2>/dev/null; do
        touch "$HERMES_HOME/heartbeat"
        sleep 30
    done
) &
HEARTBEAT_PID=$!

# Wait for Hermes to exit, capture its exit code
wait "$HERMES_PID"
EXIT_CODE=$?

# Kill heartbeat loop (it may already be gone)
kill "$HEARTBEAT_PID" 2>/dev/null || true
wait "$HEARTBEAT_PID" 2>/dev/null || true

exit "$EXIT_CODE"
