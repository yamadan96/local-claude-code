"""Path normalization helpers."""

from __future__ import annotations

from pathlib import Path


def normalize_path(path: str, root: Path) -> Path:
    """Normalize a path relative to a root directory.

    Handles ~, relative paths, and absolute paths.
    """
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = root / p
    return p.resolve()
