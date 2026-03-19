"""halyt CLI — YouTube transcript fetcher for halOS."""

import argparse
import json
import sys

from .transcript import fetch, list_available, TranscriptError, NoTranscriptAvailable, VideoUnavailable


def cmd_get(args) -> int:
    try:
        transcript = fetch(
            args.video,
            language_codes=args.lang,
        )
    except VideoUnavailable as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except NoTranscriptAvailable as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    except TranscriptError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(transcript.to_dict(), indent=2))
    else:
        if not args.no_header:
            gen_flag = " [auto-generated]" if transcript.is_generated else ""
            print(f"# {transcript.video_id} — {transcript.language}{gen_flag}\n")
        print(transcript.to_text(include_timestamps=args.timestamps))

    return 0


def cmd_list(args) -> int:
    try:
        tracks = list_available(args.video)
    except TranscriptError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if not tracks:
        print("no transcripts available")
        return 3

    if args.json:
        print(json.dumps(tracks, indent=2))
    else:
        print(f"{'code':<10}  {'generated':<10}  language")
        print(f"{'─'*10}  {'─'*10}  {'─'*30}")
        for t in tracks:
            gen = "auto" if t["is_generated"] else "manual"
            print(f"{t['language_code']:<10}  {gen:<10}  {t['language']}")

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="halyt",
        description="halyt — YouTube transcript fetcher (halOS module)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    sub = parser.add_subparsers(dest="subcommand")

    # get
    p_get = sub.add_parser("get", help="Fetch transcript for a video")
    p_get.add_argument("video", help="YouTube URL or video ID")
    p_get.add_argument(
        "--lang", nargs="+", default=["en", "en-US", "en-GB"],
        metavar="CODE", help="Language codes in priority order (default: en)"
    )
    p_get.add_argument("--timestamps", action="store_true", help="Include timestamps")
    p_get.add_argument("--no-header", action="store_true", help="Suppress header line")

    # list
    p_list = sub.add_parser("list", help="List available transcripts for a video")
    p_list.add_argument("video", help="YouTube URL or video ID")

    args = parser.parse_args(argv)

    if args.subcommand == "get":
        return cmd_get(args)
    elif args.subcommand == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
