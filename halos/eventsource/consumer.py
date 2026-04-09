"""Event consumer lifecycle — connects to NATS and drives the projection."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import nats
import nats.js.api

from .core import Event, EventPublisher, ProjectionHandler
from .projection import ProjectionEngine

# Minimal payload validation for known high-volume event types.
_REQUIRED_PAYLOAD_KEYS: dict[str, frozenset[str]] = {
    "track.movement.logged": frozenset({"domain", "duration_mins", "entry_id"}),
    "track.zazen.logged": frozenset({"domain", "duration_mins", "entry_id"}),
    "track.study.logged": frozenset({"domain", "duration_mins", "entry_id"}),
    # Fallback for any track domain not listed above
    "track.*.logged": frozenset({"domain", "duration_mins", "entry_id"}),
    "track.entry.deleted": frozenset({"domain", "entry_id"}),
    "track.entry.edited": frozenset({"domain", "entry_id"}),
    "night.item.created": frozenset({"item_id", "title"}),
    "night.item.transitioned": frozenset({"item_id", "to_status"}),
    "night.item.updated": frozenset({"item_id"}),
    "night.job.completed": frozenset({"job_id"}),
    "night.job.failed": frozenset({"job_id"}),
    "journal.entry.added": frozenset({"entry_id"}),
}


class AdvisorEventLoop:
    """Main event consumption loop for an advisor.

    Connects to NATS JetStream, replays from checkpoint, then enters
    steady-state consumption.
    """

    def __init__(
        self,
        advisor_name: str,
        nats_url: str,
        nats_user: str,
        nats_pass: str,
        projection_path: Path | str,
        handlers: list[ProjectionHandler],
        subscriptions: list[str] | None = None,
        stream: str = "HALO",
        ack_wait_secs: int = 30,
    ):
        self.advisor_name = advisor_name
        self.nats_url = nats_url
        self.nats_user = nats_user
        self.nats_pass = nats_pass
        self.stream = stream
        self.ack_wait_secs = ack_wait_secs
        self.subscriptions = subscriptions or ["halo.>"]

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
        last_seq = self.projection.last_checkpoint(self.advisor_name)

        self._nc = await nats.connect(
            self.nats_url,
            user=self.nats_user,
            password=self.nats_pass,
        )
        js = self._nc.jetstream()

        self.publisher = EventPublisher(self._nc, stream=self.stream, source=self.advisor_name)

        # If projection has no checkpoint (empty/brand-new DB), reset the durable consumer
        # so replay starts from the beginning and the projection can be rebuilt deterministically.
        if last_seq == 0:
            try:
                await js.delete_consumer(self.stream, self.advisor_name)
            except Exception:
                pass  # Missing consumer is fine.

        cfg_kwargs: dict[str, object] = {
            "durable_name": self.advisor_name,
            "ack_policy": nats.js.api.AckPolicy.EXPLICIT,
            "max_deliver": 3,
            "ack_wait": float(self.ack_wait_secs),
            "filter_subjects": self.subscriptions,
            "deliver_policy": nats.js.api.DeliverPolicy.ALL,
        }
        if last_seq > 0:
            cfg_kwargs["deliver_policy"] = nats.js.api.DeliverPolicy.BY_START_SEQUENCE
            cfg_kwargs["opt_start_seq"] = last_seq + 1

        self._sub = await js.pull_subscribe(
            self.subscriptions[0],
            durable=self.advisor_name,
            config=nats.js.api.ConsumerConfig(**cfg_kwargs),
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
                    try:
                        event = Event.from_json(
                            msg.data,
                            stream_seq=msg.metadata.sequence.stream,
                        )
                        validation_error = self._validate_event(event)
                        if validation_error:
                            await self._emit_system_error(
                                error_type="event.validation",
                                message=validation_error,
                                event=event,
                            )
                            await msg.ack()
                            continue

                        self.projection.apply(event, self.advisor_name)
                        await msg.ack()
                    except (KeyError, TypeError, ValueError) as e:
                        await self._emit_system_error(
                            error_type="event.processing",
                            message=str(e),
                            event_data=msg.data.decode(errors="replace"),
                        )
                        await msg.ack()  # poison message: skip after reporting
            except nats.errors.TimeoutError:
                pass  # Normal idle
            except Exception as e:
                print(f"ERROR processing event batch: {e}", flush=True)
                await asyncio.sleep(1)

    def _validate_event(self, event: Event) -> str | None:
        required = _REQUIRED_PAYLOAD_KEYS.get(event.type)
        if not required:
            # Check wildcard patterns (e.g. track.*.logged)
            parts = event.type.split(".")
            if len(parts) == 3:
                wildcard = f"{parts[0]}.*.{parts[2]}"
                required = _REQUIRED_PAYLOAD_KEYS.get(wildcard)
        if not required:
            return None

        missing = sorted(k for k in required if k not in event.payload)
        if missing:
            return (
                f"Missing required payload keys for {event.type}: "
                f"{', '.join(missing)}"
            )
        return None

    async def _emit_system_error(
        self,
        *,
        error_type: str,
        message: str,
        event: Event | None = None,
        event_data: str | None = None,
    ) -> None:
        if not self.publisher:
            return
        try:
            payload: dict[str, object] = {
                "source": self.advisor_name,
                "error_type": error_type,
                "message": message,
            }
            if event is not None:
                payload["event_id"] = event.id
                payload["event_type"] = event.type
                payload["stream_seq"] = event.stream_seq
            if event_data is not None:
                payload["event_data"] = event_data[:1000]
            await self.publisher.emit("system.error", payload)
        except Exception:
            pass

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
                pass

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
