"""Provider-free tests for the Codex-host target-project materializer."""

from __future__ import annotations

import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "init_codex_host.py"

_spec = importlib.util.spec_from_file_location("init_codex_host", SCRIPT)
distribution = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules[_spec.name] = distribution
_spec.loader.exec_module(distribution)

INVENTORY = tuple(distribution.INVENTORY)
PORTABLE_SURFACES = (
    "AGENTS.md",
    ".codex/agents/worker.toml",
    ".codex/agents/executor.toml",
    ".agents/skills/orchestration-codex-host/SKILL.md",
    ".agents/skills/orchestration-codex-host/references/kickoff.md",
    ".agents/skills/orchestration-codex-host/references/go.md",
    ".agents/skills/orchestration-codex-host/references/dispatch.md",
    ".agents/skills/orchestration-codex-host/references/wrapup.md",
    "docs/playbook/codex-host.md",
    "examples/task-packets/codex-host-gate.md",
)


def git_init(path: Path) -> None:
    path.mkdir()
    process = subprocess.run(
        ["git", "init", "-q", str(path)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise AssertionError(process.stderr)


def snapshot_tree(root: Path, *, exclude_git: bool) -> dict[str, tuple]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if exclude_git and (relative == ".git" or relative.startswith(".git/")):
            continue
        if path.is_symlink():
            snapshot[relative] = ("symlink", os.readlink(path))
        elif path.is_file():
            stat = path.stat()
            snapshot[relative] = ("file", path.read_bytes(), stat.st_mtime_ns)
        elif path.is_dir():
            snapshot[relative] = ("dir",)
    return snapshot


def installed_files(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.relative_to(root).parts[0] != ".git"
    }


class DistributionTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="codex-host-distribution-", dir="/private/tmp"
        )
        self.temp_path = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def make_repo(self, name="target") -> Path:
        repo = self.temp_path / name
        git_init(repo)
        return repo

    def run_cli(self, target, *, check=False, cwd=ROOT):
        command = [sys.executable, str(SCRIPT), "--target", str(target)]
        if check:
            command.append("--check")
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )


