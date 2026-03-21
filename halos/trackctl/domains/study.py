"""Study accountability tracker — three sub-domains, 1hr/day each.

Domains registered:
  study-source   — reading NanoClaw source code
  study-neetcode — DS & algorithms (neetcode.io)
  study-crafters — systems programming (codecrafters.io)

Each targets daily consistency. Streak logic same as zazen.
"""

from halos.trackctl.registry import register

register(
    name="study-source",
    description="NanoClaw source code reading (1hr/day target)",
    target=0,
)

register(
    name="study-neetcode",
    description="DS & algorithms — neetcode.io (1hr/day target)",
    target=0,
)

register(
    name="study-crafters",
    description="Systems programming — codecrafters.io (1hr/day target)",
    target=0,
)
