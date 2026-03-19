"""
halyt.transcript — YouTube transcript fetcher.

Pure Python, no external dependencies. Fetches transcripts via
YouTube's internal timedtext API, same mechanism as youtube-transcript-api.
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional


# Mimic a real browser to avoid consent redirects
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_CONSENT_COOKIE = "CONSENT=YES+cb; SOCS=CAESEwgDEgk0ODE3Nzk3MjMaAmVuIAEaBgiA_LyaBg"


@dataclass
class TranscriptSegment:
    start: float
    duration: float
    text: str


@dataclass
class Transcript:
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    segments: list[TranscriptSegment] = field(default_factory=list)

    def to_text(self, include_timestamps: bool = False) -> str:
        """Return plain text of transcript."""
        parts = []
        for seg in self.segments:
            text = seg.text.strip()
            if not text:
                continue
            if include_timestamps:
                minutes = int(seg.start // 60)
                seconds = int(seg.start % 60)
                parts.append(f"[{minutes:02d}:{seconds:02d}] {text}")
            else:
                parts.append(text)
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "language": self.language,
            "language_code": self.language_code,
            "is_generated": self.is_generated,
            "segments": [
                {"start": s.start, "duration": s.duration, "text": s.text}
                for s in self.segments
            ],
        }


class TranscriptError(Exception):
    pass


class NoTranscriptAvailable(TranscriptError):
    pass


class VideoUnavailable(TranscriptError):
    pass


def _extract_video_id(url_or_id: str) -> str:
    """Extract video ID from URL or return as-is if already an ID."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        m = re.search(pattern, url_or_id)
        if m:
            return m.group(1)
    raise TranscriptError(f"Could not extract video ID from: {url_or_id}")


def _fetch_url(url: str, extra_headers: Optional[dict] = None) -> str:
    """Fetch URL with browser-like headers."""
    headers = dict(_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise TranscriptError(f"HTTP {e.code} fetching {url}") from e
    except urllib.error.URLError as e:
        raise TranscriptError(f"URL error fetching {url}: {e.reason}") from e


def _fetch_with_consent(url: str) -> str:
    """Fetch YouTube page, bypassing consent gate with cookie."""
    return _fetch_url(url, extra_headers={"Cookie": _CONSENT_COOKIE})


def _extract_captions_data(html: str, video_id: str) -> list[dict]:
    """Extract captionTracks from ytInitialPlayerResponse in page HTML."""
    # Try to find ytInitialPlayerResponse JSON
    patterns = [
        r"ytInitialPlayerResponse\s*=\s*({.+?})\s*;",
        r"var ytInitialPlayerResponse = ({.+?});",
    ]
    for pattern in patterns:
        m = re.search(pattern, html, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                tracks = (
                    data.get("captions", {})
                    .get("playerCaptionsTracklistRenderer", {})
                    .get("captionTracks", [])
                )
                if tracks:
                    return tracks
            except json.JSONDecodeError:
                continue

    # Check for unavailable/age-gated video
    if '"playabilityStatus":{"status":"ERROR"' in html:
        raise VideoUnavailable(f"Video {video_id} is unavailable")
    if "LOGIN_REQUIRED" in html or "Sign in" in html[:2000]:
        raise VideoUnavailable(f"Video {video_id} requires sign-in")

    return []


def _parse_xml_transcript(xml_text: str) -> list[TranscriptSegment]:
    """Parse YouTube's XML transcript format."""
    segments = []
    try:
        root = ET.fromstring(xml_text)
        for text_el in root.findall(".//text"):
            start = float(text_el.get("start", 0))
            duration = float(text_el.get("dur", 0))
            raw = text_el.text or ""
            # Decode common HTML entities
            raw = (
                raw.replace("&amp;", "&")
                   .replace("&lt;", "<")
                   .replace("&gt;", ">")
                   .replace("&quot;", '"')
                   .replace("&#39;", "'")
                   .replace("\n", " ")
            )
            # Strip XML-style formatting tags
            raw = re.sub(r"<[^>]+>", "", raw).strip()
            if raw:
                segments.append(TranscriptSegment(start=start, duration=duration, text=raw))
    except ET.ParseError as e:
        raise TranscriptError(f"XML parse error: {e}") from e
    return segments


def list_available(video_id: str) -> list[dict]:
    """Return list of available transcript tracks for a video."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    html = _fetch_with_consent(url)
    tracks = _extract_captions_data(html, video_id)
    return [
        {
            "language": t.get("name", {}).get("simpleText", "Unknown"),
            "language_code": t.get("languageCode", ""),
            "is_generated": "asr" in t.get("kind", ""),
            "url": t.get("baseUrl", ""),
        }
        for t in tracks
    ]


def fetch(
    url_or_id: str,
    language_codes: Optional[list[str]] = None,
    preserve_formatting: bool = False,
) -> Transcript:
    """
    Fetch transcript for a YouTube video.

    Args:
        url_or_id: YouTube URL or 11-character video ID
        language_codes: Preferred language codes in priority order (default: ['en'])
        preserve_formatting: If True, keep XML formatting tags

    Returns:
        Transcript object

    Raises:
        NoTranscriptAvailable: No captions found
        VideoUnavailable: Video cannot be accessed
        TranscriptError: Other fetch/parse errors
    """
    if language_codes is None:
        language_codes = ["en", "en-US", "en-GB"]

    video_id = _extract_video_id(url_or_id)
    page_url = f"https://www.youtube.com/watch?v={video_id}"
    html = _fetch_with_consent(page_url)
    tracks = _extract_captions_data(html, video_id)

    if not tracks:
        raise NoTranscriptAvailable(
            f"No transcript available for video {video_id}. "
            "The video may not have captions, or they may be disabled."
        )

    # Select best track: prefer requested language, then any manual, then generated
    selected = None

    # First pass: exact language match
    for code in language_codes:
        for track in tracks:
            if track.get("languageCode", "").lower() == code.lower():
                selected = track
                break
        if selected:
            break

    # Second pass: prefix match (e.g. 'en' matches 'en-US')
    if not selected:
        for code in language_codes:
            for track in tracks:
                if track.get("languageCode", "").lower().startswith(code.lower()):
                    selected = track
                    break
            if selected:
                break

    # Fallback: first available track
    if not selected:
        selected = tracks[0]

    track_url = selected.get("baseUrl", "")
    if not track_url:
        raise TranscriptError(f"No URL found for transcript track: {selected}")

    xml_text = _fetch_url(track_url)
    segments = _parse_xml_transcript(xml_text)

    return Transcript(
        video_id=video_id,
        language=selected.get("name", {}).get("simpleText", "Unknown"),
        language_code=selected.get("languageCode", ""),
        is_generated="asr" in selected.get("kind", ""),
        segments=segments,
    )
