"""Tests for the bounded external-agent runner (dual-host contract).

All provider invocations use the fake `codex`/`claude` executables in
tests/fixtures/orchestration-agent/bin — no real provider, no network,
no quota. Target repositories are built at test time by copying
repo-template/ into a temporary directory and running `git init` there
(feasibility finding F4: no nested .git is ever committed).

Dual-host defaults exercised here:
- adversarial_reviewer under claude_hosted -> codex_cli / codex_read_only
- adversarial_reviewer under codex_hosted  -> claude_cli / claude_read_only
- implementer via the opt-in headless_cli path -> codex_cli / codex_workspace_write
- feasibility_verifier / implementer via active_host -> never spawn an external CLI
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
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
    "FAKE_REPORTED_MODEL",
    "FAKE_SESSION_ID",
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

# Packet-scoped governance identity used by every test invocation. Deliberately
# NOT a product name: the contract is that identity is arbitrary and explicit.
GOVERNANCE = {
    "governance_authority": "control-window-A",
    "authorization_issuer": "control-window-A",
    "acceptance_owner": "control-window-A",
    "finding_adjudicator": "control-window-A",
    "final_ratifier": "control-window-A",
}

EXECUTION_HOSTS = {"claude_hosted": "claude_code", "codex_hosted": "codex_desktop"}

# Default task-packet body: carries the mechanically enforced authorization.
PACKET_ALLOW = (
    "fake task packet content\n"
    "External-side-effect authorization: ALLOW_PROVIDER_INVOCATION\n"
    "Host-local execution authorization: NONE\n"
)
PACKET_HOST_LOCAL_ALLOW = (
    "fake host-local scout packet\n"
    "External-side-effect authorization: NONE\n"
    "Host-local execution authorization: ALLOW_HOST_LOCAL_CLI_INVOCATION\n"
    "Host-local reasoning effort: low\n"
    + oa.PROVIDER_TASK_START
    + "\nInspect src/app.py in read-only mode and report feasibility through "
    "summary and evidence. Do not implement or review.\n"
    + oa.PROVIDER_TASK_END
    + "\n"
)

# Default invocation path per role for test convenience (each test may override).
DEFAULT_INVOCATION = {
    "feasibility_verifier": "active_host",
    "implementer": "headless_cli",
    "adversarial_reviewer": "external_cli",
}

# provider/profile the fake result must carry, per (role, host_mode).
ROLE_DEFAULTS = {
    ("adversarial_reviewer", "claude_hosted"): ("codex_cli", "codex_read_only"),
    ("adversarial_reviewer", "codex_hosted"): ("claude_cli", "claude_read_only"),
    ("implementer", "claude_hosted"): ("codex_cli", "codex_workspace_write"),
    ("implementer", "codex_hosted"): ("codex_cli", "codex_workspace_write"),
}
AUTO_IDENTITY = object()


def default_routing():
    return json.loads(DEFAULT_ROUTING_FILE.read_text(encoding="utf-8"))


def make_result(
    role,
    provider,
    profile,
    host_mode="claude_hosted",
    invocation_path=None,
    **overrides,
):
    result = {
        "verdict": (
            "PASS_FOR_IMPLEMENTATION_AUTHORIZATION"
            if role == "feasibility_verifier"
            else "COMPLETED"
        ),
        "summary": "fake run summary",
        "evidence": ["src/app.py:1 fake evidence"],
        "stop_reason": None,
        "tests": [],
        "repository_state": {
            "pre": {"head_sha": "0" * 40, "status_short": ""},
            "post": {"head_sha": "0" * 40, "status_short": ""},
        },
    }
    if role in ("implementer", "adversarial_reviewer"):
        result["changed_files"] = []
    if role == "adversarial_reviewer":
        result.update(
            {
                "findings": [],
                "observations": [],
                "suggestions": [],
                "evidence_gaps": [],
            }
        )
    result.update(overrides)
    return result


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

    def governance_argv(self):
        return [
            "--governance-authority",
            GOVERNANCE["governance_authority"],
            "--authorization-issuer",
            GOVERNANCE["authorization_issuer"],
            "--acceptance-owner",
            GOVERNANCE["acceptance_owner"],
            "--finding-adjudicator",
            GOVERNANCE["finding_adjudicator"],
            "--final-ratifier",
            GOVERNANCE["final_ratifier"],
        ]

    def repository_identity_argv(self, repo):
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--short", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return [
            "--authoritative-plan-sha",
            "1" * 40,
            "--candidate-sha",
            "2" * 40,
            "--target-repository-head",
            head,
            "--target-repository-status",
            oa._status_evidence(status),
        ]

    def packet_with_repository_identity(
        self, packet_text, repo, plan_sha="1" * 40, candidate_sha="2" * 40
    ):
        identity = self.repository_identity_argv(repo)
        values = dict(zip(identity[::2], identity[1::2]))
        return (
            packet_text.rstrip("\n")
            + "\nAuthoritative plan commit SHA: "
            + plan_sha
            + "\nRelease/implementation candidate SHA: "
            + candidate_sha
            + "\nTarget repository HEAD: "
            + values["--target-repository-head"]
            + "\nTarget repository status/dirty-state evidence: "
            + values["--target-repository-status"]
            + "\n"
        )

    def run_runner(
        self,
        role,
        *,
        host_mode="claude_hosted",
        invocation_path=None,
        governance=True,
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
        reasoning_effort=None,
        packet_text=PACKET_ALLOW,
        flag_auth="ALLOW_PROVIDER_INVOCATION",
        host_local_auth=None,
        host_tier=None,
        authoritative_plan_sha="1" * 40,
        candidate_sha="2" * 40,
        target_repository_head=AUTO_IDENTITY,
        target_repository_status=AUTO_IDENTITY,
    ):
        if invocation_path is None:
            invocation_path = DEFAULT_INVOCATION.get(role)
        repo = repo or self.make_repo()
        artifact_dir = self.tmp / ("artifacts-" + uuid.uuid4().hex[:8])
        task_file = self.tmp / ("task-" + uuid.uuid4().hex[:8] + ".md")
        routing_path = self.write_routing(routing if routing is not None else default_routing())
        os.environ["FAKE_CLI_MODE"] = mode
        if final is None and (role, host_mode) in ROLE_DEFAULTS:
            provider, profile = ROLE_DEFAULTS[(role, host_mode)]
            final = make_result(
                role, provider, profile, host_mode=host_mode, invocation_path=invocation_path
            )
        if final is not None:
            os.environ["FAKE_FINAL_RESULT"] = json.dumps(final)
        for key, value in (extra_env or {}).items():
            os.environ[key] = value
        if invocation_path == "host_local_cli":
            os.environ.setdefault("FAKE_REPORTED_MODEL", model)
        actual_head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        actual_status = subprocess.run(
            ["git", "-C", str(repo), "status", "--short", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if target_repository_head is AUTO_IDENTITY:
            target_repository_head = actual_head
        if target_repository_status is AUTO_IDENTITY:
            target_repository_status = oa._status_evidence(actual_status)
        identity_lines = []
        for field, value in (
            ("Authoritative plan commit SHA", authoritative_plan_sha),
            ("Release/implementation candidate SHA", candidate_sha),
            ("Target repository HEAD", target_repository_head),
            ("Target repository status/dirty-state evidence", target_repository_status),
        ):
            if value is not None:
                identity_lines.append("%s: %s" % (field, value))
        task_file.write_text(
            packet_text.rstrip("\n") + "\n" + "\n".join(identity_lines) + "\n",
            encoding="utf-8",
        )
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
        if reasoning_effort is not None:
            argv += ["--reasoning-effort", reasoning_effort]
        for flag, value in (
            ("--authoritative-plan-sha", authoritative_plan_sha),
            ("--candidate-sha", candidate_sha),
            ("--target-repository-head", target_repository_head),
            ("--target-repository-status", target_repository_status),
        ):
            if value is not None:
                argv += [flag, value]
        if host_mode is not None:
            argv += ["--host-mode", host_mode]
        if invocation_path is not None:
            argv += ["--invocation-path", invocation_path]
        if host_tier is not None:
            argv += ["--host-tier", host_tier]
        if governance:
            argv += self.governance_argv()
        if flag_auth is not None:
            argv += ["--external-authorization", flag_auth]
        if host_local_auth is not None:
            argv += ["--host-local-authorization", host_local_auth]
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
# Routing validation (schema v2: governance-neutral, host-aware, tier-aware)
# ---------------------------------------------------------------------------


class RoutingValidationTests(RunnerTestCase):
    def test_valid_default_routing_loads(self):
        routing = oa.load_routing(DEFAULT_ROUTING_FILE)
        self.assertEqual(oa.validate_routing(routing), [])

    def test_default_routing_pins_no_governance_owner(self):
        # The governance owner must never be a fixed product value anywhere.
        raw = DEFAULT_ROUTING_FILE.read_text(encoding="utf-8").lower()
        self.assertNotIn("chatgpt", raw)
        routing = default_routing()
        self.assertNotIn("authority", routing)
        self.assertEqual(routing["governance"]["binding"], "task_packet")

    def test_legacy_pinned_authority_block_is_configuration_error(self):
        routing = default_routing()
        routing["authority"] = {"final_adjudicator": "chatgpt"}
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("must not be pinned", invocation["detail"])

    def test_governance_binding_tamper_is_configuration_error(self):
        routing = default_routing()
        routing["governance"]["binding"] = "chatgpt"
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_same_family_reviewer_is_configuration_error(self):
        # Claude CLI must never be the claude_hosted reviewer (self-review).
        routing = default_routing()
        routing["host_modes"]["claude_hosted"]["external_reviewer"] = {
            "provider": "claude_cli",
            "profile": "claude_read_only",
        }
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("opposing provider", invocation["detail"])

    def test_unknown_reviewer_provider_is_configuration_error(self):
        routing = default_routing()
        routing["host_modes"]["claude_hosted"]["external_reviewer"]["provider"] = (
            "openai_agentkit"
        )
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_unknown_reviewer_profile_is_configuration_error(self):
        routing = default_routing()
        routing["host_modes"]["claude_hosted"]["external_reviewer"]["profile"] = (
            "danger_full_access"
        )
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_write_capable_reviewer_profile_is_configuration_error(self):
        routing = default_routing()
        routing["host_modes"]["claude_hosted"]["external_reviewer"]["profile"] = (
            "codex_workspace_write"
        )
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_host_tier_mapped_to_external_cli_is_configuration_error(self):
        # Codex CLI must never be a host-local tier (i.e. never the default
        # implementer of any host mode).
        routing = default_routing()
        routing["host_modes"]["claude_hosted"]["local_tiers"]["worker"]["provider"] = (
            "codex_cli"
        )
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("only the corrective Codex-hosted scout", invocation["detail"])

    def test_role_bindings_tamper_is_configuration_error(self):
        routing = default_routing()
        routing["role_bindings"]["implementer"] = "external_reviewer"
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_dispatch_constraint_tamper_is_configuration_error(self):
        routing = default_routing()
        routing["constraints"]["implementer_may_dispatch_reviewer"] = True
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_auto_reviewer_dispatch_constraint_tamper_is_configuration_error(self):
        routing = default_routing()
        routing["constraints"]["host_may_auto_dispatch_reviewer"] = True
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_one_active_host_constraint_tamper_is_configuration_error(self):
        routing = default_routing()
        routing["constraints"]["one_active_host"] = False
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_missing_host_mode_definition_is_configuration_error(self):
        routing = default_routing()
        del routing["host_modes"]["codex_hosted"]
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", routing=routing)
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_headless_enabled_by_default_is_configuration_error(self):
        routing = default_routing()
        routing["headless_cli_implementation"]["enabled_by_default"] = True
        rc, artifacts, _, _ = self.run_runner("implementer", routing=routing)
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("never the default", invocation["detail"])


# ---------------------------------------------------------------------------
# Governance identity and host/tier explicitness (fail closed)
# ---------------------------------------------------------------------------


class IdentityFailClosedTests(RunnerTestCase):
    def test_missing_governance_identity_is_configuration_error(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            governance=False,
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("governance identity missing", invocation["detail"])
        self.assertFalse(argv_file.exists(), "provider spawned without governance identity")

    def test_missing_host_mode_is_configuration_error(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", host_mode=None)
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("host mode must be explicit", invocation["detail"])

    def test_unknown_host_mode_is_configuration_error(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", host_mode="dual")
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_missing_invocation_path_is_configuration_error(self):
        # Force invocation_path to stay unset by picking a role and clearing it.
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer", invocation_path="unspecified"
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("invocation path", invocation["detail"])


# ---------------------------------------------------------------------------
# Dual-host role/path matrix
# ---------------------------------------------------------------------------


class DualHostMatrixTests(RunnerTestCase):
    def test_claude_hosted_feasibility_is_active_host_only(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CAPABILITY_UNAVAILABLE")
        self.assertIn("active host", invocation["detail"])
        self.assertIn("claude_code", invocation["detail"])
        self.assertFalse(argv_file.exists(), "external CLI spawned for feasibility")

    def test_external_cli_feasibility_is_configuration_error(self):
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier", invocation_path="external_cli"
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("active-host responsibility", invocation["detail"])

    def test_claude_hosted_implementer_default_resolves_to_active_host(self):
        # Codex CLI is no longer the Claude-hosted default implementer: the
        # active_host path never spawns an external process.
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "implementer",
            invocation_path="active_host",
            host_tier="worker",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CAPABILITY_UNAVAILABLE")
        self.assertIn("worker/executor", invocation["detail"])
        self.assertIn("headless", invocation["detail"])
        self.assertFalse(argv_file.exists(), "external CLI spawned for active-host implementer")

    def test_external_cli_implementer_is_configuration_error(self):
        rc, artifacts, _, _ = self.run_runner(
            "implementer", invocation_path="external_cli"
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertIn("headless_cli", invocation["detail"])

    def test_claude_hosted_reviewer_resolves_to_codex_cli(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer")
        self.assertEqual(rc, 0)
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        self.assertEqual(invocation["provider"], "codex_cli")
        self.assertEqual(invocation["profile"], "codex_read_only")
        self.assertEqual(invocation["cli_version"], "fake-codex 0.0.1")
        self.assertEqual(invocation["host_mode"], "claude_hosted")
        self.assertEqual(invocation["execution_host"], "claude_code")
        self.assertEqual(invocation["invocation_path"], "external_cli")

    def test_codex_hosted_reviewer_resolves_to_claude_cli(self):
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer", host_mode="codex_hosted"
        )
        self.assertEqual(rc, 0)
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        self.assertEqual(invocation["provider"], "claude_cli")
        self.assertEqual(invocation["profile"], "claude_read_only")
        self.assertEqual(invocation["cli_version"], "fake-claude 0.0.1")
        self.assertEqual(invocation["host_adapter_status"], "implemented")

    def test_codex_hosted_feasibility_uses_authorized_host_local_cli_scout(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier",
            host_mode="codex_hosted",
            invocation_path="host_local_cli",
            host_tier="scout",
            model="gpt-5.6-luna",
            reasoning_effort="low",
            packet_text=PACKET_HOST_LOCAL_ALLOW,
            flag_auth=None,
            host_local_auth="ALLOW_HOST_LOCAL_CLI_INVOCATION",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
            final=make_result(
                "feasibility_verifier",
                "codex_cli",
                "codex_read_only",
            ),
        )
        self.assertEqual(rc, 0)
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        self.assertEqual(invocation["provider"], "codex_cli")
        self.assertEqual(invocation["profile"], "codex_read_only")
        self.assertEqual(invocation["host_tier"], "scout")
        self.assertEqual(invocation["invocation_path"], "host_local_cli")
        self.assertTrue(argv_file.exists())

    def test_codex_hosted_implementer_requires_native_host(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "implementer",
            host_mode="codex_hosted",
            invocation_path="active_host",
            host_tier="executor",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CAPABILITY_UNAVAILABLE")
        self.assertIn("host-native execution required", invocation["detail"])
        self.assertIn("codex_desktop", invocation["detail"])
        self.assertFalse(argv_file.exists(), "external CLI spawned for implementer")

    def test_headless_implementer_is_recorded_as_headless(self):
        rc, artifacts, _, _ = self.run_runner(
            "implementer",
            mode="write-file",
            allowed=("src/app.py",),
            extra_env={"FAKE_WRITE_PATH": "src/app.py"},
            final=make_result(
                "implementer",
                "codex_cli",
                "codex_workspace_write",
                changed_files=["src/app.py"],
            ),
        )
        self.assertEqual(rc, 0)
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        self.assertEqual(invocation["invocation_path"], "headless_cli")
        self.assertEqual(invocation["profile"], "codex_workspace_write")


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
# External reviewer read-only paths (codex transport under claude_hosted)
# ---------------------------------------------------------------------------


class ExternalReviewerReadOnlyTests(RunnerTestCase):
    def test_read_only_happy_path_success(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer")
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
            "adversarial_reviewer",
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
            "adversarial_reviewer",
            mode="write-file",
            extra_env={"FAKE_WRITE_PATH": "NEW_FILE.txt"},
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "READ_ONLY_MUTATION")
        self.assertTrue((repo / "NEW_FILE.txt").is_file())

    def test_closed_gate_fixture_is_flagged_and_never_reverted(self):
        template_text = (REPO_TEMPLATE / "CLOSED_GATE.md").read_text(encoding="utf-8")
        rc, artifacts, repo, _ = self.run_runner(
            "adversarial_reviewer",
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
            "adversarial_reviewer",
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
        packet_sent = stdin_capture.read_text(encoding="utf-8")
        self.assertTrue(packet_sent.startswith(PACKET_ALLOW))
        self.assertIn("Target repository HEAD:", packet_sent)

    def test_headless_implementation_argv_requests_network_disabled(self):
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
            "adversarial_reviewer",
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
            host_mode="codex_hosted",
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
# Headless implementation changed-path validation
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
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", mode="nonzero")
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
            "adversarial_reviewer",
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
        task_file.write_text(
            self.packet_with_repository_identity(PACKET_ALLOW, repo),
            encoding="utf-8",
        )
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
                "adversarial_reviewer",
                "--host-mode",
                "claude_hosted",
                "--invocation-path",
                "external_cli",
                *self.governance_argv(),
                "--external-authorization",
                "ALLOW_PROVIDER_INVOCATION",
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
                *self.repository_identity_argv(repo),
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
            "adversarial_reviewer",
            extra_env={"FAKE_STDERR_TEXT": "stderr-marker-line"},
        )
        self.assertEqual(rc, 0)
        stdout_text = (artifacts / "stdout.jsonl").read_text(encoding="utf-8")
        stderr_text = (artifacts / "stderr.log").read_text(encoding="utf-8")
        self.assertIn("stderr-marker-line", stderr_text)
        self.assertNotIn("stderr-marker-line", stdout_text)
        self.assertIn("thread.started", stdout_text)
        self.assertNotIn("thread.started", stderr_text)


# ---------------------------------------------------------------------------
# Structured output validation
# ---------------------------------------------------------------------------


class StructuredOutputTests(RunnerTestCase):
    def test_invalid_final_json_is_invalid_output(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", mode="invalid-json")
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "INVALID_OUTPUT")

    def test_missing_final_result_is_invalid_output(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", mode="missing-final")
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "INVALID_OUTPUT")

    def test_deleted_transcript_is_transcript_incomplete(self):
        artifact_dir = self.tmp / ("artifacts-" + uuid.uuid4().hex[:8])
        # FAKE_DELETE_PATH must point at the runner-owned stdout artifact.
        rc = None
        repo = self.make_repo()
        task_file = self.tmp / "task-del.md"
        task_file.write_text(
            self.packet_with_repository_identity(PACKET_ALLOW, repo),
            encoding="utf-8",
        )
        routing_path = self.write_routing(default_routing())
        os.environ["FAKE_CLI_MODE"] = "delete-transcript"
        os.environ["FAKE_DELETE_PATH"] = str(artifact_dir / "stdout.jsonl")
        os.environ["FAKE_FINAL_RESULT"] = json.dumps(
            make_result("adversarial_reviewer", "codex_cli", "codex_read_only")
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = oa.main(
                [
                    "run",
                    "--routing-file",
                    str(routing_path),
                    "--role",
                    "adversarial_reviewer",
                    "--host-mode",
                    "claude_hosted",
                    "--invocation-path",
                    "external_cli",
                    *self.governance_argv(),
                    "--external-authorization",
                    "ALLOW_PROVIDER_INVOCATION",
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
                    *self.repository_identity_argv(repo),
                ]
            )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifact_dir, "TRANSCRIPT_INCOMPLETE")

    def test_provider_cannot_supply_role_provenance(self):
        final = make_result("adversarial_reviewer", "codex_cli", "codex_read_only")
        final["role"] = "implementer"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            final=final,
        )
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("controller-owned", invocation["detail"])

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
                "adversarial_reviewer", "codex_cli", "codex_read_only", findings=[finding]
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
                "adversarial_reviewer", "codex_cli", "codex_read_only", findings=[finding]
            ),
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "INVALID_OUTPUT")

    def test_claude_reviewer_happy_path_success(self):
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer", host_mode="codex_hosted"
        )
        self.assertEqual(rc, 0)
        self.assert_outcome(artifacts, "SUCCESS")
        final = json.loads((artifacts / "final-result.json").read_text(encoding="utf-8"))
        for field in ("findings", "observations", "suggestions", "evidence_gaps"):
            self.assertEqual(final["provider_result"][field], [])

    def test_feasibility_verdicts_are_enforced_by_validate_result(self):
        # Feasibility runs on the active host and never reaches this runner's
        # spawn path, but the shared semantic validator still enforces the
        # three-verdict contract for any feasibility result it is handed.
        good = make_result(
            "feasibility_verifier",
            "codex_cli",
            "codex_read_only",
            invocation_path="external_cli",
        )
        canonical_good = oa.normalize_provider_result(
            good, "feasibility_verifier"
        )
        self.assertEqual(
            oa.validate_result(canonical_good, "feasibility_verifier"),
            [],
        )
        bad = dict(canonical_good, verdict="LOOKS_FINE")
        errors = oa.validate_result(bad, "feasibility_verifier")
        self.assertTrue(any("feasibility verdict" in e for e in errors))


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


class ManifestTests(RunnerTestCase):
    def run_and_verify(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer")
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

    def test_no_pinned_governance_owner_in_source(self):
        self.assertNotIn("chatgpt", self.SOURCE.lower())
        self.assertNotIn("FIXED_AUTHORITY", self.SOURCE)

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

    def test_canonical_schema_separates_provenance_from_provider_result(self):
        self.assertEqual(set(self.SCHEMA["required"]), {
            "schema_version", "provenance", "provider_result"
        })
        required = set(self.SCHEMA["$defs"]["provenance"]["required"])
        for field in (
            "governance_identity",
            "authoritative_plan_sha",
            "candidate_sha",
            "target_repository_head",
            "host_mode",
            "execution_host",
            "host_tier",
            "invocation_path",
            "role",
            "provider",
            "profile",
            "requested_model",
            "resolved_model",
            "reported_model",
            "requested_reasoning_effort",
            "resolved_reasoning_effort",
            "reported_reasoning_effort",
            "session_id",
        ):
            self.assertIn(field, required, field)
        self.assertEqual(self.SCHEMA["properties"]["schema_version"]["enum"], [3])
        gov = self.SCHEMA["$defs"]["provenance"]["properties"]["governance_identity"]
        self.assertEqual(
            set(gov["required"]),
            {
                "governance_authority",
                "authorization_issuer",
                "acceptance_owner",
                "finding_adjudicator",
                "final_ratifier",
            },
        )


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
                "adversarial_reviewer",
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
        def mutate(schema):
            schema["$defs"]["finding"].pop("additionalProperties")
        self.run_with_schema(mutate)

    def test_incomplete_required_fails_closed(self):
        def mutate(schema):
            schema["$defs"]["provider_result_adversarial_reviewer"][
                "required"
            ].remove("verdict")

        self.run_with_schema(mutate)

    def test_conditional_keyword_fails_closed(self):
        def mutate(schema):
            schema["if"] = {"properties": {"role": {"const": "implementer"}}}
            schema["then"] = {}

        self.run_with_schema(mutate)

    def test_unresolvable_ref_fails_closed(self):
        def mutate(schema):
            schema["properties"]["provider_result"] = {
                "$ref": "#/$defs/does_not_exist"
            }

        self.run_with_schema(mutate)


class RoleSpecificEnvelopeTests(RunnerTestCase):
    """C3: providers see role surfaces; canonical results stay uniform."""

    def test_implementer_missing_reviewer_collections_is_normalized(self):
        final = make_result("implementer", "codex_cli", "codex_workspace_write")
        rc, artifacts, _, _ = self.run_runner(
            "implementer", allowed=("src/app.py",), final=final
        )
        self.assertEqual(rc, 0)
        self.assert_outcome(artifacts, "SUCCESS")
        canonical = json.loads((artifacts / "final-result.json").read_text())
        for field in oa.REVIEWER_COLLECTIONS:
            self.assertEqual(canonical["provider_result"][field], [])

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

    def test_reported_model_alias_expansion_is_recorded_not_rejected(self):
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            model="sol",
            extra_env={"FAKE_REPORTED_MODEL": "gpt-5.6-sol"},
        )
        self.assertEqual(rc, 0)
        self.assert_outcome(artifacts, "SUCCESS")
        final = json.loads((artifacts / "final-result.json").read_text())
        self.assertEqual(final["provenance"]["requested_model"], "sol")
        self.assertEqual(final["provenance"]["reported_model"], "gpt-5.6-sol")

    def test_rewritten_governance_identity_is_invalid_output(self):
        final = make_result("adversarial_reviewer", "codex_cli", "codex_read_only")
        final["governance_identity"] = dict(
            GOVERNANCE, final_ratifier="the-reviewer-itself"
        )
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", final=final)
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("controller-owned", invocation["detail"])

    def test_host_mode_mismatch_is_invalid_output(self):
        final = make_result(
            "adversarial_reviewer",
            "codex_cli",
            "codex_read_only",
            host_mode="codex_hosted",
        )
        final["execution_host"] = "claude_code"
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", final=final)
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("controller-owned", invocation["detail"])

    def test_external_reviewer_reporting_host_tier_is_invalid_output(self):
        final = make_result(
            "adversarial_reviewer", "codex_cli", "codex_read_only", host_tier="executor"
        )
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer", final=final)
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("controller-owned", invocation["detail"])


class ArbitraryAuthorityTests(RunnerTestCase):
    """F-X1: governance authority is packet-scoped, never derived or pinned."""

    CUSTOM = {
        "governance_authority": "acme-review-board",
        "authorization_issuer": "release-manager-42",
        "acceptance_owner": "qa-lead-7",
        "finding_adjudicator": "independent-arbiter",
        "final_ratifier": "steering-committee",
    }

    def custom_argv(self):
        return [
            "--governance-authority",
            self.CUSTOM["governance_authority"],
            "--authorization-issuer",
            self.CUSTOM["authorization_issuer"],
            "--acceptance-owner",
            self.CUSTOM["acceptance_owner"],
            "--finding-adjudicator",
            self.CUSTOM["finding_adjudicator"],
            "--final-ratifier",
            self.CUSTOM["final_ratifier"],
        ]

    def run_with_custom_identity(self):
        repo = self.make_repo()
        artifact_dir = self.tmp / ("artifacts-" + uuid.uuid4().hex[:8])
        task_file = self.tmp / "task-custom-authority.md"
        task_file.write_text(
            self.packet_with_repository_identity(PACKET_ALLOW, repo),
            encoding="utf-8",
        )
        routing_path = self.write_routing(default_routing())
        os.environ["FAKE_CLI_MODE"] = "success"
        final = make_result("adversarial_reviewer", "codex_cli", "codex_read_only")
        os.environ["FAKE_FINAL_RESULT"] = json.dumps(final)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = oa.main(
                [
                    "run",
                    "--routing-file",
                    str(routing_path),
                    "--role",
                    "adversarial_reviewer",
                    "--host-mode",
                    "claude_hosted",
                    "--invocation-path",
                    "external_cli",
                    *self.custom_argv(),
                    "--external-authorization",
                    "ALLOW_PROVIDER_INVOCATION",
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
                    *self.repository_identity_argv(repo),
                ]
            )
        return rc, artifact_dir

    def test_arbitrary_explicit_authority_identity_is_accepted(self):
        rc, artifacts = self.run_with_custom_identity()
        self.assertEqual(rc, 0)
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        self.assertEqual(invocation["governance_identity"], self.CUSTOM)

    def test_authority_is_controller_injected_not_derived_from_provider(self):
        rc, artifacts = self.run_with_custom_identity()
        self.assertEqual(rc, 0)
        invocation = self.read_invocation(artifacts)
        # The recorded identity is exactly the packet input; no field equals
        # the host, provider, or any product identity it could be derived from.
        self.assertEqual(invocation["governance_identity"], self.CUSTOM)
        derived_candidates = {
            invocation["execution_host"],
            invocation["provider"],
            invocation["profile"],
            invocation["host_mode"],
            "chatgpt",
            "claude",
            "codex",
        }
        for value in invocation["governance_identity"].values():
            self.assertNotIn(value, derived_candidates, value)
        final = json.loads((artifacts / "final-result.json").read_text())
        self.assertEqual(final["provenance"]["governance_identity"], self.CUSTOM)
        self.assertNotIn("governance_identity", final["provider_result"])

    def test_partially_missing_authority_fields_fail_closed(self):
        # Drop exactly one identity field: the runner must name it and stop.
        argv_without_ratifier = self.governance_argv()[:-2]
        repo = self.make_repo()
        artifact_dir = self.tmp / "artifacts-partial-authority"
        task_file = self.tmp / "task-partial-authority.md"
        task_file.write_text(
            self.packet_with_repository_identity(PACKET_ALLOW, repo),
            encoding="utf-8",
        )
        routing_path = self.write_routing(default_routing())
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = oa.main(
                [
                    "run",
                    "--routing-file",
                    str(routing_path),
                    "--role",
                    "adversarial_reviewer",
                    "--host-mode",
                    "claude_hosted",
                    "--invocation-path",
                    "external_cli",
                    *argv_without_ratifier,
                    "--external-authorization",
                    "ALLOW_PROVIDER_INVOCATION",
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
                    *self.repository_identity_argv(repo),
                ]
            )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifact_dir, "CONFIGURATION_ERROR")
        self.assertIn("final_ratifier", invocation["detail"])


class ExternalAuthorizationTests(RunnerTestCase):
    """F-X2: External-side-effect authorization is mechanically enforced."""

    def assert_not_spawned(self, artifacts, argv_file):
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertFalse(
            argv_file.exists(), "provider spawned despite missing/invalid authorization"
        )
        # Preflight failure evidence is preserved as an artifact bundle.
        self.assertTrue((artifacts / "invocation.json").is_file())
        self.assertTrue((artifacts / "manifest.sha256").is_file())
        return invocation

    def test_valid_authorization_spawns_provider(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 0)
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        self.assertEqual(
            invocation["external_side_effect_authorization"], "ALLOW_PROVIDER_INVOCATION"
        )
        self.assertTrue(argv_file.exists())

    def test_missing_packet_field_prevents_spawn(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            packet_text="fake task packet content\n",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_not_spawned(artifacts, argv_file)
        self.assertIn("does not carry", invocation["detail"])

    def test_deny_value_prevents_spawn(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            packet_text="External-side-effect authorization: DENY\n",
            flag_auth="DENY",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_not_spawned(artifacts, argv_file)
        self.assertIn("not authorized", invocation["detail"])

    def test_unknown_value_prevents_spawn(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            packet_text="External-side-effect authorization: ALLOW_EVERYTHING\n",
            flag_auth="ALLOW_EVERYTHING",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        self.assert_not_spawned(artifacts, argv_file)

    def test_none_value_prevents_spawn(self):
        # An implementer-style NONE packet can never authorize a reviewer
        # invocation: each external call needs its own packet authorization.
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            packet_text=(
                "| External-side-effect authorization | NONE（不得 dispatch reviewer） |\n"
            ),
            flag_auth="NONE",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_not_spawned(artifacts, argv_file)
        self.assertIn("not authorized", invocation["detail"])

    def test_packet_flag_mismatch_prevents_spawn(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            packet_text=PACKET_ALLOW,
            flag_auth="DENY",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_not_spawned(artifacts, argv_file)
        self.assertIn("mismatch", invocation["detail"])

    def test_flag_alone_without_packet_field_prevents_spawn(self):
        # A caller-side value can never stand in for the packet authorization.
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            packet_text="fake task packet content\n",
            flag_auth="ALLOW_PROVIDER_INVOCATION",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        self.assert_not_spawned(artifacts, argv_file)

    def test_packet_alone_without_flag_prevents_spawn(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            packet_text=PACKET_ALLOW,
            flag_auth=None,
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_not_spawned(artifacts, argv_file)
        self.assertIn("--external-authorization", invocation["detail"])

    def test_ambiguous_conflicting_values_prevent_spawn(self):
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            packet_text=(
                "External-side-effect authorization: ALLOW_PROVIDER_INVOCATION\n"
                "External-side-effect authorization: NONE\n"
            ),
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_not_spawned(artifacts, argv_file)
        self.assertIn("ambiguous", invocation["detail"])

    def test_headless_implementer_also_requires_packet_authorization(self):
        # Implementer-path spawns are gated by the same per-packet check; an
        # authorization on some other packet never carries over.
        argv_file = self.tmp / "captured-argv.json"
        rc, artifacts, _, _ = self.run_runner(
            "implementer",
            allowed=("src/app.py",),
            packet_text="| External-side-effect authorization | NONE |\n",
            flag_auth="NONE",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        self.assert_not_spawned(artifacts, argv_file)

    def test_parser_accepts_table_cell_form_with_annotation(self):
        value, errors = oa.parse_packet_external_authorization(
            "| External-side-effect authorization | "
            "ALLOW_PROVIDER_INVOCATION（僅此一次 Codex CLI 呼叫） |\n"
        )
        self.assertEqual(errors, [])
        self.assertEqual(value, "ALLOW_PROVIDER_INVOCATION")


class CorrectiveC2ContractTests(RunnerTestCase):
    """C2: host-local scout, immutable provenance, and repository identities."""

    def scout_kwargs(self):
        return {
            "host_mode": "codex_hosted",
            "invocation_path": "host_local_cli",
            "host_tier": "scout",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "low",
            "packet_text": PACKET_HOST_LOCAL_ALLOW,
            "flag_auth": None,
            "host_local_auth": "ALLOW_HOST_LOCAL_CLI_INVOCATION",
            "final": make_result(
                "feasibility_verifier", "codex_cli", "codex_read_only"
            ),
        }

    def test_external_reviewer_token_cannot_authorize_host_local_scout(self):
        kwargs = self.scout_kwargs()
        kwargs.update(
            packet_text=(
                PACKET_ALLOW
                + "Host-local reasoning effort: low\n"
            ),
            flag_auth="ALLOW_PROVIDER_INVOCATION",
        )
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier", **kwargs)
        self.assertEqual(rc, 2)
        self.assertIn("cannot authorize host_local_cli", self.assert_outcome(
            artifacts, "CONFIGURATION_ERROR"
        )["detail"])

    def test_host_local_token_cannot_authorize_external_reviewer(self):
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            packet_text=PACKET_HOST_LOCAL_ALLOW,
            flag_auth=None,
            host_local_auth="ALLOW_HOST_LOCAL_CLI_INVOCATION",
        )
        self.assertEqual(rc, 2)
        self.assertIn("cannot authorize external_cli", self.assert_outcome(
            artifacts, "CONFIGURATION_ERROR"
        )["detail"])

    def test_host_local_scout_write_profile_is_rejected_before_spawn(self):
        data = default_routing()
        data["host_modes"]["codex_hosted"]["local_tiers"]["scout"]["profile"] = (
            "codex_workspace_write"
        )
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier", routing=data, **self.scout_kwargs()
        )
        self.assertEqual(rc, 2)
        self.assert_outcome(artifacts, "CONFIGURATION_ERROR")

    def test_host_local_scout_model_substitution_is_rejected(self):
        kwargs = self.scout_kwargs()
        kwargs["model"] = "gpt-5.6-sol"
        rc, artifacts, _, _ = self.run_runner("feasibility_verifier", **kwargs)
        self.assertEqual(rc, 2)
        self.assertIn("gpt-5.6-luna", self.assert_outcome(
            artifacts, "CONFIGURATION_ERROR"
        )["detail"])

    def test_missing_target_repository_head_fails_closed(self):
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer", target_repository_head=None
        )
        self.assertEqual(rc, 2)
        self.assertIn("target repository HEAD", self.assert_outcome(
            artifacts, "CONFIGURATION_ERROR"
        )["detail"])

    def test_missing_target_dirty_state_evidence_fails_closed(self):
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer", target_repository_status=None
        )
        self.assertEqual(rc, 2)
        self.assertIn("dirty-state evidence", self.assert_outcome(
            artifacts, "CONFIGURATION_ERROR"
        )["detail"])

    def test_target_repository_head_mismatch_fails_before_spawn(self):
        argv_file = self.tmp / "not-spawned.json"
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            target_repository_head="3" * 40,
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
        )
        self.assertEqual(rc, 2)
        self.assertIn("HEAD mismatch", self.assert_outcome(
            artifacts, "CONFIGURATION_ERROR"
        )["detail"])
        self.assertFalse(argv_file.exists())

    def test_plan_candidate_and_target_head_may_all_differ(self):
        rc, artifacts, repo, _ = self.run_runner(
            "adversarial_reviewer",
            authoritative_plan_sha="a" * 40,
            candidate_sha="b" * 40,
        )
        self.assertEqual(rc, 0)
        final = json.loads((artifacts / "final-result.json").read_text())
        provenance = final["provenance"]
        self.assertEqual(provenance["authoritative_plan_sha"], "a" * 40)
        self.assertEqual(provenance["candidate_sha"], "b" * 40)
        self.assertEqual(
            provenance["target_repository_head"],
            subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
        )

    def test_provider_transport_schema_contains_only_substantive_fields(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer")
        self.assertEqual(rc, 0)
        schema = json.loads((artifacts / "provider-result.schema.json").read_text())
        self.assertEqual(set(schema["required"]), set(oa.PROVIDER_RESULT_REQUIRED))
        for field in ("governance_identity", "host_mode", "model", "session_id"):
            self.assertNotIn(field, schema["properties"])

    def test_final_result_has_controller_provenance_and_provider_result(self):
        rc, artifacts, _, _ = self.run_runner("adversarial_reviewer")
        self.assertEqual(rc, 0)
        final = json.loads((artifacts / "final-result.json").read_text())
        self.assertEqual(set(final), {"schema_version", "provenance", "provider_result"})
        self.assertEqual(final["schema_version"], 3)
        self.assertEqual(final["provenance"]["governance_identity"], GOVERNANCE)

    def test_provider_provenance_attempt_never_creates_canonical_artifact(self):
        result = make_result("adversarial_reviewer", "codex_cli", "codex_read_only")
        result["provenance"] = {"final_ratifier": "provider"}
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer", final=result
        )
        self.assertEqual(rc, 1)
        self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertFalse((artifacts / "final-result.json").exists())

    def test_claude_substantive_result_accepts_reported_alias_expansion(self):
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer",
            host_mode="codex_hosted",
            model="sonnet",
            extra_env={"FAKE_REPORTED_MODEL": "claude-sonnet-4-6"},
        )
        self.assertEqual(rc, 0)
        final = json.loads((artifacts / "final-result.json").read_text())
        self.assertEqual(final["provenance"]["requested_model"], "sonnet")
        self.assertEqual(
            final["provenance"]["reported_model"], "claude-sonnet-4-6"
        )


class ScoutLowEffortCorrectiveTests(RunnerTestCase):
    """Pin Codex-hosted scout to Luna/low before any provider spawn."""

    def scout_kwargs(self):
        return {
            "host_mode": "codex_hosted",
            "invocation_path": "host_local_cli",
            "host_tier": "scout",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "low",
            "packet_text": PACKET_HOST_LOCAL_ALLOW,
            "flag_auth": None,
            "host_local_auth": "ALLOW_HOST_LOCAL_CLI_INVOCATION",
            "final": make_result(
                "feasibility_verifier", "codex_cli", "codex_read_only"
            ),
        }

    def run_scout(self, **overrides):
        kwargs = self.scout_kwargs()
        kwargs.update(overrides)
        return self.run_runner("feasibility_verifier", **kwargs)

    def assert_pre_spawn_failure(self, **overrides):
        argv_file = self.tmp / ("not-spawned-" + uuid.uuid4().hex + ".json")
        extra_env = dict(overrides.pop("extra_env", {}))
        extra_env["FAKE_ARGV_FILE"] = str(argv_file)
        rc, artifacts, _, _ = self.run_scout(
            extra_env=extra_env, **overrides
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertFalse(argv_file.exists(), invocation["detail"])
        return invocation

    def test_fake_codex_argv_pins_low_and_ignores_global_config(self):
        argv_file = self.tmp / "captured-argv.json"
        codex_home = self.tmp / "codex-home"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text(
            'model_reasoning_effort = "high"\n',
            encoding="utf-8",
        )
        rc, artifacts, _, _ = self.run_scout(
            extra_env={
                "FAKE_ARGV_FILE": str(argv_file),
                "CODEX_HOME": str(codex_home),
            }
        )
        self.assertEqual(rc, 0)
        argv = json.loads(argv_file.read_text(encoding="utf-8"))
        self.assertIn("--ignore-user-config", argv)
        self.assertIn("--strict-config", argv)
        self.assertIn("model_reasoning_effort=low", argv)
        effort_index = argv.index("model_reasoning_effort=low")
        self.assertEqual(argv[effort_index - 1], "-c")
        self.assertNotIn("model_reasoning_effort=high", argv)
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-5.6-luna")
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        self.assertIs(invocation["user_config_ignored"], True)
        self.assertIs(invocation["strict_config"], True)

    def test_invocation_and_provenance_preserve_requested_resolved_identity(self):
        rc, artifacts, _, _ = self.run_scout()
        self.assertEqual(rc, 0)
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        for source in (
            invocation,
            json.loads((artifacts / "final-result.json").read_text())[
                "provenance"
            ],
        ):
            self.assertEqual(source["requested_model"], "gpt-5.6-luna")
            self.assertEqual(source["resolved_model"], "gpt-5.6-luna")
            self.assertEqual(source["requested_reasoning_effort"], "low")
            self.assertEqual(source["resolved_reasoning_effort"], "low")
            self.assertEqual(source["reported_model"], "gpt-5.6-luna")
            self.assertIsNone(source["reported_reasoning_effort"])

    def test_missing_cli_effort_fails_before_spawn(self):
        invocation = self.assert_pre_spawn_failure(reasoning_effort=None)
        self.assertIn("reasoning_effort=low", invocation["detail"])

    def test_medium_cli_effort_fails_before_spawn(self):
        invocation = self.assert_pre_spawn_failure(reasoning_effort="medium")
        self.assertIn("reasoning_effort=low", invocation["detail"])

    def test_high_cli_effort_fails_before_spawn(self):
        invocation = self.assert_pre_spawn_failure(reasoning_effort="high")
        self.assertIn("reasoning_effort=low", invocation["detail"])

    def test_missing_routing_effort_fails_before_spawn(self):
        data = default_routing()
        del data["host_modes"]["codex_hosted"]["local_tiers"]["scout"][
            "reasoning_effort"
        ]
        invocation = self.assert_pre_spawn_failure(routing=data)
        self.assertIn("routing validation failed", invocation["detail"])

    def test_medium_routing_effort_fails_before_spawn(self):
        data = default_routing()
        data["host_modes"]["codex_hosted"]["local_tiers"]["scout"][
            "reasoning_effort"
        ] = "medium"
        invocation = self.assert_pre_spawn_failure(routing=data)
        self.assertIn("routing validation failed", invocation["detail"])

    def test_missing_packet_effort_fails_before_spawn(self):
        packet = PACKET_HOST_LOCAL_ALLOW.replace(
            "Host-local reasoning effort: low\n", ""
        )
        invocation = self.assert_pre_spawn_failure(packet_text=packet)
        self.assertIn("packet, routing, and CLI", invocation["detail"])

    def test_medium_packet_effort_fails_before_spawn(self):
        packet = PACKET_HOST_LOCAL_ALLOW.replace(
            "Host-local reasoning effort: low",
            "Host-local reasoning effort: medium",
        )
        invocation = self.assert_pre_spawn_failure(packet_text=packet)
        self.assertIn("packet, routing, and CLI", invocation["detail"])

    def test_provider_cannot_supply_controller_reasoning_effort(self):
        final = make_result(
            "feasibility_verifier",
            "codex_cli",
            "codex_read_only",
            requested_reasoning_effort="high",
        )
        rc, artifacts, _, _ = self.run_scout(final=final)
        self.assertEqual(rc, 1)
        detail = self.assert_outcome(artifacts, "INVALID_OUTPUT")["detail"]
        self.assertIn("controller-owned", detail)
        self.assertFalse((artifacts / "final-result.json").exists())

    def test_reported_effort_mismatch_is_invalid_output(self):
        original = oa._extract_provider_metadata
        oa._extract_provider_metadata = lambda _: {
            "reported_model": "gpt-5.6-luna",
            "reported_reasoning_effort": "high",
            "session_id": "00000000-0000-0000-0000-000000000001",
        }
        try:
            rc, artifacts, _, _ = self.run_scout()
        finally:
            oa._extract_provider_metadata = original
        self.assertEqual(rc, 1)
        detail = self.assert_outcome(artifacts, "INVALID_OUTPUT")["detail"]
        self.assertIn("reported reasoning effort", detail)

    def test_reported_model_mismatch_is_invalid_output(self):
        rc, artifacts, _, _ = self.run_scout(
            extra_env={"FAKE_REPORTED_MODEL": "gpt-5.6-terra"}
        )
        self.assertEqual(rc, 1)
        detail = self.assert_outcome(artifacts, "INVALID_OUTPUT")["detail"]
        self.assertIn("reported model", detail)

    def test_schema_provenance_requires_model_and_effort_resolution(self):
        schema = json.loads(
            (PLUGIN_ROOT / "examples" / "schemas" / "orchestration-result.schema.json")
            .read_text(encoding="utf-8")
        )
        required = set(schema["$defs"]["provenance"]["required"])
        self.assertTrue(
            {
                "requested_model",
                "resolved_model",
                "reported_model",
                "requested_reasoning_effort",
                "resolved_reasoning_effort",
                "reported_reasoning_effort",
            }.issubset(required)
        )


class ScoutProviderPromptSeparationTests(RunnerTestCase):
    """Controller packet stays auditable; Luna receives substantive task only."""

    def scout_kwargs(self, packet=PACKET_HOST_LOCAL_ALLOW, final=None):
        return {
            "host_mode": "codex_hosted",
            "invocation_path": "host_local_cli",
            "host_tier": "scout",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "low",
            "packet_text": packet,
            "flag_auth": None,
            "host_local_auth": "ALLOW_HOST_LOCAL_CLI_INVOCATION",
            "final": final
            if final is not None
            else make_result(
                "feasibility_verifier", "codex_cli", "codex_read_only"
            ),
        }

    def assert_pre_spawn_failure(self, packet):
        argv_file = self.tmp / ("not-spawned-" + uuid.uuid4().hex + ".json")
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier",
            extra_env={"FAKE_ARGV_FILE": str(argv_file)},
            **self.scout_kwargs(packet),
        )
        self.assertEqual(rc, 2)
        invocation = self.assert_outcome(artifacts, "CONFIGURATION_ERROR")
        self.assertFalse(argv_file.exists(), invocation["detail"])
        return invocation

    def test_luna_receives_only_substantive_task_and_packet_is_preserved(self):
        stdin_capture = self.tmp / "captured-scout-stdin.md"
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier",
            extra_env={"FAKE_STDIN_FILE": str(stdin_capture)},
            **self.scout_kwargs(),
        )
        self.assertEqual(rc, 0)
        provider_prompt = stdin_capture.read_text(encoding="utf-8")
        self.assertEqual(
            provider_prompt,
            (artifacts / "provider-task.md").read_text(encoding="utf-8"),
        )
        self.assertIn("Provider execution phase: `substantive_only`", provider_prompt)
        self.assertIn("Inspect src/app.py", provider_prompt)
        for controller_only in (
            "Authoritative plan commit SHA",
            "Release/implementation candidate SHA",
            "Target repository HEAD",
            "Governance authority",
            "ALLOW_HOST_LOCAL_CLI_INVOCATION",
        ):
            self.assertNotIn(controller_only, provider_prompt)
        complete_packet = (artifacts / "task.md").read_text(encoding="utf-8")
        self.assertIn("Authoritative plan commit SHA", complete_packet)
        self.assertIn("Release/implementation candidate SHA", complete_packet)
        self.assertIn("Target repository HEAD", complete_packet)
        self.assertIn("ALLOW_HOST_LOCAL_CLI_INVOCATION", complete_packet)
        invocation = self.assert_outcome(artifacts, "SUCCESS")
        self.assertEqual(invocation["provider_task_mode"], "substantive_only")
        self.assertEqual(
            invocation["provider_task_sha256"],
            hashlib.sha256(provider_prompt.encode("utf-8")).hexdigest(),
        )

    def test_missing_substantive_task_markers_fail_before_spawn(self):
        packet = PACKET_HOST_LOCAL_ALLOW.replace(oa.PROVIDER_TASK_START, "")
        invocation = self.assert_pre_spawn_failure(packet)
        self.assertIn("exactly one provider substantive task start", invocation["detail"])

    def test_duplicate_substantive_task_marker_fails_before_spawn(self):
        packet = PACKET_HOST_LOCAL_ALLOW.replace(
            oa.PROVIDER_TASK_START,
            oa.PROVIDER_TASK_START + "\n" + oa.PROVIDER_TASK_START,
        )
        invocation = self.assert_pre_spawn_failure(packet)
        self.assertIn("exactly one provider substantive task start", invocation["detail"])

    def test_reversed_substantive_task_markers_fail_before_spawn(self):
        packet = PACKET_HOST_LOCAL_ALLOW.replace(
            oa.PROVIDER_TASK_START, "<!-- TEMP MARKER -->"
        ).replace(oa.PROVIDER_TASK_END, oa.PROVIDER_TASK_START).replace(
            "<!-- TEMP MARKER -->", oa.PROVIDER_TASK_END
        )
        invocation = self.assert_pre_spawn_failure(packet)
        self.assertIn("out of order", invocation["detail"])

    def test_controller_identity_inside_substantive_task_fails_before_spawn(self):
        packet = PACKET_HOST_LOCAL_ALLOW.replace(
            "Inspect src/app.py",
            "Governance authority: do not repeat. Inspect src/app.py",
        )
        invocation = self.assert_pre_spawn_failure(packet)
        self.assertIn("controller-only packet labels", invocation["detail"])
        self.assertIn("Governance authority", invocation["detail"])

    def test_feasibility_transport_schema_constrains_verdict_enum(self):
        schema = json.loads(
            (PLUGIN_ROOT / "examples" / "schemas" / "orchestration-result.schema.json")
            .read_text(encoding="utf-8")
        )
        transport = oa.extract_provider_result_schema(
            schema, "feasibility_verifier"
        )
        self.assertEqual(
            set(transport["properties"]["verdict"]["enum"]),
            set(oa.FEASIBILITY_VERDICTS),
        )

    def test_blocked_verdict_is_rejected_by_transport_validation(self):
        final = make_result(
            "feasibility_verifier",
            "codex_cli",
            "codex_read_only",
            verdict="BLOCKED",
        )
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier", **self.scout_kwargs(final=final)
        )
        self.assertEqual(rc, 1)
        invocation = self.assert_outcome(artifacts, "INVALID_OUTPUT")
        self.assertIn("provider transport verdict", invocation["detail"])
        self.assertFalse((artifacts / "final-result.json").exists())


class CorrectiveC3RoleSchemaTests(RunnerTestCase):
    """C3: select narrow role transports and normalize canonical empties."""

    SCHEMA = json.loads(
        (PLUGIN_ROOT / "examples" / "schemas" / "orchestration-result.schema.json")
        .read_text(encoding="utf-8")
    )

    def scout_kwargs(self, final=None):
        return {
            "host_mode": "codex_hosted",
            "invocation_path": "host_local_cli",
            "host_tier": "scout",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "low",
            "packet_text": PACKET_HOST_LOCAL_ALLOW,
            "flag_auth": None,
            "host_local_auth": "ALLOW_HOST_LOCAL_CLI_INVOCATION",
            "final": final
            if final is not None
            else make_result(
                "feasibility_verifier", "codex_cli", "codex_read_only"
            ),
        }

    def test_single_schema_ssot_contains_three_role_definitions(self):
        schema_files = list(
            (PLUGIN_ROOT / "examples" / "schemas").glob(
                "orchestration-result*.schema.json"
            )
        )
        self.assertEqual(schema_files, [
            PLUGIN_ROOT / "examples" / "schemas" / "orchestration-result.schema.json"
        ])
        self.assertEqual(self.SCHEMA["properties"]["schema_version"]["enum"], [3])
        for definition in oa.PROVIDER_TRANSPORT_DEFINITION_BY_ROLE.values():
            self.assertIn(definition, self.SCHEMA["$defs"])

    def test_runner_selects_transport_definition_only_from_role(self):
        expected = {
            "feasibility_verifier": {
                "verdict",
                "summary",
                "evidence",
                "stop_reason",
                "tests",
                "repository_state",
            },
            "implementer": {
                "verdict",
                "summary",
                "evidence",
                "stop_reason",
                "changed_files",
                "tests",
                "repository_state",
            },
            "adversarial_reviewer": set(oa.PROVIDER_RESULT_REQUIRED),
        }
        for role, fields in expected.items():
            schema = oa.extract_provider_result_schema(self.SCHEMA, role)
            self.assertEqual(set(schema["properties"]), fields, role)
            self.assertEqual(oa.preflight_strict_schema(schema), [], role)

    def test_unknown_role_fails_closed_and_cli_has_no_schema_selector(self):
        with self.assertRaises(oa.ConfigError):
            oa.extract_provider_result_schema(self.SCHEMA, "caller_selected_role")
        source = RUNNER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("--provider-schema", source)
        self.assertNotIn("--schema-definition", source)

    def test_feasibility_transport_exposes_no_review_collections(self):
        schema = oa.extract_provider_result_schema(
            self.SCHEMA, "feasibility_verifier"
        )
        for field in (*oa.REVIEWER_COLLECTIONS, "changed_files"):
            self.assertNotIn(field, schema["properties"])
        self.assertNotIn("finding", schema["$defs"])

    def test_implementer_transport_exposes_no_review_collections(self):
        schema = oa.extract_provider_result_schema(self.SCHEMA, "implementer")
        self.assertIn("changed_files", schema["properties"])
        for field in oa.REVIEWER_COLLECTIONS:
            self.assertNotIn(field, schema["properties"])
        self.assertNotIn("finding", schema["$defs"])

    def test_reviewer_transport_keeps_complete_review_surface(self):
        schema = oa.extract_provider_result_schema(
            self.SCHEMA, "adversarial_reviewer"
        )
        self.assertEqual(set(schema["properties"]), set(oa.PROVIDER_RESULT_REQUIRED))
        for field in oa.REVIEWER_COLLECTIONS:
            self.assertIn(field, schema["properties"])
        self.assertIn("finding", schema["$defs"])

    def test_luna_style_feasibility_result_succeeds_and_normalizes(self):
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier", **self.scout_kwargs()
        )
        self.assertEqual(rc, 0)
        self.assert_outcome(artifacts, "SUCCESS")
        raw = json.loads((artifacts / "provider-result.json").read_text())
        self.assertNotIn("changed_files", raw)
        for field in oa.REVIEWER_COLLECTIONS:
            self.assertNotIn(field, raw)
        canonical = json.loads((artifacts / "final-result.json").read_text())[
            "provider_result"
        ]
        self.assertEqual(canonical["changed_files"], [])
        for field in oa.REVIEWER_COLLECTIONS:
            self.assertEqual(canonical[field], [])

    def test_feasibility_findings_are_rejected_not_reclassified(self):
        final = make_result(
            "feasibility_verifier",
            "codex_cli",
            "codex_read_only",
            findings=[],
        )
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier", **self.scout_kwargs(final)
        )
        self.assertEqual(rc, 1)
        detail = self.assert_outcome(artifacts, "INVALID_OUTPUT")["detail"]
        self.assertIn("outside the selected role schema: findings", detail)
        self.assertFalse((artifacts / "final-result.json").exists())

    def test_feasibility_unknown_extra_field_is_rejected(self):
        final = make_result(
            "feasibility_verifier",
            "codex_cli",
            "codex_read_only",
            invented_review="do not ignore me",
        )
        rc, artifacts, _, _ = self.run_runner(
            "feasibility_verifier", **self.scout_kwargs(final)
        )
        self.assertEqual(rc, 1)
        detail = self.assert_outcome(artifacts, "INVALID_OUTPUT")["detail"]
        self.assertIn("invented_review", detail)

    def test_reviewer_collections_are_preserved_without_rewrite(self):
        finding = {
            "id": "F-C3",
            "severity": "Major",
            "violated_requirement": "review requirement",
            "location": "src/app.py:1",
            "repository_evidence": "src/app.py:1 evidence",
            "impact": "observable impact",
            "minimal_remediation_scope": "one function",
        }
        final = make_result(
            "adversarial_reviewer",
            "codex_cli",
            "codex_read_only",
            findings=[finding],
            observations=["observation"],
            suggestions=["suggestion"],
            evidence_gaps=["gap"],
        )
        rc, artifacts, _, _ = self.run_runner(
            "adversarial_reviewer", final=final
        )
        self.assertEqual(rc, 0)
        canonical = json.loads((artifacts / "final-result.json").read_text())[
            "provider_result"
        ]
        for field in oa.REVIEWER_COLLECTIONS:
            self.assertEqual(canonical[field], final[field])


class ClaudeInvocationContractTests(RunnerTestCase):
    """RC-2: stream-json with --print requires --verbose (real 2.1.191 contract)."""

    def test_claude_argv_includes_verbose_with_stream_json(self):
        rc, _, _, _ = self.run_runner(
            "adversarial_reviewer",
            host_mode="codex_hosted",
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
