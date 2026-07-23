"""Tests for the bounded external-agent runner.

All provider invocations use the fake `codex`/`claude` executables in
tests/fixtures/orchestration-agent/bin — no real provider, no network,
no quota. Target repositories are built at test time by copying
repo-template/ into a temporary directory and running `git init` there
(feasibility finding F4: no nested .git is ever committed).
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from importlib import util as importlib_util
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = PLUGIN_ROOT / "scripts" / "orchestration_agent.py"
FIXTURES = PLUGIN_ROOT / "tests" / "fixtures" / "orchestration-agent"
FAKE_BIN = FIXTURES / "bin"
REPO_TEMPLATE = FIXTURES / "repo-template"
DEFAULT_ROUTING_FILE = PLUGIN_ROOT / "docs" / "playbook" / "agent-routing.json"

_spec = importlib_util.spec_from_file_location("orchestration_agent", RUNNER_PATH)
oa = importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(oa)

FAKE_ENV_KEYS = (
    "FAKE_CLI_MODE",
    "FAKE_ARGV_FILE",
    "FAKE_STDIN_FILE",
    "FAKE_FINAL_RESULT",
    "FAKE_RESULT_STYLE",
    "FAKE_WRITE_PATH",
    "FAKE_PID_FILE",
    "FAKE_DELETE_PATH",
    "FAKE_STDERR_TEXT",
    "FAKE_EXIT_CODE",
    "FAKE_SLEEP_SECONDS",
)

GIT_WRITE_SUBCOMMANDS = frozenset(
    {
        "add",
        "commit",
        "push",
        "merge",
        "rebase",
        "reset",
        "clean",
        "checkout",
        "switch",
        "restore",
        "stash",
        "worktree",
    }
)


def default_routing():
    return json.loads(DEFAULT_ROUTING_FILE.read_text(encoding="utf-8"))


def make_result(role, provider, profile, **overrides):
    result = {
        "schema_version": 1,
        "role": role,
        "provider": provider,
        "profile": profile,
        "model": "fake-model-1",
        "verdict": (
            "PASS_FOR_IMPLEMENTATION_AUTHORIZATION"
            if role == "feasibility_verifier"
            else "COMPLETED"
        ),
        "summary": "fake run summary",
        "evidence": ["src/app.py:1 fake evidence"],
        "stop_reason": None,
        "session_id": "00000000-0000-0000-0000-000000000001",
        "changed_files": [],
        "tests": [],
        "repository_state": {
            "pre": {"head_sha": "0" * 40, "status_short": ""},
            "post": {"head_sha": "0" * 40, "status_short": ""},
        },
        # Fixed envelope: every role sends all four reviewer collections;
        # non-reviewer roles must leave them empty.
        "findings": [],
        "observations": [],
        "suggestions": [],
        "evidence_gaps": [],
    }
    result.update(overrides)
    return result


ROLE_DEFAULTS = {
    "feasibility_verifier": ("codex_cli", "codex_read_only"),
    "implementer": ("codex_cli", "codex_workspace_write"),
    "adversarial_reviewer": ("claude_cli", "claude_read_only"),
}


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._env_backup = os.environ.copy()
        os.environ["PATH"] = str(FAKE_BIN) + os.pathsep + self._env_backup.get("PATH", "")
        for key in FAKE_ENV_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)
        self._tmp.cleanup()

    # -- helpers -----------------------------------------------------------

    def make_repo(self):
        repo = self.tmp / ("repo-" + uuid.uuid4().hex[:8])
        shutil.copytree(REPO_TEMPLATE, repo)
        run = lambda *args: subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.name=fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            check=True,
            capture_output=True,
        )
        run("init", "-q")
        run("add", "-A")
        run("commit", "-q", "-m", "fixture base commit")
        return repo

    def write_routing(self, routing):
        path = self.tmp / ("routing-" + uuid.uuid4().hex[:8] + ".json")
        path.write_text(json.dumps(routing, indent=2), encoding="utf-8")
        return path

    def run_runner(
        self,
        role,
        *,
        routing=None,
        mode="success",
        final=None,
        allowed=(),
        forbidden=(),
        timeout=30,
        grace=2,
        resume=None,
        repo=None,
        extra_env=None,
        model="fake-model-1",
    ):
        repo = repo or self.make_repo()
        artifact_dir = self.tmp / ("artifacts-" + uuid.uuid4().hex[:8])
        task_file = self.tmp / ("task-" + uuid.uuid4().hex[:8] + ".md")
        task_file.write_text("fake task packet content\n", encoding="utf-8")
        routing_path = self.write_routing(routing if routing is not None else default_routing())
        os.environ["FAKE_CLI_MODE"] = mode
        if final is None and role in ROLE_DEFAULTS:
            provider, profile = ROLE_DEFAULTS[role]
            final = make_result(role, provider, profile)
        if final is not None:
            os.environ["FAKE_FINAL_RESULT"] = json.dumps(final)
        for key, value in (extra_env or {}).items():
            os.environ[key] = value
        argv = [
            "run",
            "--routing-file",
            str(routing_path),
            "--role",
            role,
            "--workdir",
            str(repo),
            "--task-file",
            str(task_file),
            "--artifact-dir",
            str(artifact_dir),
            "--timeout-seconds",
            str(timeout),
            "--grace-seconds",
            str(grace),
            "--model",
            model,
        ]
        for path in allowed:
            argv += ["--allowed-file", path]
        for path in forbidden:
            argv += ["--forbidden-file", path]
        if resume:
            argv += ["--resume-session-id", resume]
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = oa.main(argv)
        return rc, artifact_dir, repo, stdout.getvalue()

    def read_invocation(self, artifact_dir):
        return json.loads((artifact_dir / "invocation.json").read_text(encoding="utf-8"))

    def assert_outcome(self, artifact_dir, expected):
        invocation = self.read_invocation(artifact_dir)
        self.assertEqual(invocation["outcome"], expected, invocation["detail"])
        return invocation


# ---------------------------------------------------------------------------
# Routing validation
# ---------------------------------------------------------------------------


class RoutingValidationTests(RunnerTestCase):
    def test_valid_default_routing_loads(self):
        routing = oa.load_routing(DEFAULT_ROUTING_FILE)
        self.assertEqual(oa.validate_routing(routing), [])

    def test_authority_owner_tamper_is_configuration_error(self):
        routing = default_routing()
        routing["authority"]["final_adjudicator"] = "implementer"
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_same_provider_implementer_reviewer_is_configuration_error(self):
        routing = default_routing()
        routing["roles"]["adversarial_reviewer"] = {
            "provider": "codex_cli",
            "profile": "codex_read_only",
        }
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_unknown_provider_is_configuration_error(self):
        routing = default_routing()
        routing["roles"]["implementer"]["provider"] = "openai_agentkit"
        rc, artifacts, _, _ = self.run_runner("implementer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_unknown_profile_is_configuration_error(self):
        routing = default_routing()
        routing["roles"]["implementer"]["profile"] = "danger_full_access"
        rc, artifacts, _, _ = self.run_runner("implementer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_read_only_role_with_write_profile_is_configuration_error(self):
        routing = default_routing()
        routing["roles"]["feasibility_verifier"] = {
            "provider": "codex_cli",
            "profile": "codex_workspace_write",
        }
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_dispatch_constraint_tamper_is_configuration_error(self):
        routing = default_routing()
        routing["constraints"]["implementer_may_dispatch_reviewer"] = True
        rc, artifacts, _, _ = self.run_runner("implementer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_claude_subagent_routing_is_capability_unavailable(self):
        routing = default_routing()
        routing["roles"]["implementer"] = {
            "provider": "claude_subagent",
            "profile": "executor",
        }
        rc, artifacts, _, _ = self.run_runner("implementer", routing=routing)
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CAPABILITY_UNAVAILABLE")
        self.assertIn("Task path", invocation["detail"])


# ---------------------------------------------------------------------------
# Session boundaries
# ---------------------------------------------------------------------------


class SessionBoundaryTests(RunnerTestCase):
    def test_reviewer_resume_is_configuration_error(self):
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer", resume=str(uuid.uuid4())
        )
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_cross_role_resume_is_configuration_error(self):
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier", resume=str(uuid.uuid4())
        )
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_implementer_resume_is_deferred_fail_closed(self):
        rc, artifacts, _, _ = self.run_runner("implementer", resume=str(uuid.uuid4()))
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CAPABILITY_UNAVAILABLE")
        self.assertIn("not supported yet", invocation["detail"])


# ---------------------------------------------------------------------------
# Codex read-only paths
# ---------------------------------------------------------------------------


class CodexReadOnlyTests(RunnerTestCase):
    def test_read_only_happy_path_success(self):
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier")
        self.assertEqual(rc, 0)
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        self.assertEqual(invocation["cli_version"], "fake-codex 0.0.1")
        for name in (
            "task.md",
            "routing.json",
            "invocation.json",
            "stdout.jsonl",
            "stderr.log",
            "final-result.json",
            "pre-git.json",
            "post-git.json",
            "changed-paths.json",
            "manifest.sha256",
        ):
            self.assertTrue((artifacts / name).is_file(), name)

    def test_read_only_tracked_write_is_mutation(self):
        rc, artifacts, repo, _ = self.run_runner(
            "feasibility_verifier",
            mode="write-file",
            extra_env={"FAKE_WRITE_PATH": "src/app.py"},
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "READ_ONLY_MUTATION")
        # No cleanup: the mutated file must remain exactly as the agent left it.
        self.assertEqual(
            (repo / "src" / "app.py").read_text(encoding="utf-8"),
            "written by fake agent\n",
        )

    def test_read_only_untracked_write_is_mutation(self):
        rc, artifacts, repo, _ = self.run_runner(
            "feasibility_verifier",
            mode="write-file",
            extra_env={"FAKE_WRITE_PATH": "NEW_FILE.txt"},
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "READ_ONLY_MUTATION")
        self.assertTrue((repo / "NEW_FILE.txt").is_file())

    def test_closed_gate_fixture_is_flagged_and_never_reverted(self):
        template_text = (REPO_TEMPLATE / "CLOSED_GATE.md").read_text(encoding="utf-8")
        rc, artifacts, repo, _ = self.run_runner(
            "feasibility_verifier",
            mode="write-file",
            extra_env={"FAKE_WRITE_PATH": "CLOSED_GATE.md"},
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "READ_ONLY_MUTATION")
        # The runner must neither restore the closed-gate file (no revert)...
        self.assertEqual(
            (repo / "CLOSED_GATE.md").read_text(encoding="utf-8"),
            "written by fake agent\n",
        )
        # ...nor have touched the committed template source.
        self.assertEqual(
            (REPO_TEMPLATE / "CLOSED_GATE.md").read_text(encoding="utf-8"), template_text
        )


# ---------------------------------------------------------------------------
# Provider argv construction
# ---------------------------------------------------------------------------


class ProviderArgvTests(RunnerTestCase):
    def captured_argv(self):
        return json.loads(
            (self.tmp / "captured-argv.json").read_text(encoding="utf-8")
        )

    def test_codex_read_only_argv(self):
        stdin_capture = self.tmp / "captured-stdin.txt"
        rc, _, repo, _ = self.run_runner(
            "feasibility_verifier",
            extra_env={
                "FAKE_ARGV_FILE": str(self.tmp / "captured-argv.json"),
                "FAKE_STDIN_FILE": str(stdin_capture),
            },
        )
        self.assertEqual(rc, 0)
        argv = self.captured_argv()
        self.assertEqual(argv[0], "exec")
        self.assertIn("-s", argv)
        self.assertEqual(argv[argv.index("-s") + 1], "read-only")
        self.assertIn("approval_policy=never", argv)
        self.assertEqual(argv[argv.index("approval_policy=never") - 1], "-c")
        self.assertNotIn("-a", argv)
        self.assertNotIn("--full-auto", argv)
        self.assertIn("--json", argv)
        self.assertIn("--output-schema", argv)
        self.assertIn("-m", argv)
        self.assertEqual(argv[argv.index("-m") + 1], "fake-model-1")
        self.assertIn("-C", argv)
        self.assertEqual(argv[argv.index("-C") + 1], str(repo))
        self.assertEqual(argv[-1], "-")
        self.assertEqual(
            stdin_capture.read_text(encoding="utf-8"), "fake task packet content\n"
        )

    def test_codex_implementation_argv_requests_network_disabled(self):
        rc, artifacts, _, _ = self.run_runner(
            "implementer",
            allowed=("src/app.py",),
            extra_env={"FAKE_ARGV_FILE": str(self.tmp / "captured-argv.json")},
        )
        self.assertEqual(rc, 0)
        argv = self.captured_argv()
        self.assertEqual(argv[argv.index("-s") + 1], "workspace-write")
        self.assertIn("sandbox_workspace_write.network_access=false", argv)
        index = argv.index("sandbox_workspace_write.network_access=false")
        self.assertEqual(argv[index - 1], "-c")
        invocation = self.read_invocation(artifacts)
        self.assertFalse(invocation["network"]["verified_by_real_cli"])
        self.assertIn("smoke test", invocation["network"]["note"])

    def test_codex_argv_has_no_dangerous_bypass_flags(self):
        rc, _, _, _ = self.run_runner(
            "feasibility_verifier",
            extra_env={"FAKE_ARGV_FILE": str(self.tmp / "captured-argv.json")},
        )
        self.assertEqual(rc, 0)
        argv = self.captured_argv()
        for element in argv:
            self.assertNotIn("dangerously", element)
            self.assertNotIn("yolo", element)
            self.assertNotEqual(element, "danger-full-access")

    def test_claude_reviewer_argv_read_only_and_fresh(self):
        rc, _, _, _ = self.run_runner(
            "adversarial_reviewer",
            extra_env={"FAKE_ARGV_FILE": str(self.tmp / "captured-argv.json")},
        )
        self.assertEqual(rc, 0)
        argv = self.captured_argv()
        self.assertIn("-p", argv)
        self.assertIn("--verbose", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "plan")
        self.assertEqual(argv[argv.index("--tools") + 1], "Read,Glob,Grep")
        self.assertEqual(
            argv[argv.index("--disallowedTools") + 1], "Bash,Edit,Write,NotebookEdit,Task"
        )
        self.assertIn("--strict-mcp-config", argv)
        self.assertIn("--disable-slash-commands", argv)
        self.assertIn("--no-session-persistence", argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "stream-json")
        self.assertIn("--json-schema", argv)
        for flag in ("--resume", "--continue", "--fork-session", "--mcp-config", "-r", "-c"):
            self.assertNotIn(flag, argv)


# ---------------------------------------------------------------------------
# Implementation changed-path validation
# ---------------------------------------------------------------------------


class ImplementationPathTests(RunnerTestCase):
    def test_allowed_file_change_is_success(self):
        rc, artifacts, _, _ = self.run_runner(
            "implementer",
            mode="write-file",
            allowed=("src/app.py",),
            forbidden=("FORBIDDEN.md",),
            extra_env={"FAKE_WRITE_PATH": "src/app.py"},
            final=make_result(
                "implementer",
                "codex_cli",
                "codex_workspace_write",
                changed_files=["src/app.py"],
            ),
        )
        self.assertEqual(rc, 0)
        self.assert_outcome(artifacts, "SUCCESS")
        changed = json.loads(
            (artifacts / "changed-paths.json").read_text(encoding="utf-8")
        )
        self.assertEqual(changed["changed_paths"], ["src/app.py"])
        self.assertEqual(changed["violations"], [])

    def test_forbidden_file_change_is_flagged_without_revert(self):
        rc, artifacts, repo, _ = self.run_runner(
            "implementer",
            mode="write-file",
            allowed=("src/app.py",),
            forbidden=("FORBIDDEN.md",),
            extra_env={"FAKE_WRITE_PATH": "FORBIDDEN.md"},
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "FORBIDDEN_PATH_CHANGED")
        # Evidence preserved, no automatic repair.
        self.assertEqual(
            (repo / "FORBIDDEN.md").read_text(encoding="utf-8"),
            "written by fake agent\n",
        )

    def test_unlisted_file_change_is_forbidden_path_changed(self):
        rc, artifacts, _, _ = self.run_runner(
            "implementer",
            mode="write-file",
            allowed=("src/app.py",),
            extra_env={"FAKE_WRITE_PATH": "UNLISTED.txt"},
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "FORBIDDEN_PATH_CHANGED")

    def test_dirty_prestate_fails_closed_without_cleanup(self):
        repo = self.make_repo()
        marker = "pre-existing user work\n"
        (repo / "src" / "app.py").write_text(marker, encoding="utf-8")
        rc, artifacts, _, _ = self.run_runner(
            "implementer", allowed=("src/app.py",), repo=repo
        )
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        # The pre-existing change must survive untouched.
        self.assertEqual((repo / "src" / "app.py").read_text(encoding="utf-8"), marker)


# ---------------------------------------------------------------------------
# Process behavior
# ---------------------------------------------------------------------------


class ProcessBehaviorTests(RunnerTestCase):
    def test_nonzero_exit_preserves_stderr(self):
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier", mode="nonzero")
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "PROCESS_NONZERO")
        self.assertEqual(invocation["child_exit_code"], 3)
        self.assertIn(
            "fake failure detail on stderr",
            (artifacts / "stderr.log").read_text(encoding="utf-8"),
        )

    def test_timeout_kills_process_group_and_keeps_partial_transcript(self):
        pid_file = self.tmp / "pids.json"
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier",
            mode="partial-timeout",
            timeout=1,
            grace=1,
            extra_env={"FAKE_PID_FILE": str(pid_file)},
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "TIMEOUT")
        stdout_text = (artifacts / "stdout.jsonl").read_text(encoding="utf-8")
        self.assertIn("partial output before hang", stdout_text)
        for name in ("pre-git.json", "post-git.json", "invocation.json", "manifest.sha256"):
            self.assertTrue((artifacts / name).is_file(), name)
        pids = json.loads(pid_file.read_text(encoding="utf-8"))
        for label in ("self", "grandchild"):
            self.assert_process_dead(pids[label], label)

    def assert_process_dead(self, pid, label):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            except PermissionError:
                self.fail("%s process %d still exists (owned elsewhere)" % (label, pid))
            # A killed child may linger as a zombie until reaped by its parent;
            # reap-check via waitpid is not possible across sessions, so poll.
            time.sleep(0.1)
        self.fail("%s process %d still alive after kill" % (label, pid))

    def test_interrupt_terminates_group_and_classifies_interrupted(self):
        repo = self.make_repo()
        artifact_dir = self.tmp / "artifacts-interrupt"
        task_file = self.tmp / "task-interrupt.md"
        task_file.write_text("fake task packet content\n", encoding="utf-8")
        routing_path = self.write_routing(default_routing())
        pid_file = self.tmp / "pids-interrupt.json"
        env = os.environ.copy()
        env.update({"FAKE_CLI_MODE": "timeout", "FAKE_PID_FILE": str(pid_file)})
        runner = subprocess.Popen(
            [
                sys.executable,
                str(RUNNER_PATH),
                "run",
                "--routing-file",
                str(routing_path),
                "--role",
                "feasibility_verifier",
                "--workdir",
                str(repo),
                "--task-file",
                str(task_file),
                "--artifact-dir",
                str(artifact_dir),
                "--timeout-seconds",
                "60",
                "--grace-seconds",
                "1",
                "--model",
                "fake-model-1",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 10
        while not pid_file.is_file() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(pid_file.is_file(), "fake CLI never started")
        runner.send_signal(signal.SIGINT)
        runner.wait(timeout=15)
        self.assertEqual(runner.returncode, 1)
        invocation = json.loads(
            (artifact_dir / "invocation.json").read_text(encoding="utf-8")
        )
        self.assertEqual(invocation["outcome"], "INTERRUPTED")
        pids = json.loads(pid_file.read_text(encoding="utf-8"))
        self.assert_process_dead(pids["grandchild"], "grandchild")

    def test_stdout_and_stderr_are_separate(self):
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier",
            extra_env={"FAKE_STDERR_TEXT": "stderr-marker-line"},
        )
        self.assertEqual(rc, 0)
        stdout_text = (artifacts / "stdout.jsonl").read_text(encoding="utf-8")
        stderr_text = (artifacts / "stderr.log").read_text(encoding="utf-8")
        self.assertIn("stderr-marker-line", stderr_text)
        self.assertNotIn("stderr-marker-line", stdout_text)
        self.assertIn("fake codex event", stdout_text)
        self.assertNotIn("fake codex event", stderr_text)


# ---------------------------------------------------------------------------
# Structured output validation
# ---------------------------------------------------------------------------


class StructuredOutputTests(RunnerTestCase):
    def test_invalid_final_json_is_invalid_output(self):
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier", mode="invalid-json")
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "INVALID_OUTPUT")

    def test_missing_final_result_is_invalid_output(self):
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier", mode="missing-final")
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "INVALID_OUTPUT")

    def test_deleted_transcript_is_transcript_incomplete(self):
        artifact_dir = self.tmp / ("artifacts-" + uuid.uuid4().hex[:8])
        # FAKE_DELETE_PATH must point at the runner-owned stdout artifact.
        rc = None
        repo = self.make_repo()
        task_file = self.tmp / "task-del.md"
        task_file.write_text("fake task packet content\n", encoding="utf-8")
        routing_path = self.write_routing(default_routing())
        os.environ["FAKE_CLI_MODE"] = "delete-transcript"
        os.environ["FAKE_DELETE_PATH"] = str(artifact_dir / "stdout.jsonl")
        os.environ["FAKE_FINAL_RESULT"] = json.dumps(
            make_result("feasibility_verifier", "codex_cli", "codex_read_only")
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = oa.main(
                [
                    "run",
                    "--routing-file",
                    str(routing_path),
                    "--role",
                    "feasibility_verifier",
                    "--workdir",
                    str(repo),
                    "--task-file",
                    str(task_file),
                    "--artifact-dir",
                    str(artifact_dir),
                    "--timeout-seconds",
                    "30",
                    "--model",
                    "fake-model-1",
                ]
            )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifact_dir, "TRANSCRIPT_INCOMPLETE")

    def test_result_role_mismatch_is_invalid_output(self):
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier",
            final=make_result("implementer", "codex_cli", "codex_read_only"),
        )
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("role mismatch", invocation["detail"])

    def test_model_blocker_is_distinct_outcome(self):
        rc, artifacts, _, _ = self.run_runner(
            "implementer",
            allowed=("src/app.py",),
            final=make_result(
                "implementer",
                "codex_cli",
                "codex_workspace_write",
                verdict="MODEL_REPORTED_BLOCKER",
                stop_reason="forbidden-file dependency discovered",
            ),
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "MODEL_REPORTED_BLOCKER")

    def test_model_stop_is_distinct_outcome(self):
        rc, artifacts, _, _ = self.run_runner(
            "implementer",
            allowed=("src/app.py",),
            final=make_result(
                "implementer",
                "codex_cli",
                "codex_workspace_write",
                verdict="STOPPED",
                stop_reason="specification contradiction",
            ),
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "STOPPED")

    def test_reviewer_finding_missing_evidence_is_invalid_output(self):
        finding = {
            "id": "F1",
            "severity": "Major",
            "violated_requirement": "some requirement",
            "location": "src/app.py:1",
            # repository_evidence intentionally missing
            "impact": "impact text",
            "minimal_remediation_scope": "scope text",
        }
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            final=make_result(
                "adversarial_reviewer", "claude_cli", "claude_read_only", findings=[finding]
            ),
        )
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("repository_evidence", invocation["detail"])

    def test_reviewer_bad_severity_is_invalid_output(self):
        finding = {
            "id": "F1",
            "severity": "Catastrophic",
            "violated_requirement": "some requirement",
            "location": "src/app.py:1",
            "repository_evidence": "src/app.py:1 evidence",
            "impact": "impact text",
            "minimal_remediation_scope": "scope text",
        }
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            final=make_result(
                "adversarial_reviewer", "claude_cli", "claude_read_only", findings=[finding]
            ),
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "INVALID_OUTPUT")

    def test_claude_reviewer_happy_path_success(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer")
        self.assertEqual(rc, 0)
        self.assert_outcome(artifacts, "SUCCESS")
        final = json.loads((artifacts / "final-result.json").read_text(encoding="utf-8"))
        for field in ("findings", "observations", "suggestions", "evidence_gaps"):
            self.assertEqual(final[field], [])


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


class ManifestTests(RunnerTestCase):
    def run_and_verify(self):
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier")
        self.assertEqual(rc, 0)
        return artifacts

    def verify(self, artifacts):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = oa.main(["verify-manifest", "--artifact-dir", str(artifacts)])
        return rc, json.loads(stdout.getvalue())

    def test_manifest_verifies_after_run(self):
        artifacts = self.run_and_verify()
        rc, report = self.verify(artifacts)
        self.assertEqual(rc, 0)
        self.assertEqual(report["manifest"], "PASS")

    def test_manifest_fails_after_tamper(self):
        artifacts = self.run_and_verify()
        stdout_file = artifacts / "stdout.jsonl"
        stdout_file.write_text(
            stdout_file.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8"
        )
        rc, report = self.verify(artifacts)
        self.assertEqual(rc, 1)
        self.assertEqual(report["manifest"], "FAIL")
        self.assertTrue(any("hash mismatch" in p for p in report["problems"]))

    def test_manifest_fails_on_missing_artifact(self):
        artifacts = self.run_and_verify()
        (artifacts / "stderr.log").unlink()
        rc, report = self.verify(artifacts)
        self.assertEqual(rc, 1)
        self.assertTrue(any("missing artifact" in p for p in report["problems"]))


# ---------------------------------------------------------------------------
# Static safety
# ---------------------------------------------------------------------------


class StaticSafetyTests(unittest.TestCase):
    SOURCE = RUNNER_PATH.read_text(encoding="utf-8")

    def test_no_dangerous_bypass_flag_strings_in_source(self):
        for token in (
            "dangerously-bypass-approvals-and-sandbox",
            "dangerously-bypass-hook-trust",
            "dangerously-skip-permissions",
            "yolo",
            "danger-full-access",
        ):
            self.assertNotIn(token, self.SOURCE, token)

    def test_git_allowlist_is_read_only(self):
        self.assertTrue(oa.GIT_READ_ONLY_SUBCOMMANDS.isdisjoint(GIT_WRITE_SUBCOMMANDS))
        with self.assertRaises(ValueError):
            oa._run_git(PLUGIN_ROOT, ["add", "."])
        with self.assertRaises(ValueError):
            oa._run_git(PLUGIN_ROOT, ["worktree", "add", "/tmp/x"])

    def test_subprocess_calls_confined_to_whitelisted_functions(self):
        tree = ast.parse(self.SOURCE)
        allowed_functions = {"_run_git", "_capture_cli_version", "_spawn_child"}
        offenders = []

        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.stack = []

            def visit_FunctionDef(self, node):
                self.stack.append(node.name)
                self.generic_visit(node)
                self.stack.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Call(self, node):
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "subprocess"
                    and func.attr in {"run", "Popen", "call", "check_call", "check_output"}
                ):
                    location = self.stack[-1] if self.stack else "<module>"
                    if location not in allowed_functions:
                        offenders.append((location, func.attr))
                self.generic_visit(node)

        Visitor().visit(tree)
        self.assertEqual(offenders, [])

    def test_only_run_git_reaches_git_and_it_is_read_only(self):
        # _run_git is the sole function that constructs a git argv, and its
        # first-token allowlist makes every reachable git call read-only.
        tree = ast.parse(self.SOURCE)
        git_literal_functions = set()

        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.stack = []

            def visit_FunctionDef(self, node):
                self.stack.append(node.name)
                self.generic_visit(node)
                self.stack.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Constant(self, node):
                if node.value == "git" and self.stack:
                    git_literal_functions.add(self.stack[-1])

        Visitor().visit(tree)
        self.assertEqual(git_literal_functions, {"_run_git"})


# ---------------------------------------------------------------------------
# Corrective C1 — real-CLI contract closure (RC-1 schema transport, RC-2 argv)
# ---------------------------------------------------------------------------


class StrictSchemaContractTests(unittest.TestCase):
    """RC-1: the canonical schema must stay in the strict transport subset."""

    SCHEMA = json.loads(
        (PLUGIN_ROOT / "examples" / "schemas" / "orchestration-result.schema.json")
        .read_text(encoding="utf-8")
    )

    FORBIDDEN = {
        "if",
        "then",
        "else",
        "allOf",
        "dependentSchemas",
        "unevaluatedProperties",
        "patternProperties",
    }

    def walk_objects(self, node, location="$"):
        if isinstance(node, dict):
            yield location, node
            for key, value in node.items():
                yield from self.walk_objects(value, "%s.%s" % (location, key))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from self.walk_objects(value, "%s[%d]" % (location, index))

    def test_every_object_declares_strict_contract(self):
        object_nodes = 0
        for location, node in self.walk_objects(self.SCHEMA):
            if node.get("type") == "object" or "properties" in node:
                object_nodes += 1
                self.assertIs(node.get("additionalProperties"), False, location)
                self.assertEqual(
                    set(node.get("required", [])), set(node["properties"]), location
                )
        self.assertGreaterEqual(object_nodes, 5)

    def test_no_forbidden_conditional_keywords(self):
        for location, node in self.walk_objects(self.SCHEMA):
            self.assertFalse(self.FORBIDDEN.intersection(node), location)

    def test_runner_preflight_accepts_canonical_schema(self):
        self.assertEqual(oa.preflight_strict_schema(self.SCHEMA), [])


class SchemaPreflightTests(RunnerTestCase):
    """RC-1: preflight fails closed before any provider spawn."""

    def run_with_schema(self, mutate):
        schema = json.loads(
            (PLUGIN_ROOT / "examples" / "schemas" / "orchestration-result.schema.json")
            .read_text(encoding="utf-8")
        )
        mutate(schema)
        bad_schema = self.tmp / "mutated-schema.json"
        bad_schema.write_text(json.dumps(schema), encoding="utf-8")
        argv_file = self.tmp / "captured-argv.json"
        original = oa.RESULT_SCHEMA_FILE
        oa.RESULT_SCHEMA_FILE = bad_schema
        try:
            rc, artifacts, _, _ = self.run_runner(
                "feasibility_verifier",
                extra_env={"FAKE_ARGV_FILE": str(argv_file)},
            )
        finally:
            oa.RESULT_SCHEMA_FILE = original
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("preflight", invocation["detail"])
        # The fake provider must never have been spawned: no argv capture.
        self.assertFalse(argv_file.exists(), "provider was spawned despite preflight failure")
        return invocation

    def test_missing_nested_additional_properties_fails_closed(self):
        self.run_with_schema(
            lambda schema: schema["$defs"]["finding"].pop("additionalProperties")
        )

    def test_incomplete_required_fails_closed(self):
        def mutate(schema):
            schema["required"].remove("verdict")

        self.run_with_schema(mutate)

    def test_conditional_keyword_fails_closed(self):
        def mutate(schema):
            schema["if"] = {"properties": {"role": {"const": "implementer"}}}
            schema["then"] = {}

        self.run_with_schema(mutate)

    def test_unresolvable_ref_fails_closed(self):
        def mutate(schema):
            schema["properties"]["repository_state"] = {
                "$ref": "#/$defs/does_not_exist"
            }

        self.run_with_schema(mutate)


class FixedEnvelopeTests(RunnerTestCase):
    """RC-1: every role emits the same envelope; semantics stay in the runner."""

    def test_non_reviewer_missing_collections_is_invalid_output(self):
        final = make_result("feasibility_verifier", "codex_cli", "codex_read_only")
        del final["findings"]
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier", final=final)
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("findings", invocation["detail"])

    def test_non_reviewer_nonempty_collections_is_invalid_output(self):
        final = make_result(
            "implementer",
            "codex_cli",
            "codex_workspace_write",
            suggestions=["sneaky reviewer-style note"],
        )
        rc, artifacts, _, _ = self.run_runner(
            "implementer", allowed=("src/app.py",), final=final
        )
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("suggestions", invocation["detail"])

    def test_tests_entry_without_output_digest_is_invalid_output(self):
        final = make_result(
            "implementer",
            "codex_cli",
            "codex_workspace_write",
            tests=[{"command": "python3 -m unittest", "status": "passed"}],
        )
        rc, artifacts, _, _ = self.run_runner(
            "implementer", allowed=("src/app.py",), final=final
        )
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("output_digest", invocation["detail"])

    def test_model_mismatch_is_invalid_output(self):
        final = make_result(
            "feasibility_verifier",
            "codex_cli",
            "codex_read_only",
            model="some-other-model",
        )
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier", final=final)
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("model mismatch", invocation["detail"])


class ClaudeInvocationContractTests(RunnerTestCase):
    """RC-2: stream-json with --print requires --verbose (real 2.1.191 contract)."""

    def test_claude_argv_includes_verbose_with_stream_json(self):
        rc, _, _, _ = self.run_runner(
            "adversarial_reviewer",
            extra_env={"FAKE_ARGV_FILE": str(self.tmp / "captured-argv.json")},
        )
        self.assertEqual(rc, 0)
        argv = json.loads(
            (self.tmp / "captured-argv.json").read_text(encoding="utf-8")
        )
        self.assertIn("--verbose", argv)
        self.assertIn("-p", argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "stream-json")

    def test_fake_claude_rejects_stream_json_without_verbose(self):
        fake_claude = FAKE_BIN / "claude"
        proc = subprocess.run(
            [str(fake_claude), "-p", "--output-format", "stream-json"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(
            "--output-format=stream-json requires --verbose", proc.stderr
        )


if __name__ == "__main__":
    unittest.main()
