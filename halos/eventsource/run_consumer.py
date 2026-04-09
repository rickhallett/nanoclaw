#!/usr/bin/env python3
"""Standalone NATS event consumer process for an advisor pod.

Runs alongside Hermes as a background process. Consumes events from
the HALO stream and maintains local SQLite projections that halos CLI
tools can read.

Environment variables:
    ADVISOR_NAME        - advisor identifier (e.g. "musashi")
    NATS_URL            - NATS server URL (default: nats://nats.halo-fleet.svc.cluster.local:4222)
    NATS_USER           - NATS auth user (default: "advisor")
    NATS_PASS           - NATS auth password (required)
    HALO_STORE_DIR      - projection database path (default: $HERMES_HOME/store)
    HERMES_HOME         - data directory (default: /opt/data)
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

from halos.eventsource.consumer import AdvisorEventLoop
from halos.eventsource.handlers.advisor import AdvisorTelephonyHandler
from halos.eventsource.handlers.dev import DevCommitProjectionHandler
from halos.eventsource.handlers.journal import JournalProjectionHandler
from halos.eventsource.handlers.mail import MailTriageHandler
from halos.eventsource.handlers.night import NightProjectionHandler
from halos.eventsource.handlers.observation import ObservationProjectionHandler
from halos.eventsource.handlers.system import SystemEventHandler
from halos.eventsource.handlers.track import TrackProjectionHandler


def _resolve_store_dir() -> Path:
    if os.environ.get("HALO_STORE_DIR"):
        return Path(os.environ["HALO_STORE_DIR"])
    home = os.environ.get("HERMES_HOME", "/opt/data")
    return Path(home) / "store"


def main():
    advisor_name = os.environ.get("ADVISOR_NAME")
    if not advisor_name:
        print("ERROR: ADVISOR_NAME not set", file=sys.stderr)
        sys.exit(1)

    nats_pass = os.environ.get("NATS_PASS")
    if not nats_pass:
        print("ERROR: NATS_PASS not set", file=sys.stderr)
        sys.exit(1)

    nats_url = os.environ.get("NATS_URL", "nats://nats.halo-fleet.svc.cluster.local:4222")
    nats_user = os.environ.get("NATS_USER", "advisor")
    store_dir = _resolve_store_dir()

    print(f"[eventsource] Starting consumer for {advisor_name}", flush=True)
    print(f"[eventsource] NATS: {nats_url} user={nats_user}", flush=True)
    print(f"[eventsource] Projection: {store_dir}/projection.db", flush=True)

    loop_instance = AdvisorEventLoop(
        advisor_name=advisor_name,
        nats_url=nats_url,
        nats_user=nats_user,
        nats_pass=nats_pass,
        projection_path=store_dir / "projection.db",
        handlers=[
            AdvisorTelephonyHandler(),
            DevCommitProjectionHandler(),
            JournalProjectionHandler(),
            MailTriageHandler(),
            NightProjectionHandler(),
            ObservationProjectionHandler(),
            SystemEventHandler(),
            TrackProjectionHandler(),
        ],
        subscriptions=["halo.>"],
    )

    loop = asyncio.new_event_loop()

    def shutdown(sig, _frame):
        print(f"[eventsource] Received {signal.Signals(sig).name}, stopping...", flush=True)
        loop.create_task(loop_instance.stop())

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        loop.run_until_complete(loop_instance.start())
    except KeyboardInterrupt:
        loop.run_until_complete(loop_instance.stop())
    finally:
        loop.close()
        print(f"[eventsource] Consumer stopped", flush=True)


if __name__ == "__main__":
    main()
