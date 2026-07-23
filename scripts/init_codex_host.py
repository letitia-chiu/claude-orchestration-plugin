#!/usr/bin/env python3
"""Install the Codex-host adapter into one explicit target Git repository.

The materializer is intentionally narrow:

- its canonical source root is derived from this file, never from the shell CWD;
- it owns one fixed target inventory;
- it preflights every source and destination before writing anything;
- missing files are copied byte-for-byte;
- identical files are left untouched;
- any conflict fails closed with zero writes;
- check mode is read-only;
- it performs no provider, network, Git-write, hook, or global-config action.

Standard library only.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


EXIT_OK = 0
EXIT_NOT_INSTALLED = 2
EXIT_CONFLICT = 3
EXIT_CONFIGURATION_ERROR = 4

MISSING = "MISSING"
IDENTICAL = "IDENTICAL"
CONFLICT = "CONFLICT"

INVENTORY = (
    "AGENTS.md",
    ".codex/agents/worker.toml",
    ".codex/agents/executor.toml",
    ".agents/skills/orchestration-codex-host/SKILL.md",
    ".agents/skills/orchestration-codex-host/references/kickoff.md",
    ".agents/skills/orchestration-codex-host/references/go.md",
    ".agents/skills/orchestration-codex-host/references/dispatch.md",
    ".agents/skills/orchestration-codex-host/references/wrapup.md",
    "docs/playbook/README.md",
    "docs/playbook/orchestration.md",
    "docs/playbook/task-routing.md",
    "docs/playbook/agent-routing.json",
    "docs/playbook/codex-host.md",
    "examples/schemas/orchestration-result.schema.json",
    "examples/task-packets/active-host-feasibility.md",
    "examples/task-packets/active-host-implementation.md",
    "examples/task-packets/claude-adversarial-review.md",
    "examples/task-packets/codex-host-gate.md",
    "examples/task-packets/headless-codex-implementation.md",
    "scripts/orchestration_agent.py",
)

GIT_READ_ONLY_ARGS = ("rev-parse", "--show-toplevel")


class ConfigurationError(Exception):
    """An invalid source, target, inventory, or filesystem boundary."""


@dataclass(frozen=True)
class InventoryItem:
    relative_path: str
    source_path: Path
    target_path: Path
    source_bytes: bytes
    state: str


def plugin_root() -> Path:
    """Return the checkout/installation root containing this script."""
    return Path(__file__).resolve().parent.parent


def _relative_parts(relative_path: str) -> tuple[str, ...]:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or not path.parts:
        raise ConfigurationError("inventory path must be non-empty and relative: %r" % relative_path)
    if any(part in ("", ".", "..") for part in path.parts):
        raise ConfigurationError("inventory path contains an unsafe component: %r" % relative_path)
    if path.parts[0] == ".git":
        raise ConfigurationError("inventory must never target .git: %r" % relative_path)
    return path.parts


def _load_sources(source_root: Path) -> dict[str, tuple[Path, bytes]]:
    try:
        root = source_root.resolve(strict=True)
    except OSError as exc:
        raise ConfigurationError("source root is unavailable: %s" % exc) from exc
    if not root.is_dir():
        raise ConfigurationError("source root is not a directory: %s" % root)

    sources: dict[str, tuple[Path, bytes]] = {}
    for relative_path in INVENTORY:
        parts = _relative_parts(relative_path)
        source_path = root.joinpath(*parts)
        if source_path.is_symlink():
            raise ConfigurationError("canonical source must not be a symlink: %s" % source_path)
        try:
            resolved_source = source_path.resolve(strict=True)
        except OSError as exc:
            raise ConfigurationError(
                "required canonical source is missing: %s" % source_path
            ) from exc
        try:
            resolved_source.relative_to(root)
        except ValueError as exc:
            raise ConfigurationError(
                "canonical source escapes plugin root: %s" % source_path
            ) from exc
        if not resolved_source.is_file():
            raise ConfigurationError("canonical source is not a file: %s" % source_path)
        sources[relative_path] = (resolved_source, resolved_source.read_bytes())
    return sources


def _validate_target(target_arg: str) -> Path:
    candidate = Path(target_arg)
    if not candidate.is_absolute():
        raise ConfigurationError("target must be an absolute path")
    if any(part == ".." for part in candidate.parts):
        raise ConfigurationError("target path must not contain '..'")
    if candidate.is_symlink():
        raise ConfigurationError("target repository path must not be a symlink")
    if not candidate.exists():
        raise ConfigurationError("target does not exist: %s" % candidate)
    if not candidate.is_dir():
        raise ConfigurationError("target is not a directory: %s" % candidate)

    try:
        target = candidate.resolve(strict=True)
    except OSError as exc:
        raise ConfigurationError("target cannot be resolved: %s" % exc) from exc
    if Path(os.path.abspath(os.fspath(candidate))) != target:
        raise ConfigurationError(
            "target path resolves through a symlink or alias: %s -> %s"
            % (candidate, target)
        )

    git_marker = target / ".git"
    if git_marker.is_symlink():
        raise ConfigurationError("target .git entry must not be a symlink")
    try:
        process = subprocess.run(
            ["git", "-C", str(target), *GIT_READ_ONLY_ARGS],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ConfigurationError("unable to validate target Git worktree: %s" % exc) from exc
    if process.returncode != 0:
        raise ConfigurationError(
            "target is not a Git worktree/repository: %s" % target
        )
    try:
        git_root = Path(process.stdout.strip()).resolve(strict=True)
    except OSError as exc:
        raise ConfigurationError("Git returned an invalid worktree root") from exc
    if git_root != target:
        raise ConfigurationError(
            "target must be the Git worktree root: %s (Git root: %s)"
            % (target, git_root)
        )
    return target


def _assert_no_symlink_components(target: Path, destination: Path) -> None:
    try:
        relative = destination.relative_to(target)
    except ValueError as exc:
        raise ConfigurationError("destination escapes target root: %s" % destination) from exc

    current = target
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ConfigurationError(
                "destination path contains a symlink: %s" % current
            )
        if current.exists() and current != destination and not current.is_dir():
            raise ConfigurationError(
                "destination parent is not a directory: %s" % current
            )


def _preflight(
    target: Path, sources: dict[str, tuple[Path, bytes]]
) -> list[InventoryItem]:
    items = []
    for relative_path in INVENTORY:
        parts = _relative_parts(relative_path)
        source_path, source_bytes = sources[relative_path]
        destination = target.joinpath(*parts)
        _assert_no_symlink_components(target, destination)
        if destination.exists():
            if not destination.is_file():
                state = CONFLICT
            elif destination.read_bytes() == source_bytes:
                state = IDENTICAL
            else:
                state = CONFLICT
        else:
            state = MISSING
        items.append(
            InventoryItem(
                relative_path=relative_path,
                source_path=source_path,
                target_path=destination,
                source_bytes=source_bytes,
                state=state,
            )
        )
    return items


def _print_preflight(items: list[InventoryItem], stream) -> None:
    for item in items:
        print("%s %s" % (item.state, item.relative_path), file=stream)


def _write_missing(target: Path, items: list[InventoryItem], stream) -> None:
    for item in items:
        if item.state == IDENTICAL:
            print("UNCHANGED %s" % item.relative_path, file=stream)
            continue
        item.target_path.parent.mkdir(parents=True, exist_ok=True)
        _assert_no_symlink_components(target, item.target_path)
        try:
            with item.target_path.open("xb") as handle:
                handle.write(item.source_bytes)
        except FileExistsError as exc:
            raise ConfigurationError(
                "target changed after preflight; refused overwrite: %s"
                % item.target_path
            ) from exc
        print("CREATED %s" % item.relative_path, file=stream)


def materialize(
    target_arg: str,
    *,
    check_mode: bool = False,
    source_root: Path | None = None,
    stdout=None,
    stderr=None,
) -> int:
    """Check or install the fixed inventory and return the CLI exit code."""
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    try:
        root = plugin_root() if source_root is None else source_root
        sources = _load_sources(root)
        target = _validate_target(target_arg)
        items = _preflight(target, sources)
    except ConfigurationError as exc:
        print("CONFIGURATION_ERROR: %s" % exc, file=stderr)
        return EXIT_CONFIGURATION_ERROR

    conflicts = [item for item in items if item.state == CONFLICT]
    missing = [item for item in items if item.state == MISSING]

    if check_mode:
        _print_preflight(items, stdout)
        if conflicts:
            print(
                "CONFLICT: %d conflicting target file(s); no writes performed"
                % len(conflicts),
                file=stderr,
            )
            if any(item.relative_path == "AGENTS.md" for item in conflicts):
                agents = next(item for item in conflicts if item.relative_path == "AGENTS.md")
                print(
                    "AGENTS.md requires repository-owner manual merge; canonical source: %s"
                    % agents.source_path,
                    file=stderr,
                )
            return EXIT_CONFLICT
        if missing:
            print(
                "NOT_INSTALLED: %d required target file(s) missing; no writes performed"
                % len(missing),
                file=stderr,
            )
            return EXIT_NOT_INSTALLED
        print("OK: all %d files are identical" % len(items), file=stdout)
        return EXIT_OK

    if conflicts:
        _print_preflight(items, stdout)
        print(
            "CONFLICT: %d conflicting target file(s); transaction aborted with zero writes"
            % len(conflicts),
            file=stderr,
        )
        if any(item.relative_path == "AGENTS.md" for item in conflicts):
            agents = next(item for item in conflicts if item.relative_path == "AGENTS.md")
            print(
                "AGENTS.md requires repository-owner manual merge; canonical source: %s"
                % agents.source_path,
                file=stderr,
            )
        return EXIT_CONFLICT

    try:
        _write_missing(target, items, stdout)
    except (ConfigurationError, OSError) as exc:
        print("CONFIGURATION_ERROR: %s" % exc, file=stderr)
        return EXIT_CONFIGURATION_ERROR
    print(
        "INSTALLED: %d created, %d unchanged, %d total"
        % (len(missing), len(items) - len(missing), len(items)),
        file=stdout,
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install the Codex-host adapter into one explicit target Git repository."
    )
    parser.add_argument("--target", required=True, help="absolute target Git worktree root")
    parser.add_argument(
        "--check",
        action="store_true",
        help="classify the complete inventory without writing files or directories",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return materialize(args.target, check_mode=args.check)


if __name__ == "__main__":
    sys.exit(main())
