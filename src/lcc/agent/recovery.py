"""Malformed tool-call JSON recovery for weak local models."""

from __future__ import annotations

import json
import re
from typing import Any


def recover_tool_call_json(raw: str) -> dict[str, Any] | None:
    """Attempt to recover a valid JSON dict from malformed tool-call output.

    Strategies applied in order:
    1. Strip markdown code fences (```json ... ```)
    2. Extract the first { ... } block (greedy balanced braces)
    3. Attempt json.loads on the extracted text
    4. If result has '_raw' key (arguments-as-string), try to parse that

    Returns the parsed dict, or None if all recovery attempts fail.
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Strategy 1: Strip markdown fences
    text = _strip_markdown_fences(text)

    # Strategy 2: Extract first {...} block
    extracted = _extract_first_json_object(text)
    if extracted is None:
        return None

    # Strategy 3: Parse
    try:
        result = json.loads(extracted)
        if isinstance(result, dict):
            # Strategy 4: Handle arguments-as-string
            if "_raw" in result:
                inner = recover_tool_call_json(result["_raw"])
                if inner is not None:
                    return inner
            return result
    except json.JSONDecodeError:
        pass

    # Try with minor fixes (trailing commas, single quotes)
    fixed = _fix_common_json_errors(extracted)
    try:
        result = json.loads(fixed)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    return None


def fuzzy_match_tool_name(
    candidate: str,
    known_names: list[str],
    max_distance: int = 3,
) -> str | None:
    """Find the closest matching tool name using Levenshtein distance.

    Returns the matched name if distance < max_distance, else None.
    """
    if not candidate or not known_names:
        return None

    candidate_lower = candidate.lower().strip()

    # Exact match (case-insensitive)
    for name in known_names:
        if name.lower() == candidate_lower:
            return name

    # Levenshtein distance
    best_name: str | None = None
    best_distance = max_distance

    for name in known_names:
        dist = _levenshtein(candidate_lower, name.lower())
        if dist < best_distance:
            best_distance = dist
            best_name = name

    return best_name


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from text."""
    # Match ```json ... ``` or ``` ... ```
    pattern = r"```(?:json|JSON)?\s*\n?(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _extract_first_json_object(text: str) -> str | None:
    """Extract the first balanced {...} block from text."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        char = text[i]
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _fix_common_json_errors(text: str) -> str:
    """Attempt to fix common JSON syntax errors."""
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Replace single quotes with double quotes (simple heuristic)
    if "'" in text and '"' not in text:
        text = text.replace("'", '"')
    return text


def _levenshtein(s1: str, s2: str) -> int:
    """Compute the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]
