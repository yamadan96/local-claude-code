"""Application configuration dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field

# Single source of truth for the enum; re-exported here for config users
from lcc.safety.permissions import PermissionMode

__all__ = ["AppConfig", "PermissionMode"]

DEFAULT_MODEL = "qwen2.5-coder:14b"
DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MAX_INPUT_TOKENS = 16000
DEFAULT_MAX_OUTPUT_TOKENS = 2000
DEFAULT_TOOL_TIMEOUT_SECONDS = 30


@dataclass
class AppConfig:
    """Central application configuration."""

    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    permission_mode: PermissionMode = PermissionMode.ASK
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    tool_timeout_seconds: int = DEFAULT_TOOL_TIMEOUT_SECONDS
    allow_outside_cwd: bool = False
    cwd: str = field(default="")
