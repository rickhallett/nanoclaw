"""CLI entry point for hal-briefing command."""

import argparse
import sys

from halos.common.log import hlog

from .archive import archive_briefing
from .config import load_config
from .deliver import deliver_message
from .diary import write_diary_entry
from .gather import gather_morning, gather_nightly
from .nightctl_summary import gather_nightctl_summary, format_nightctl_summary
from .synthesise import synthesise


def cmd_morning(args, cfg):
    hlog("briefings", "info", "morning_start", {})
    data = gather_morning(cfg)

    if args.dry_run:
        print(data.to_context())
        print("\n--- (dry-run: no synthesis or delivery) ---")
        return 0

    if args.raw:
        text = data.to_context() + "\n\n🔴"
    else:
        text = synthesise(data, cfg)

    if args.no_send:
        print(text)
        return 0

    archive_path = archive_briefing(cfg, "morning", text)
    path = deliver_message(cfg, text)
    hlog(
        "briefings",
        "info",
        "morning_delivered",
        {
            "ipc_file": str(path),
            "archive": str(archive_path),
        },
    )
    print(f"delivered → {path.name}")
    print(f"archived → {archive_path}")
    return 0


def cmd_nightly(args, cfg):
    hlog("briefings", "info", "nightly_start", {})
    data = gather_nightly(cfg)

    if args.dry_run:
        print(data.to_context())
        print("\n--- (dry-run: no synthesis or delivery) ---")
        return 0

    if args.raw:
        text = data.to_context() + "\n\n🔴"
    else:
        text = synthesise(data, cfg)

    if args.no_send:
        print(text)
        return 0

    archive_path = archive_briefing(cfg, "nightly", text)
    path = deliver_message(cfg, text)
    hlog(
        "briefings",
        "info",
        "nightly_delivered",
        {
            "ipc_file": str(path),
            "archive": str(archive_path),
        },
    )
    print(f"delivered → {path.name}")
    print(f"archived → {archive_path}")
    return 0


def cmd_diary(args, cfg):
    hlog("briefings", "info", "diary_start", {})

    path = write_diary_entry(cfg, dry_run=args.dry_run)

    if args.dry_run:
        print("\n--- (dry-run: not written to disk) ---")
        return 0

    if path:
        hlog("briefings", "info", "diary_written", {"file": str(path)})
        print(f"written → {path}")
    else:
        hlog("briefings", "warn", "diary_failed", {})
        print("WARNING: diary entry could not be generated", file=sys.stderr)
        return 1
    return 0


def cmd_nightctl(args, cfg):
    """Pre-morning summary of overnight nightctl activity."""
    hlog("briefings", "info", "nightctl_summary_start", {})
    summary = gather_nightctl_summary(cfg)

    if args.dry_run:
        print(format_nightctl_summary(summary))
        print("\n--- (dry-run: no delivery) ---")
        return 0

    text = format_nightctl_summary(summary)

    if args.no_send:
        print(text)
        return 0

    archive_path = archive_briefing(cfg, "nightctl", text)
    path = deliver_message(cfg, text)
    hlog(
        "briefings",
        "info",
        "nightctl_summary_delivered",
        {
            "ipc_file": str(path),
            "archive": str(archive_path),
        },
    )
    print(f"delivered → {path.name}")
    print(f"archived → {archive_path}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="hal-briefing",
        description="HAL daily briefings — morning and nightly digests via Telegram",
    )
    parser.add_argument("--config", default=None, help="Path to briefings.yaml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Gather data but skip synthesis and delivery",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Skip synthesis, send raw data as the message",
    )
    parser.add_argument(
        "--no-send",
        action="store_true",
        dest="no_send",
        help="Synthesise but print to stdout instead of delivering",
    )
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="subcommand")
    sub.add_parser("morning", help="0600 morning briefing")
    sub.add_parser("nightly", help="2100 evening recap")
    sub.add_parser("diary", help="Dear Diary — autonomous reflection entry")
    sub.add_parser("nightctl", help="0545 overnight agent-job summary")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(4)

    dispatch = {
        "morning": cmd_morning,
        "nightly": cmd_nightly,
        "diary": cmd_diary,
        "nightctl": cmd_nightctl,
    }

    sys.exit(dispatch[args.subcommand](args, cfg) or 0)
