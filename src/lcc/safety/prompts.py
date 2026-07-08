"""User-facing permission prompt formatting."""

from __future__ import annotations

from lcc.safety.permissions import PermissionRequest


def format_permission_prompt(request: PermissionRequest) -> str:
    """Format a permission request into a human-readable prompt string."""
    parts = [f"[permission] {request.tool_name}"]
    if request.arguments_summary:
        parts.append(f": {request.arguments_summary}")
    elif request.description:
        parts.append(f": {request.description}")
    return "".join(parts)
