"""Anthropic API client wrapper with streaming, error handling, and model routing."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError

# Load .env from project root (walk up from this file)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# Model configuration
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-20250514"


def get_client() -> Anthropic:
    """Get an Anthropic client, checking for API key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Export it: export ANTHROPIC_API_KEY=sk-..."
        )
    return Anthropic(api_key=api_key)


def call_haiku(
    system: str,
    user_message: str,
    max_tokens: int = 2048,
) -> str:
    """Call Haiku for fast triage. Non-streaming (triage should be quick).

    Returns the text response or raises on failure.
    """
    client = get_client()
    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except RateLimitError:
        raise RuntimeError("Rate limited by Anthropic API. Wait a moment and retry.")
    except APIConnectionError:
        raise RuntimeError("Cannot connect to Anthropic API. Check your network.")
    except APIError as e:
        raise RuntimeError(f"Anthropic API error: {e.message}")


def stream_sonnet(
    system: str,
    user_message: str,
    max_tokens: int = 4096,
):
    """Stream a response from Sonnet for deep reasoning.

    Yields text chunks as they arrive. This is the main output the user sees.
    """
    client = get_client()
    try:
        with client.messages.stream(
            model=SONNET_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except RateLimitError:
        yield "\n\n[ERROR] Rate limited by Anthropic API. Wait a moment and retry."
    except APIConnectionError:
        yield "\n\n[ERROR] Cannot connect to Anthropic API. Check your network."
    except APIError as e:
        yield f"\n\n[ERROR] Anthropic API error: {e.message}"
