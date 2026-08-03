from __future__ import annotations

import argparse
import difflib
import os
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
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


class TargetAccessError(OSError):
    """Raised when the selected target cannot be accessed safely."""


class BackupExistsError(FileExistsError):
    """Raised when installation would overwrite an existing backup."""


EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_ENVIRONMENT = 2


@dataclass(frozen=True)
class EnvironmentReport:
    version: str | None
    multi_agent_enabled: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class TargetSnapshot:
    text: str
    stat_result: os.stat_result


def parse_codex_version(output: str) -> str | None:
    """Extract the semantic version from `codex-cli X.Y.Z`."""
    match = re.search(r"\bcodex-cli\s+(\d+\.\d+\.\d+)\b", output)
    return match.group(1) if match else None


def multi_agent_is_enabled(output: str) -> bool:
    """Return true only for a multi_agent feature row ending in true."""
    for line in output.splitlines():
        fields = line.split()
        if fields and fields[0] == "multi_agent":
            return fields[-1].lower() == "true"
    return False


def run_environment_check(codex_bin: str = "codex") -> EnvironmentReport:
    """Run version and feature checks without changing Codex configuration."""
    errors: list[str] = []
    try:
        version_run = subprocess.run(
            [codex_bin, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        return EnvironmentReport(None, False, (f"Cannot run {codex_bin}: {error}",))

    version_output = version_run.stdout + version_run.stderr
    version = parse_codex_version(version_output)
    if version_run.returncode != 0 or version is None:
        errors.append("Unable to identify the installed Codex CLI version")

    try:
        feature_run = subprocess.run(
            [codex_bin, "features", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        errors.append(f"Cannot run {codex_bin} features list: {error}")
        return EnvironmentReport(version, False, tuple(errors))
    enabled = feature_run.returncode == 0 and multi_agent_is_enabled(
        feature_run.stdout + feature_run.stderr
    )
    if not enabled:
        errors.append("Codex multi_agent feature is unavailable or disabled")
    return EnvironmentReport(version, enabled, tuple(errors))


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
    current_lines = [] if current is None else current.splitlines(keepends=True)
    desired_lines = desired.splitlines(keepends=True)
    lines = list(
        difflib.unified_diff(
            current_lines,
            desired_lines,
            fromfile="/dev/null" if current is None else str(target),
            tofile=str(target),
            lineterm="\n",
        )
    )
    output: list[str] = []
    for line in lines:
        output.append(line)
        if not line.endswith(("\n", "\r")):
            output.append("\n\\ No newline at end of file\n")
    return "".join(output)


def _resolved_path(path: Path) -> Path:
    try:
        return path.expanduser().resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise TargetAccessError(f"Cannot resolve target {path}: {error}") from error


def _ensure_allowed_target(target: Path) -> None:
    resolved_target = _resolved_path(target)
    protected = _resolved_path(Path.home() / ".codex" / "config.toml")
    if resolved_target == protected:
        raise TargetAccessError(
            f"Refusing protected Codex config target: {target}"
        )
    try:
        if target.exists() and protected.exists() and target.samefile(protected):
            raise TargetAccessError(
                f"Refusing protected Codex config target: {target}"
            )
    except TargetAccessError:
        raise
    except OSError as error:
        raise TargetAccessError(f"Cannot resolve target {target}: {error}") from error


def _read_target(target: Path) -> TargetSnapshot | None:
    """Read one regular, non-symlink target without newline conversion."""
    _ensure_allowed_target(target)
    try:
        initial_stat = target.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise TargetAccessError(f"Cannot read target {target}: {error}") from error

    if stat.S_ISLNK(initial_stat.st_mode):
        raise TargetAccessError(
            f"Cannot read target {target}: refusing symlink target"
        )
    if not stat.S_ISREG(initial_stat.st_mode):
        raise TargetAccessError(
            f"Cannot read target {target}: target is not a regular file"
        )

    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(target, flags)
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise TargetAccessError(
                f"Cannot read target {target}: target is not a regular file"
            )
        if not os.path.samestat(initial_stat, opened_stat):
            raise TargetAccessError(
                f"Cannot read target {target}: target changed while opening"
            )
        with os.fdopen(
            descriptor,
            mode="r",
            encoding="utf-8",
            newline="",
        ) as handle:
            descriptor = -1
            text = handle.read()
        return TargetSnapshot(text, opened_stat)
    except TargetAccessError:
        raise
    except (OSError, UnicodeError) as error:
        raise TargetAccessError(f"Cannot read target {target}: {error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _target_matches_snapshot(target: Path, snapshot: TargetSnapshot) -> bool:
    try:
        current_stat = target.lstat()
    except OSError as error:
        raise TargetAccessError(
            f"Cannot replace target {target}: {error}"
        ) from error
    if stat.S_ISLNK(current_stat.st_mode):
        raise TargetAccessError(
            f"Cannot replace target {target}: refusing symlink target"
        )
    expected = snapshot.stat_result
    return (
        os.path.samestat(current_stat, expected)
        and current_stat.st_mode == expected.st_mode
        and current_stat.st_size == expected.st_size
        and current_stat.st_mtime_ns == expected.st_mtime_ns
    )


def _create_backup(
    target: Path,
    snapshot: TargetSnapshot,
    timestamp: str | None,
) -> Path:
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = Path(f"{target}.bak-{stamp}")
    descriptor = -1
    created = False
    try:
        descriptor = os.open(
            backup,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            stat.S_IMODE(snapshot.stat_result.st_mode),
        )
        created = True
        with os.fdopen(
            descriptor,
            mode="w",
            encoding="utf-8",
            newline="",
        ) as handle:
            descriptor = -1
            handle.write(snapshot.text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(backup, stat.S_IMODE(snapshot.stat_result.st_mode))
        os.utime(
            backup,
            ns=(
                snapshot.stat_result.st_atime_ns,
                snapshot.stat_result.st_mtime_ns,
            ),
        )
    except FileExistsError as error:
        raise BackupExistsError(
            f"Backup already exists; refusing to overwrite: {backup}"
        ) from error
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        if created:
            backup.unlink(missing_ok=True)
        raise
    return backup


def install_agent(
    desired: str,
    target: Path,
    *,
    replace: bool = False,
    timestamp: str | None = None,
) -> Path | None:
    """Validate and atomically install desired, returning a backup path if made."""
    _ensure_allowed_target(target)
    errors = validate_agent_text(desired)
    if errors:
        raise AgentConfigError("; ".join(errors))
    snapshot = _read_target(target)
    if snapshot is not None and not replace:
        raise ExistingAgentError(f"Refusing to replace existing agent: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None

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
        _ensure_allowed_target(target)
        if snapshot is None:
            try:
                os.link(temporary, target, follow_symlinks=False)
            except FileExistsError as error:
                raise ExistingAgentError(
                    f"Refusing to replace target created during install: {target}"
                ) from error
        else:
            if not _target_matches_snapshot(target, snapshot):
                raise TargetAccessError(
                    f"Cannot replace target {target}: target changed during install"
                )
            backup = _create_backup(target, snapshot, timestamp)
            if not _target_matches_snapshot(target, snapshot):
                raise TargetAccessError(
                    f"Cannot replace target {target}: target changed during install"
                )
            os.replace(temporary, target)
        temporary.unlink(missing_ok=True)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return backup


def _default_template() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "luna-worker.toml"


def _default_target() -> Path:
    return Path.home() / ".codex" / "agents" / "luna-worker.toml"


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--template", type=Path, default=_default_template())
    parser.add_argument("--target", type=Path, default=_default_target())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the Lunaria Luna worker")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "verify"):
        command = commands.add_parser(name)
        _add_common_arguments(command)
        command.add_argument("--codex-bin", default="codex")
    plan = commands.add_parser("plan")
    _add_common_arguments(plan)
    install = commands.add_parser("install")
    _add_common_arguments(install)
    install.add_argument("--replace", action="store_true")
    return parser


def _read_desired(template: Path) -> str:
    desired = template.read_text(encoding="utf-8")
    errors = validate_agent_text(desired)
    if errors:
        raise AgentConfigError("; ".join(errors))
    return desired


def _installed_errors(
    target: Path,
    desired: str,
    snapshot: TargetSnapshot | None,
) -> tuple[str, ...]:
    if snapshot is None:
        return (f"Agent is missing: {target}",)
    installed = snapshot.text
    errors = list(validate_agent_text(installed))
    if installed != desired:
        errors.append(f"Installed agent differs from template: {target}")
    return tuple(errors)


def main(argv: list[str] | None = None) -> int:
    """Run check, plan, install, or verify and return a stable exit code."""
    args = build_parser().parse_args(argv)
    try:
        _ensure_allowed_target(args.target)
        desired = _read_desired(args.template)
        snapshot = _read_target(args.target)
    except (OSError, UnicodeError, AgentConfigError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ENVIRONMENT

    if args.command == "plan":
        current = None if snapshot is None else snapshot.text
        print(f"Target: {args.target}")
        print(render_diff(current, desired, args.target), end="")
        return EXIT_OK

    if args.command == "install":
        current = None if snapshot is None else snapshot.text
        print(render_diff(current, desired, args.target), end="")
        try:
            backup = install_agent(desired, args.target, replace=args.replace)
        except ExistingAgentError as error:
            print(f"error: {error}", file=sys.stderr)
            return EXIT_DRIFT
        except (OSError, AgentConfigError) as error:
            print(f"error: {error}", file=sys.stderr)
            return EXIT_ENVIRONMENT
        print(f"Installed: {args.target}")
        if backup is not None:
            print(f"Backup: {backup}")
        print(
            "If this task has not refreshed custom-agent discovery, "
            "start a new Codex task."
        )
        return EXIT_OK

    report = run_environment_check(args.codex_bin)
    drift = _installed_errors(args.target, desired, snapshot)
    if report.version is not None:
        print(f"Codex CLI: {report.version}")
    for error in report.errors + drift:
        print(f"error: {error}", file=sys.stderr)
    if report.errors:
        return EXIT_ENVIRONMENT
    if drift:
        return EXIT_DRIFT
    print(f"Valid luna_worker: {args.target}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
