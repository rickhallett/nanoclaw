"""Daily movement tracker domain.

Freeform log — no rigid workout plan. Log what you did, grow organically.
Fields: timestamp, duration_mins, notes (activity description goes in notes).
Streak: any day with >= 1 entry counts. Miss a calendar day = reset.
Target: none (ongoing accountability, no fixed goal).
"""

from halos.trackctl.registry import register

register(
    name="movement",
    description="Daily movement and exercise log",
    target=0,
)
