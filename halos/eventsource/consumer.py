"""Event consumer lifecycle — connects to NATS and drives the projection."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import nats
import nats.js.api

from .core import Event, EventPublisher
from .projection import ProjectionEngine, ProjectionHandler


class AdvisorEventLoop:
    """Main event consumption loop for an advisor.

    Connects to NATS JetStream, replays from last checkpoint,
    then enters steady-state consumption. The projection is
    rebuilt automatically on startup if needed.
    """

    def __init__(
        self,
        advisor_name: str,
        nats_url: str,
        nats_user: str,
        nats_pass: str,
        projection_path: Path | str,
        handlers: list[ProjectionHandler],
    ):
        self.advisor_name = advisor_name
        self.nats_url = nats_url
        self.nats_user = nats_user
        self.nats_pass = nats_pass
        self.projection = ProjectionEngine(Path(projection_path), handlers)
        self.publisher: EventPublisher | None = None
        self._nc: nats.NATS | None = None
        self._sub = None
        self._start_time = 0.0
        self._running = False

    async def start(self) -> None:
        """Connect to NATS, replay from checkpoint, enter steady state."""
        self._start_time = time.monotonic()
        self.projection.open()

        self._nc = await nats.connect(
            self.nats_url,
            user=self.nats_user,
            password=self.nats_pass,
        )

        self.publisher = EventPublisher(
            self._nc, source=self.advisor_name
        )

        self._sub = await self._nc.jetstream().pull_subscribe(
            "halo.>",
            durable=self.advisor_name,
            config=nats.js.api.ConsumerConfig(
                ack_policy=nats.js.api.AckPolicy.EXPLICIT,
                max_deliver=3,
                ack_wait=30,
            ),
        )

        await self.publisher.emit(
            "system.advisor.started",
            {
                "advisor": self.advisor_name,
                "version": self._get_version(),
                "image_tag": self._get_image_tag(),
            },
        )

        self._running = True
        await self._consume_loop()

    async def _consume_loop(self) -> None:
        """Pull and process events until stopped."""
        while self._running:
            try:
                messages = await self._sub.fetch(batch=10, timeout=5)
                for msg in messages:
                    event = Event.from_json(
                        msg.data,
                        stream_seq=msg.metadata.sequence.stream,
                    )
                    self.projection.apply(event, self.advisor_name)
                    await msg.ack()
            except nats.errors.TimeoutError:
                pass  # No messages — normal idle
            except Exception as e:
                print(f"ERROR processing event: {e}", flush=True)
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False

        if self.publisher:
            try:
                await self.publisher.emit(
                    "system.advisor.stopped",
                    {
                        "advisor": self.advisor_name,
                        "reason": "shutdown",
                        "uptime_secs": self._uptime(),
                    },
                )
            except Exception:
                pass  # Best-effort on shutdown

        if self._sub:
            await self._sub.unsubscribe()
        if self._nc:
            await self._nc.close()
        self.projection.close()

    def _get_version(self) -> str:
        return os.environ.get("HALO_VERSION", "0.0.0-dev")

    def _get_image_tag(self) -> str:
        return os.environ.get("HALO_IMAGE_TAG", "unknown")

    def _uptime(self) -> float:
        return time.monotonic() - self._start_time
