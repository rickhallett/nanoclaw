"""jobctl metrics — JSON output for dashctl integration."""

import json
import click
from jobctl.db import get_conn, init_db


@click.command("metrics")
def metrics_cmd():
    """Output JSON metrics for dashctl integration."""
    init_db()
    conn = get_conn()

    counts = {row["status"]: row["count"] for row in conn.execute(
        "SELECT status, COUNT(*) as count FROM listings GROUP BY status"
    ).fetchall()}

    applied_count = counts.get("applied", 0) + counts.get("interviewing", 0) + \
                    counts.get("offered", 0) + counts.get("rejected", 0)
    reviewed_count = sum(counts.get(s, 0) for s in ["accepted", "dismissed", "applied",
                                                       "interviewing", "offered", "rejected"])
    total = sum(counts.values())
    accepted_count = counts.get("accepted", 0)

    # Response rate: interviewing+offered / applied total
    total_applied = applied_count
    responded = counts.get("interviewing", 0) + counts.get("offered", 0)
    response_rate = round(responded / total_applied, 3) if total_applied > 0 else 0.0

    # Acceptance rate: accepted / (accepted + dismissed)
    decided = accepted_count + counts.get("dismissed", 0)
    acceptance_rate = round(accepted_count / decided, 3) if decided > 0 else 0.0

    metrics = {
        "applied_count": applied_count,
        "reviewed_count": reviewed_count,
        "total_count": total,
        "pending_review_count": counts.get("pending_review", 0),
        "accepted_count": accepted_count,
        "dismissed_count": counts.get("dismissed", 0),
        "interviewing_count": counts.get("interviewing", 0),
        "offered_count": counts.get("offered", 0),
        "rejected_count": counts.get("rejected", 0),
        "response_rate": response_rate,
        "acceptance_rate": acceptance_rate,
    }

    conn.close()
    click.echo(json.dumps(metrics, indent=2))
