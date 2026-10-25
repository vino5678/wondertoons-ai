"""Path safety helpers (stdlib only)."""
from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from app.core.errors import InvalidInputError

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def validate_relative_path(value: str, allowed_extensions: set | None = None) -> str:
    """Return a normalised, forward-slash relative path or raise InvalidInputError.
    Rejects absolute paths, drive letters, '..' segments and control characters."""
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError("Path must be a non-empty string.")
    if len(value) > 260 or any(ord(c) < 32 for c in value):
        raise InvalidInputError("Path is too long or contains control characters.")
    unified = value.replace("\\", "/")
    win = PureWindowsPath(value)
    if win.drive or win.root or PurePosixPath(unified).is_absolute() or unified.startswith("//"):
        raise InvalidInputError("Absolute paths are not allowed; use a path relative to the data folder.")
    parts = [p for p in PurePosixPath(unified).parts if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        raise InvalidInputError("Path must not contain '..' segments.")
    normalised = "/".join(parts)
    if allowed_extensions is not None and PurePosixPath(normalised).suffix.lower() not in allowed_extensions:
        raise InvalidInputError(f"File extension must be one of: {', '.join(sorted(allowed_extensions))}.")
    return normalised


def safe_join(base: Path, relative: str) -> Path:
    """Join and verify the result stays inside base (resolves symlinks)."""
    rel = validate_relative_path(relative)
    base_resolved = base.resolve()
    target = (base_resolved / rel).resolve()
    if target != base_resolved and base_resolved not in target.parents:
        raise InvalidInputError("Path escapes the allowed directory.")
    return target
