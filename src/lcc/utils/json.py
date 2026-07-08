"""Lenient JSON parsing helpers."""

from __future__ import annotations

import json
from typing import Any

from lcc.agent.recovery import recover_tool_call_json


def lenient_json_loads(text: str) -> Any:
    """Parse JSON leniently, attempting recovery on failure.

    Tries standard json.loads first, then falls back to
    recovery strategies for malformed JSON.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    recovered = recover_tool_call_json(text)
    if recovered is not None:
        return recovered

    raise json.JSONDecodeError("Failed to parse JSON even with recovery", text, 0)
