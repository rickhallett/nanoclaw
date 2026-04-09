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

# --- Seed track databases (baked into image, copied on first run only) ---
# Existing dbs on the PVC are never overwritten — only missing ones are seeded.
if [ -d /opt/defaults/store ]; then
    for db in /opt/defaults/store/track_*.db; do
        [ -f "$db" ] || continue
        target="$HERMES_HOME/store/$(basename "$db")"
        if [ ! -f "$target" ]; then
            cp "$db" "$target"
            echo "Seeded $(basename "$db")" >&2
        fi
    done
fi

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
#
# .env: Hermes loads $HERMES_HOME/.env with override=True (dotenv), so this
# file MUST contain real values, not empty placeholders. When running via
# `docker run --env-file`, we generate .env from the live environment.
# In K8s, the Secret mount provides the file directly.
if [ ! -f "$HERMES_HOME/.env" ]; then
    # Generate .env from environment variables passed via --env-file or -e
    # Only write keys that are actually set and non-empty
    {
        [ -n "${TELEGRAM_BOT_TOKEN:-}" ]      && echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
        [ -n "${ANTHROPIC_API_KEY:-}" ]      && echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
        [ -n "${TELEGRAM_ALLOWED_USERS:-}" ] && echo "TELEGRAM_ALLOWED_USERS=$TELEGRAM_ALLOWED_USERS"
        [ -n "${COST_CEILING_USD:-}" ]       && echo "COST_CEILING_USD=$COST_CEILING_USD"
        [ -n "${DEFAULT_MODEL:-}" ]          && echo "DEFAULT_MODEL=$DEFAULT_MODEL"
        [ -n "${DEFAULT_PROVIDER:-}" ]       && echo "DEFAULT_PROVIDER=$DEFAULT_PROVIDER"
    } > "$HERMES_HOME/.env"
    echo "Generated .env from environment variables." >&2
fi
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

# --- Gateway NATS hooks bootstrap (optional) ---
# Installs a local hook that mirrors inbound/outbound advisor messages to
# Halostream with a standardized event envelope.
if [ "${ENABLE_NATS_GATEWAY_HOOK:-1}" = "1" ]; then
    HOOK_DIR="$HERMES_HOME/hooks/nats-events"
    mkdir -p "$HOOK_DIR"
    cat > "$HOOK_DIR/HOOK.yaml" <<'YAML'
name: nats-events
description: Publish advisor inbound/outbound messages to NATS
events:
  - agent:start
  - agent:end
YAML
    cat > "$HOOK_DIR/handler.py" <<'PY'
import json
import os
import uuid
from datetime import datetime, timezone

import nats


async def _publish(subject: str, event: dict) -> None:
    nats_pass = os.environ.get("NATS_PASS", "")
    if not nats_pass:
        return
    nats_url = os.environ.get("NATS_URL", "nats://nats.halo-fleet.svc.cluster.local:4222")
    nats_user = os.environ.get("NATS_USER", "advisor")
    nc = await nats.connect(nats_url, user=nats_user, password=nats_pass)
    try:
        js = nc.jetstream()
        await js.publish(
            subject,
            json.dumps(event).encode(),
            headers={"Nats-Msg-Id": event["id"]},
        )
    finally:
        await nc.close()


def _event(event_type: str, context: dict) -> tuple[str, dict]:
    advisor = os.environ.get("ADVISOR_NAME", "unknown")
    now = datetime.now(timezone.utc).isoformat()
    session_id = str(context.get("session_id", "") or "")

    if event_type == "agent:start":
        evt_type = "advisor.inbound.received"
        text = str(context.get("message", "") or "")
        direction = "inbound"
        subject = "halo.advisor.inbound.received"
    else:
        evt_type = "advisor.outbound.sent"
        text = str(context.get("response", "") or "")
        direction = "outbound"
        subject = "halo.advisor.outbound.sent"

    payload = {
        "schema_version": "1.0",
        "advisor": advisor,
        "direction": direction,
        "platform": str(context.get("platform", "") or ""),
        "session_id": session_id,
        "user_id": str(context.get("user_id", "") or ""),
        "message_text": text,
        "message_len": len(text),
        "event_name": event_type,
    }

    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": evt_type,
        "version": 1,
        "source": advisor,
        "timestamp": now,
        "correlation_id": session_id or f"cor_{uuid.uuid4().hex}",
        "payload": payload,
    }
    return subject, event


async def handle(event_type: str, context: dict):
    if event_type not in ("agent:start", "agent:end"):
        return
    try:
        subject, event = _event(event_type, context or {})
        await _publish(subject, event)
    except Exception:
        # Hooks must never block gateway processing.
        return
PY
fi

# --- Advisor touchbase cron bootstrap (optional, idempotent) ---
if [ -n "${ADVISOR_NAME:-}" ] && [ -n "${ADVISOR_TOUCHBASE_SCHEDULE:-}" ]; then
    python3 - <<'PY'
import os
from cron.jobs import create_job, list_jobs, parse_schedule, update_job

advisor = os.environ.get("ADVISOR_NAME", "").strip()
schedule = os.environ.get("ADVISOR_TOUCHBASE_SCHEDULE", "").strip()
chat_id = os.environ.get("ADVISOR_TOUCHBASE_CHAT_ID", "").strip()
platform = os.environ.get("ADVISOR_TOUCHBASE_PLATFORM", "telegram").strip() or "telegram"
name = f"touchbase-{advisor}"

if advisor and schedule:
    prompt = (
        "Morning touch-base. Give a concise synthesis covering: "
        "(1) current focus goals status, "
        "(2) what we are focused on today, "
        "(3) blockers or blind spots, "
        "(4) direct questions for Kai. "
        "Use your available halos tools to ground claims. "
        "Keep it brief, specific, and operator-grade."
    )

    origin = {"platform": platform, "chat_id": chat_id} if chat_id else None
    deliver = "origin" if origin else platform

    existing = None
    for job in list_jobs(include_disabled=True):
        if job.get("name") == name:
            existing = job
            break

    if existing is None:
        create_job(
            prompt=prompt,
            schedule=schedule,
            name=name,
            deliver=deliver,
            origin=origin,
        )
    else:
        updates = {"enabled": True}
        desired_display = schedule
        if existing.get("schedule_display") != desired_display:
            updates["schedule"] = parse_schedule(schedule)
            updates["schedule_display"] = desired_display
        if existing.get("deliver") != deliver:
            updates["deliver"] = deliver
        if origin and existing.get("origin") != origin:
            updates["origin"] = origin
        if updates:
            update_job(existing["id"], updates)
PY
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

# --- Event consumer (NATS → local projection) ---
# Runs alongside Hermes if NATS_PASS is set. Maintains SQLite projections
# that halos CLI tools read. Crashes are non-fatal to the main process.
if [ -n "${NATS_PASS:-}" ]; then
    python3 -m halos.eventsource.run_consumer &
    CONSUMER_PID=$!
    echo "Started event consumer (PID $CONSUMER_PID)" >&2
fi

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

# Kill event consumer if running
if [ -n "${CONSUMER_PID:-}" ]; then
    kill "$CONSUMER_PID" 2>/dev/null || true
    wait "$CONSUMER_PID" 2>/dev/null || true
fi

exit "$EXIT_CODE"
