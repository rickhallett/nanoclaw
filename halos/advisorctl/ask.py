"""Live query to an advisor via the Hermes HTTP API.

Sends an OpenAI-compatible chat completion request to the advisor's
gateway API server and streams the response to stdout.
"""

from __future__ import annotations

import json
import sys
from typing import Iterator

import httpx

from .config import resolve_url


def ask(
    advisor: str,
    prompt: str,
    *,
    url_override: str | None = None,
    session_id: str | None = None,
    system: str | None = None,
    stream: bool = True,
    timeout: float = 120.0,
) -> str:
    """Send a prompt to the advisor and return the full response text.

    When stream=True (default), tokens are printed to stdout as they arrive.
    Returns the accumulated response either way.
    """
    base_url = resolve_url(advisor, url_override)
    endpoint = f"{base_url}/v1/chat/completions"

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = {
        "messages": messages,
        "stream": stream,
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if session_id:
        headers["X-Hermes-Session-Id"] = session_id

    if stream:
        return _stream_response(endpoint, body, headers, timeout)
    else:
        return _blocking_response(endpoint, body, headers, timeout)


def _stream_response(
    endpoint: str,
    body: dict,
    headers: dict[str, str],
    timeout: float,
) -> str:
    """SSE streaming — print tokens as they arrive, return accumulated text."""
    chunks: list[str] = []

    with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        with client.stream("POST", endpoint, json=body, headers=headers) as resp:
            resp.raise_for_status()
            for chunk in _parse_sse(resp.iter_lines()):
                chunks.append(chunk)
                sys.stdout.write(chunk)
                sys.stdout.flush()

    # Newline after streamed output
    if chunks:
        sys.stdout.write("\n")
        sys.stdout.flush()

    return "".join(chunks)


def _blocking_response(
    endpoint: str,
    body: dict,
    headers: dict[str, str],
    timeout: float,
) -> str:
    """Non-streaming — wait for full response."""
    with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        resp = client.post(endpoint, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "")


def _parse_sse(lines: Iterator[str]) -> Iterator[str]:
    """Parse OpenAI-format SSE stream, yielding content deltas."""
    for line in lines:
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload.strip() == "[DONE]":
            return
        try:
            obj = json.loads(payload)
            delta = obj.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content")
            if content:
                yield content
        except (json.JSONDecodeError, IndexError, KeyError):
            continue
