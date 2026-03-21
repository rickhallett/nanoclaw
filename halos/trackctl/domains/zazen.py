"""Zazen (seated meditation) tracker domain.

Fields: timestamp, duration_mins, notes
Streak: any day with >= 1 entry counts. Miss a calendar day = reset.
Target: 100 consecutive days.
"""

from halos.trackctl.registry import register

register(
    name="zazen",
    description="Seated meditation practice",
    target=100,
)
