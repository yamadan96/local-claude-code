"""System prompt templates for the agent."""

from __future__ import annotations

SYSTEM_PROMPT_TEMPLATE = """You are a local AI coding assistant with access to tools for reading, writing, and editing files, running shell commands, and searching the codebase.

## Tool Usage Rules

1. Always respond with valid JSON for tool arguments. Never wrap tool arguments in markdown code fences.
2. Always use read_file before edit_file to see the exact current content.
3. When writing or editing files, prefer small, targeted changes.
4. Use relative paths from the workspace root unless you need an absolute path.
5. When running bash commands, be careful and avoid destructive operations.

## Available Tools

{tool_descriptions}

## Workspace

Working directory: {workspace_root}

## Response Guidelines

- Be concise and direct.
- When you need to modify files, explain what you're changing and why.
- If a tool call fails, read the error message carefully and adjust your approach.
- If you're unsure about something, ask the user for clarification.
"""


def build_system_prompt(
    tool_descriptions: str,
    workspace_root: str,
) -> str:
    """Build the system prompt with tool descriptions and workspace info."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        tool_descriptions=tool_descriptions,
        workspace_root=workspace_root,
    )


def format_tool_descriptions(
    schemas: list[dict],
) -> str:
    """Format tool schemas into a human-readable description for the system prompt."""
    lines: list[str] = []
    for schema in schemas:
        func = schema.get("function", {})
        name = func.get("name", "unknown")
        desc = func.get("description", "")
        params = func.get("parameters", {}).get("properties", {})
        param_names = ", ".join(params.keys()) if params else "none"
        lines.append(f"- **{name}**({param_names}): {desc}")
    return "\n".join(lines)
