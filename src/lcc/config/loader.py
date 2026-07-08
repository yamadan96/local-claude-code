"""Multi-source config merging: defaults -> global TOML -> project TOML -> env -> CLI."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from lcc.config.models import AppConfig, PermissionMode

# Mapping from env-var name to AppConfig field name
_ENV_MAP: dict[str, str] = {
    "LCC_MODEL": "model",
    "LCC_BASE_URL": "base_url",
    "LCC_API_KEY": "api_key",
    "LCC_PERMISSION_MODE": "permission_mode",
    "LCC_MAX_INPUT_TOKENS": "max_input_tokens",
}

# Fields that should be parsed as integers
_INT_FIELDS: set[str] = {
    "max_input_tokens",
    "max_output_tokens",
    "tool_timeout_seconds",
}

# Fields that should be parsed as booleans
_BOOL_FIELDS: set[str] = {"allow_outside_cwd"}


def _read_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file and return its contents, or empty dict if not found."""
    if not path.is_file():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _merge_toml(base: dict[str, Any], toml_data: dict[str, Any]) -> dict[str, Any]:
    """Merge TOML data into base dict (flat keys only)."""
    for key, value in toml_data.items():
        if isinstance(value, dict):
            continue  # Skip nested tables for v1
        base[key] = value
    return base


def _merge_env(base: dict[str, Any]) -> dict[str, Any]:
    """Merge environment variables into base dict."""
    for env_name, field_name in _ENV_MAP.items():
        value = os.environ.get(env_name)
        if value is not None:
            base[field_name] = value
    return base


def _coerce_value(key: str, value: Any) -> Any:
    """Coerce string values to the correct type for AppConfig fields."""
    if key in _INT_FIELDS and isinstance(value, str):
        return int(value)
    if key in _BOOL_FIELDS and isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    if key == "permission_mode" and isinstance(value, str):
        return PermissionMode(value)
    return value


def load_config(
    cli_overrides: dict[str, Any] | None = None,
    cwd: str | None = None,
) -> AppConfig:
    """Load config with full precedence chain.

    Precedence (lowest to highest):
    1. Built-in defaults (AppConfig defaults)
    2. ~/.lcc/config.toml (global)
    3. .lcc.toml in project dir (project-specific)
    4. Environment variables
    5. CLI flags (cli_overrides)
    """
    merged: dict[str, Any] = {}

    # Global config
    global_path = Path.home() / ".lcc" / "config.toml"
    _merge_toml(merged, _read_toml(global_path))

    # Project config
    project_dir = Path(cwd) if cwd else Path.cwd()
    project_path = project_dir / ".lcc.toml"
    _merge_toml(merged, _read_toml(project_path))

    # Environment variables
    _merge_env(merged)

    # CLI overrides
    if cli_overrides:
        for key, value in cli_overrides.items():
            if value is not None:
                merged[key] = value

    # Coerce types
    coerced: dict[str, Any] = {}
    valid_fields = {f.name for f in AppConfig.__dataclass_fields__.values()}
    for key, value in merged.items():
        if key in valid_fields:
            coerced[key] = _coerce_value(key, value)

    # Set cwd
    if cwd:
        coerced["cwd"] = cwd
    elif "cwd" not in coerced or not coerced["cwd"]:
        coerced["cwd"] = str(Path.cwd())

    return AppConfig(**coerced)
