"""Data sources for calctl.

Each source implements a common interface:
    fetch(start: datetime, end: datetime) -> list[dict]

Each returned dict has at minimum:
    source: str        — "google_calendar", "nightctl", "cronctl"
    title: str
    start: datetime    — UTC
    end: datetime|None — UTC (None for point-in-time events like deadlines)
    metadata: dict     — source-specific fields
"""

from __future__ import annotations

import sys
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml


class CalendarEvent:
    """Unified event representation across all sources."""

    __slots__ = ("source", "title", "start", "end", "metadata")

    def __init__(
        self,
        source: str,
        title: str,
        start: datetime,
        end: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ):
        self.source = source
        self.title = title
        self.start = start
        self.end = end
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"CalendarEvent({self.source!r}, {self.title!r}, {self.start})"


class Source(ABC):
    """Base class for calctl data sources."""

    @abstractmethod
    def fetch(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """Fetch events in the given UTC time range [start, end)."""
        ...


# ---------------------------------------------------------------------------
# NightctlSource — items with due dates
# ---------------------------------------------------------------------------


class NightctlSource(Source):
    """Load nightctl items that have a due date within the query range."""

    def __init__(self, items_dir: Optional[Path] = None):
        self._items_dir = items_dir

    def _resolve_items_dir(self) -> Path:
        if self._items_dir:
            return self._items_dir
        # Try nightctl config, fall back to default
        try:
            from halos.nightctl.config import load_config
            cfg = load_config()
            return cfg.items_dir
        except Exception:
            return Path("queue/items").resolve()

    def fetch(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        items_dir = self._resolve_items_dir()
        if not items_dir.exists():
            return []

        events: list[CalendarEvent] = []
        for f in sorted(items_dir.glob("*.yaml")):
            try:
                with open(f) as fh:
                    data = yaml.safe_load(fh) or {}
            except Exception:
                continue

            due = data.get("due")
            if not due:
                continue

            # Parse the due date
            due_dt = _parse_date_or_datetime(due)
            if due_dt is None:
                continue

            # Check range
            if due_dt < start or due_dt >= end:
                continue

            status = data.get("status", "open")
            if status in ("done", "cancelled"):
                continue

            quadrant = data.get("quadrant", data.get("priority", "q3"))
            if isinstance(quadrant, int):
                quadrant = f"q{min(max(quadrant, 1), 4)}"

            events.append(CalendarEvent(
                source="nightctl",
                title=data.get("title", f.stem),
                start=due_dt,
                end=None,
                metadata={
                    "id": data.get("id", ""),
                    "quadrant": quadrant,
                    "status": status,
                    "kind": data.get("kind", "task"),
                },
            ))
        return events


# ---------------------------------------------------------------------------
# CronctlSource — next run times for enabled cron jobs
# ---------------------------------------------------------------------------


class CronctlSource(Source):
    """Compute next run times for cronctl jobs within the query range."""

    def __init__(self, jobs_dir: Optional[Path] = None):
        self._jobs_dir = jobs_dir

    def _resolve_jobs_dir(self) -> Path:
        if self._jobs_dir:
            return self._jobs_dir
        try:
            from halos.cronctl.config import load_config
            cfg = load_config()
            return cfg.jobs_dir
        except Exception:
            return Path("cron/jobs").resolve()

    def fetch(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        jobs_dir = self._resolve_jobs_dir()
        if not jobs_dir.exists():
            return []

        events: list[CalendarEvent] = []
        for f in sorted(jobs_dir.glob("*.yaml")):
            try:
                with open(f) as fh:
                    data = yaml.safe_load(fh) or {}
            except Exception:
                continue

            if not data.get("enabled", True):
                continue

            schedule_expr = data.get("schedule", "")
            if not schedule_expr:
                continue

            title = data.get("title", data.get("id", f.stem))

            # Compute next runs within the window
            try:
                runs = _cron_next_runs(schedule_expr, start, end)
            except Exception:
                continue

            for run_time in runs:
                events.append(CalendarEvent(
                    source="cronctl",
                    title=title,
                    start=run_time,
                    end=None,
                    metadata={
                        "id": data.get("id", ""),
                        "schedule": schedule_expr,
                        "command": data.get("command", ""),
                    },
                ))
        return events


# ---------------------------------------------------------------------------
# GoogleCalendarSource — Google Calendar API
# ---------------------------------------------------------------------------


class GoogleCalendarSource(Source):
    """Fetch events from Google Calendar API.

    Gracefully degrades if credentials or libraries are unavailable.
    """

    def __init__(self, calendar_id: str = "primary", credentials_dir: Optional[Path] = None):
        self._calendar_id = calendar_id
        self._credentials_dir = credentials_dir

    def fetch(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        try:
            return self._fetch_impl(start, end)
        except ImportError:
            warnings.warn(
                "Google Calendar API libraries not available. "
                "Install google-auth and google-api-python-client for calendar integration.",
                stacklevel=2,
            )
            return []
        except Exception as e:
            warnings.warn(
                f"Google Calendar fetch failed: {e}. Returning empty list.",
                stacklevel=2,
            )
            return []

    def _fetch_impl(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = self._load_credentials()
        if creds is None:
            warnings.warn(
                "Google Calendar credentials not found. "
                "Run OAuth flow to configure.",
                stacklevel=2,
            )
            return []

        service = build("calendar", "v3", credentials=creds)
        events_result = (
            service.events()
            .list(
                calendarId=self._calendar_id,
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=100,
            )
            .execute()
        )

        events: list[CalendarEvent] = []
        for item in events_result.get("items", []):
            ev_start = self._parse_gcal_time(item.get("start", {}))
            ev_end = self._parse_gcal_time(item.get("end", {}))
            if ev_start is None:
                continue

            attendees = [
                a.get("email", "") for a in item.get("attendees", [])
            ]

            events.append(CalendarEvent(
                source="google_calendar",
                title=item.get("summary", "(no title)"),
                start=ev_start,
                end=ev_end,
                metadata={
                    "location": item.get("location", ""),
                    "attendees": attendees,
                    "event_id": item.get("id", ""),
                    "html_link": item.get("htmlLink", ""),
                },
            ))
        return events

    def _load_credentials(self):
        """Load Google OAuth credentials from the standard location."""
        try:
            from google.oauth2.credentials import Credentials
        except ImportError:
            return None

        cred_dir = self._credentials_dir or Path.home() / ".google-workspace-mcp" / "credentials"
        token_file = cred_dir / "token.json"
        if not token_file.exists():
            return None

        import json
        with open(token_file) as f:
            token_data = json.load(f)

        return Credentials.from_authorized_user_info(token_data)

    @staticmethod
    def _parse_gcal_time(time_dict: dict) -> Optional[datetime]:
        """Parse a Google Calendar start/end time dict."""
        if not time_dict:
            return None
        # dateTime for timed events, date for all-day events
        dt_str = time_dict.get("dateTime") or time_dict.get("date")
        if not dt_str:
            return None
        try:
            dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except ValueError:
            return None


# ---------------------------------------------------------------------------
# Cron expression parsing (no croniter dependency)
# ---------------------------------------------------------------------------


def _cron_next_runs(
    expr: str, start: datetime, end: datetime, max_runs: int = 50
) -> list[datetime]:
    """Compute cron expression run times within [start, end).

    Supports basic 5-field cron: minute hour dom month dow.
    Supports: *, N, N-M, */N, N/M.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return []

    minute_set = _parse_cron_field(parts[0], 0, 59)
    hour_set = _parse_cron_field(parts[1], 0, 23)
    dom_set = _parse_cron_field(parts[2], 1, 31)
    month_set = _parse_cron_field(parts[3], 1, 12)
    dow_set = _parse_cron_field(parts[4], 0, 6)

    runs: list[datetime] = []

    # Walk minute-by-minute from start. For efficiency, skip at day level
    # when month or dom don't match.
    current = start.replace(second=0, microsecond=0)

    while current < end and len(runs) < max_runs:
        if current.month not in month_set:
            # Skip to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1, hour=0, minute=0)
            else:
                current = current.replace(month=current.month + 1, day=1, hour=0, minute=0)
            continue

        if current.day not in dom_set or current.weekday() not in _dow_to_python(dow_set):
            current = current.replace(hour=0, minute=0) + timedelta(days=1)
            continue

        if current.hour not in hour_set:
            current = current.replace(minute=0) + timedelta(hours=1)
            continue

        if current.minute not in minute_set:
            current += timedelta(minutes=1)
            continue

        if current >= start:
            runs.append(current)

        current += timedelta(minutes=1)

    return runs


def _parse_cron_field(field: str, min_val: int, max_val: int) -> set[int]:
    """Parse a single cron field into a set of integer values."""
    values: set[int] = set()
    for part in field.split(","):
        if "/" in part:
            base, step_str = part.split("/", 1)
            step = int(step_str)
            if base == "*":
                start = min_val
            elif "-" in base:
                start = int(base.split("-")[0])
            else:
                start = int(base)
            for v in range(start, max_val + 1, step):
                values.add(v)
        elif part == "*":
            values.update(range(min_val, max_val + 1))
        elif "-" in part:
            lo, hi = part.split("-", 1)
            values.update(range(int(lo), int(hi) + 1))
        else:
            values.add(int(part))
    return values


def _dow_to_python(cron_dow: set[int]) -> set[int]:
    """Convert cron day-of-week (0=Sun) to Python weekday (0=Mon)."""
    mapping = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
    return {mapping.get(d, d) for d in cron_dow}


def _parse_date_or_datetime(value) -> Optional[datetime]:
    """Parse a date string or datetime string into a UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if not isinstance(value, str):
        return None

    value = value.strip()

    # Try ISO datetime
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue

    # Try date-only
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # Try fromisoformat as last resort
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None
