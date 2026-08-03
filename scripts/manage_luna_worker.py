from __future__ import annotations

import difflib
import os
import shutil
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FIELDS = ("name", "description", "developer_instructions")
PINNED_VALUES = {
    "name": "luna_worker",
    "model": "gpt-5.6-luna",
    "model_reasoning_effort": "max",
}


class AgentConfigError(ValueError):
    """Raised when the desired agent configuration is invalid."""


class ExistingAgentError(FileExistsError):
    """Raised when installation would overwrite an existing agent."""


def validate_agent_text(text: str) -> tuple[str, ...]:
    """Return all TOML schema and pinned-value errors without writing files."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return (f"Invalid TOML: {error}",)

    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Missing or empty required field: {field}")
    for field, expected in PINNED_VALUES.items():
        actual = data.get(field)
        if actual != expected:
            errors.append(f"{field} must be {expected!r}; got {actual!r}")
    return tuple(errors)


def render_diff(current: str | None, desired: str, target: Path) -> str:
    """Return a unified diff from current content to desired content."""
    current_lines = [] if current is None else current.splitlines()
    desired_lines = desired.splitlines()
    lines = list(
        difflib.unified_diff(
            current_lines,
            desired_lines,
            fromfile="/dev/null" if current is None else str(target),
            tofile=str(target),
            lineterm="",
        )
    )
    return "\n".join(lines) + ("\n" if lines else "")


def install_agent(
    desired: str,
    target: Path,
    *,
    replace: bool = False,
    timestamp: str | None = None,
) -> Path | None:
    """Validate and atomically install desired, returning a backup path if made."""
    errors = validate_agent_text(desired)
    if errors:
        raise AgentConfigError("; ".join(errors))
    if target.exists() and not replace:
        raise ExistingAgentError(f"Refusing to replace existing agent: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if target.exists():
        stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = Path(f"{target}.bak-{stamp}")
        shutil.copy2(target, backup)

    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=target.parent,
        prefix=f".{target.name}.",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(desired)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return backup