class InstallBehaviorTests(DistributionTestCase):
    def test_empty_disposable_git_repo_installs_successfully(self):
        repo = self.make_repo()
        result = self.run_cli(repo)
        self.assertEqual(result.returncode, distribution.EXIT_OK, result.stderr)
        self.assertIn("INSTALLED: 20 created, 0 unchanged, 20 total", result.stdout)

    def test_every_required_target_file_exists(self):
        repo = self.make_repo()
        self.assertEqual(self.run_cli(repo).returncode, 0)
        self.assertEqual(installed_files(repo), set(INVENTORY))

    def test_target_bytes_equal_canonical_sources(self):
        repo = self.make_repo()
        self.assertEqual(self.run_cli(repo).returncode, 0)
        for relative in INVENTORY:
            self.assertEqual(
                (repo / relative).read_bytes(),
                (ROOT / relative).read_bytes(),
                relative,
            )

    def test_second_install_is_idempotent_no_op(self):
        repo = self.make_repo()
        self.assertEqual(self.run_cli(repo).returncode, 0)
        before = snapshot_tree(repo, exclude_git=True)
        result = self.run_cli(repo)
        after = snapshot_tree(repo, exclude_git=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("INSTALLED: 0 created, 20 unchanged, 20 total", result.stdout)
        self.assertEqual(after, before)

    def test_identical_existing_file_mtime_is_not_rewritten(self):
        repo = self.make_repo()
        self.assertEqual(self.run_cli(repo).returncode, 0)
        agents = repo / "AGENTS.md"
        os.utime(agents, ns=(1_000_000_000, 1_000_000_000))
        before = agents.stat().st_mtime_ns
        self.assertEqual(self.run_cli(repo).returncode, 0)
        self.assertEqual(agents.stat().st_mtime_ns, before)

    def test_new_missing_file_is_added_when_existing_files_are_identical(self):
        repo = self.make_repo()
        self.assertEqual(self.run_cli(repo).returncode, 0)
        missing = repo / "docs/playbook/codex-host.md"
        missing.unlink()
        result = self.run_cli(repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(missing.read_bytes(), (ROOT / "docs/playbook/codex-host.md").read_bytes())
        self.assertIn("INSTALLED: 1 created, 19 unchanged, 20 total", result.stdout)

    def test_source_root_is_derived_from_script_not_cwd(self):
        repo = self.make_repo()
        result = self.run_cli(repo, cwd=self.temp_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(installed_files(repo), set(INVENTORY))


class ConflictTests(DistributionTestCase):
    def test_one_conflict_aborts_entire_install_with_zero_writes(self):
        repo = self.make_repo()
        conflict = repo / "docs/playbook/agent-routing.json"
        conflict.parent.mkdir(parents=True)
        conflict.write_bytes(b"project-local routing\n")
        before = snapshot_tree(repo, exclude_git=True)
        result = self.run_cli(repo)
        after = snapshot_tree(repo, exclude_git=True)
        self.assertEqual(result.returncode, distribution.EXIT_CONFLICT)
        self.assertIn("CONFLICT docs/playbook/agent-routing.json", result.stdout)
        self.assertIn("transaction aborted with zero writes", result.stderr)
        self.assertEqual(after, before)

    def test_different_agents_md_requires_manual_merge_and_zero_writes(self):
        repo = self.make_repo()
        agents = repo / "AGENTS.md"
        agents.write_text("# Project instructions\n", encoding="utf-8")
        before = snapshot_tree(repo, exclude_git=True)
        result = self.run_cli(repo)
        after = snapshot_tree(repo, exclude_git=True)
        self.assertEqual(result.returncode, distribution.EXIT_CONFLICT)
        self.assertIn("CONFLICT AGENTS.md", result.stdout)
        self.assertIn("repository-owner manual merge", result.stderr)
        self.assertIn(str(ROOT / "AGENTS.md"), result.stderr)
        self.assertEqual(after, before)

    def test_directory_at_file_destination_is_a_conflict(self):
        repo = self.make_repo()
        (repo / "AGENTS.md").mkdir()
        before = snapshot_tree(repo, exclude_git=True)
        result = self.run_cli(repo)
        self.assertEqual(result.returncode, distribution.EXIT_CONFLICT)
        self.assertEqual(snapshot_tree(repo, exclude_git=True), before)


class CheckModeTests(DistributionTestCase):
    def test_check_all_identical_exits_zero(self):
        repo = self.make_repo()
        self.assertEqual(self.run_cli(repo).returncode, 0)
        result = self.run_cli(repo, check=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("IDENTICAL "), len(INVENTORY))
        self.assertIn("OK: all 20 files are identical", result.stdout)

    def test_check_missing_is_nonzero_and_writes_nothing(self):
        repo = self.make_repo()
        before = snapshot_tree(repo, exclude_git=False)
        result = self.run_cli(repo, check=True)
        after = snapshot_tree(repo, exclude_git=False)
        self.assertEqual(result.returncode, distribution.EXIT_NOT_INSTALLED)
        self.assertEqual(result.stdout.count("MISSING "), len(INVENTORY))
        self.assertIn("NOT_INSTALLED", result.stderr)
        self.assertEqual(after, before)

    def test_check_conflict_is_nonzero_and_writes_nothing(self):
        repo = self.make_repo()
        (repo / "AGENTS.md").write_bytes(b"different\n")
        before = snapshot_tree(repo, exclude_git=False)
        result = self.run_cli(repo, check=True)
        after = snapshot_tree(repo, exclude_git=False)
        self.assertEqual(result.returncode, distribution.EXIT_CONFLICT)
        self.assertIn("CONFLICT AGENTS.md", result.stdout)
        self.assertEqual(after, before)


class TargetValidationTests(DistributionTestCase):
    def test_relative_target_is_rejected(self):
        result = self.run_cli("relative-target")
        self.assertEqual(result.returncode, distribution.EXIT_CONFIGURATION_ERROR)
        self.assertIn("absolute path", result.stderr)

    def test_nonexistent_target_is_rejected_without_creation(self):
        target = self.temp_path / "missing"
        result = self.run_cli(target)
        self.assertEqual(result.returncode, distribution.EXIT_CONFIGURATION_ERROR)
        self.assertFalse(target.exists())

    def test_non_git_directory_is_rejected(self):
        target = self.temp_path / "directory"
        target.mkdir()
        before = snapshot_tree(target, exclude_git=False)
        result = self.run_cli(target)
        self.assertEqual(result.returncode, distribution.EXIT_CONFIGURATION_ERROR)
        self.assertIn("not a Git", result.stderr)
        self.assertEqual(snapshot_tree(target, exclude_git=False), before)

    def test_target_with_dotdot_component_is_rejected(self):
        repo = self.make_repo()
        target = repo.parent / "target" / ".." / "target"
        result = self.run_cli(target)
        self.assertEqual(result.returncode, distribution.EXIT_CONFIGURATION_ERROR)
        self.assertIn("must not contain '..'", result.stderr)

    def test_symlink_target_root_is_rejected(self):
        repo = self.make_repo()
        link = self.temp_path / "target-link"
        link.symlink_to(repo, target_is_directory=True)
        result = self.run_cli(link)
        self.assertEqual(result.returncode, distribution.EXIT_CONFIGURATION_ERROR)
        self.assertIn("must not be a symlink", result.stderr)

    def test_symlink_parent_escape_is_rejected_before_any_write(self):
        repo = self.make_repo()
        outside = self.temp_path / "outside"
        outside.mkdir()
        (repo / ".codex").symlink_to(outside, target_is_directory=True)
        before_repo = snapshot_tree(repo, exclude_git=True)
        before_outside = snapshot_tree(outside, exclude_git=False)
        result = self.run_cli(repo)
        self.assertEqual(result.returncode, distribution.EXIT_CONFIGURATION_ERROR)
        self.assertIn("contains a symlink", result.stderr)
        self.assertEqual(snapshot_tree(repo, exclude_git=True), before_repo)
        self.assertEqual(snapshot_tree(outside, exclude_git=False), before_outside)

    def test_subdirectory_of_git_repo_is_rejected(self):
        repo = self.make_repo()
        child = repo / "child"
        child.mkdir()
        result = self.run_cli(child)
        self.assertEqual(result.returncode, distribution.EXIT_CONFIGURATION_ERROR)
        self.assertIn("Git worktree root", result.stderr)


class SecurityAndPortabilityTests(DistributionTestCase):
    def test_install_does_not_modify_dot_git(self):
        repo = self.make_repo()
        before = snapshot_tree(repo / ".git", exclude_git=False)
        result = self.run_cli(repo)
        after = snapshot_tree(repo / ".git", exclude_git=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(after, before)

    def test_materializer_invokes_only_read_only_git_validation(self):
        repo = self.make_repo()
        real_run = subprocess.run
        calls = []

        def record(args, **kwargs):
            calls.append(tuple(args))
            return real_run(args, **kwargs)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(distribution.subprocess, "run", side_effect=record):
            result = distribution.materialize(
                str(repo), check_mode=True, stdout=stdout, stderr=stderr
            )
        self.assertEqual(result, distribution.EXIT_NOT_INSTALLED)
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0],
            ("git", "-C", str(repo.resolve()), "rev-parse", "--show-toplevel"),
        )
        for forbidden in ("add", "commit", "push", "checkout", "merge", "reset"):
            self.assertNotIn(forbidden, calls[0])

    def test_no_home_global_config_provider_network_or_force_surface(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for marker in (
            "Path.home(",
            ".expanduser(",
            "~/.codex",
            "~/.agents",
            "--force",
            "claude_cli",
            "codex_cli",
            "urllib",
            "requests.",
        ):
            self.assertNotIn(marker, text)

    def test_inventory_never_targets_dot_git(self):
        for relative in INVENTORY:
            self.assertNotEqual(PurePathParts(relative)[0], ".git")

    def test_only_explicit_inventory_is_installed(self):
        repo = self.make_repo()
        self.assertEqual(self.run_cli(repo).returncode, 0)
        self.assertEqual(installed_files(repo), set(INVENTORY))
        for forbidden_prefix in (
            "tests/",
            "commands/",
            "agents/",
            ".claude-plugin/",
        ):
            self.assertFalse(
                any(path.startswith(forbidden_prefix) for path in installed_files(repo)),
                forbidden_prefix,
            )

    def test_installed_skill_markdown_links_resolve_inside_target(self):
        repo = self.make_repo()
        self.assertEqual(self.run_cli(repo).returncode, 0)
        skill = repo / ".agents/skills/orchestration-codex-host/SKILL.md"
        links = re.findall(r"\]\(([^)]+)\)", skill.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(links), 4)
        for link in links:
            resolved = (skill.parent / link).resolve(strict=True)
            resolved.relative_to(repo.resolve())

    def test_installed_runner_routing_schema_and_agents_are_target_local(self):
        repo = self.make_repo()
        self.assertEqual(self.run_cli(repo).returncode, 0)
        for relative in (
            "scripts/orchestration_agent.py",
            "docs/playbook/agent-routing.json",
            "examples/schemas/orchestration-result.schema.json",
            ".codex/agents/worker.toml",
            ".codex/agents/executor.toml",
        ):
            self.assertTrue((repo / relative).is_file(), relative)
        dispatch = (
            repo
            / ".agents/skills/orchestration-codex-host/references/dispatch.md"
        ).read_text(encoding="utf-8")
        for relative in (
            "scripts/orchestration_agent.py",
            "docs/playbook/agent-routing.json",
            "examples/schemas/orchestration-result.schema.json",
        ):
            self.assertIn(relative, dispatch)

    def test_portable_surfaces_contain_no_absolute_plugin_worktree_path(self):
        forbidden = b"/Users/tzuhsuan/code/claude-orchestration-plugin-"
        for relative in PORTABLE_SURFACES:
            self.assertNotIn(forbidden, (ROOT / relative).read_bytes(), relative)

    def test_runner_resolves_its_root_from_its_installed_file(self):
        text = (ROOT / "scripts/orchestration_agent.py").read_text(encoding="utf-8")
        self.assertIn(
            "Path(__file__).resolve().parent.parent",
            text,
        )
        materializer = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Path(__file__).resolve().parent.parent", materializer)
        self.assertNotIn("Path.cwd(", materializer)

    def test_missing_canonical_source_fails_before_target_write(self):
        repo = self.make_repo()
        source = self.temp_path / "incomplete-source"
        source.mkdir()
        omitted = INVENTORY[-1]
        for relative in INVENTORY[:-1]:
            destination = source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        before = snapshot_tree(repo, exclude_git=False)
        stdout = io.StringIO()
        stderr = io.StringIO()
        result = distribution.materialize(
            str(repo),
            source_root=source,
            stdout=stdout,
            stderr=stderr,
        )
        self.assertEqual(result, distribution.EXIT_CONFIGURATION_ERROR)
        self.assertIn(omitted, stderr.getvalue())
        self.assertEqual(snapshot_tree(repo, exclude_git=False), before)


def PurePathParts(relative: str) -> tuple[str, ...]:
    return tuple(relative.split("/"))


if __name__ == "__main__":
    unittest.main()
