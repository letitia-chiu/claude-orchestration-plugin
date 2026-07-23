"""Static, provider-free contract tests for the R3 Codex-host adapter.

These tests parse repository artifacts only. They do not spawn Codex agents,
invoke Claude CLI, access the network, or claim runtime smoke evidence.
"""

from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ROOT_BINDING = ROOT / "AGENTS.md"
AGENT_DIR = ROOT / ".codex" / "agents"
SKILL_DIR = ROOT / ".agents" / "skills" / "orchestration-codex-host"
SKILL_FILE = SKILL_DIR / "SKILL.md"
REFERENCES = ("kickoff.md", "go.md", "dispatch.md", "wrapup.md")
CODEX_DOC = ROOT / "docs" / "playbook" / "codex-host.md"
ROUTING_FILE = ROOT / "docs" / "playbook" / "agent-routing.json"
PACKET_FILE = ROOT / "examples" / "task-packets" / "codex-host-gate.md"
RUNNER_FILE = ROOT / "scripts" / "orchestration_agent.py"

TIERS = ("scout", "worker", "executor")
EXPECTED_MODELS = {
    "scout": "gpt-5.6-luna",
    "worker": "gpt-5.6-terra",
    "executor": "gpt-5.6-sol",
}
EXPECTED_REASONING = {"scout": "low", "worker": "medium", "executor": "high"}
EXPECTED_SANDBOX = {
    "scout": "read-only",
    "worker": "workspace-write",
    "executor": "workspace-write",
}
COMMON_PACKET_FIELDS = (
    "Governance authority",
    "Authorization issuer",
    "Acceptance owner",
    "Finding adjudicator",
    "Final ratifier",
    "Host mode",
    "Active execution host",
    "Host-local tier",
    "Host-local model",
    "Invocation path",
    "External reviewer provider/profile/model",
    "Role",
    "Provider/profile",
    "Explicit model",
    "Repository/worktree",
    "Authoritative plan branch",
    "Authoritative plan commit SHA",
    "Canonical base SHA",
    "Target SHA or batch base SHA",
    "Goal",
    "Allowed files",
    "Forbidden files",
    "Required evidence",
    "Stop conditions",
    "Git authorization",
    "External-side-effect authorization",
    "Report schema",
)


def read(path):
    return path.read_text(encoding="utf-8")


def load_agents():
    agents = {}
    for tier in TIERS:
        path = AGENT_DIR / ("%s.toml" % tier)
        with path.open("rb") as handle:
            agents[tier] = tomllib.load(handle)
    return agents


def routing():
    return json.loads(read(ROUTING_FILE))


class RootBindingTests(unittest.TestCase):
    def test_agents_md_exists_and_points_to_formal_skill(self):
        self.assertTrue(ROOT_BINDING.is_file())
        text = read(ROOT_BINDING)
        self.assertIn(".agents/skills/orchestration-codex-host/SKILL.md", text)

    def test_agents_md_stays_a_short_binding(self):
        self.assertLessEqual(len(read(ROOT_BINDING).splitlines()), 14)

    def test_agents_md_does_not_fix_a_governance_owner(self):
        text = read(ROOT_BINDING).lower()
        self.assertIn("never inferred", text)
        for pinned in (
            "governance authority = codex",
            "governance authority = claude",
            "governance authority = chatgpt",
        ):
            self.assertNotIn(pinned, text)

    def test_agents_md_forbids_reviewer_dispatch_and_automation(self):
        text = read(ROOT_BINDING).lower()
        self.assertIn("implementer must not dispatch a reviewer", text)
        for marker in ("automatically retry", "fall back", "chain roles"):
            self.assertIn(marker, text)


class NativeAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agents = load_agents()

    def test_all_three_agent_toml_files_parse(self):
        self.assertEqual(set(self.agents), set(TIERS))

    def test_agent_names_and_models_are_distinct(self):
        self.assertEqual(
            {data["name"] for data in self.agents.values()}, set(TIERS)
        )
        self.assertEqual(len({data["model"] for data in self.agents.values()}), 3)

    def test_models_are_luna_terra_sol_in_tier_order(self):
        self.assertEqual(
            [self.agents[tier]["model"] for tier in TIERS],
            [EXPECTED_MODELS[tier] for tier in TIERS],
        )

    def test_reasoning_effort_matches_contract(self):
        for tier, expected in EXPECTED_REASONING.items():
            self.assertEqual(
                self.agents[tier]["model_reasoning_effort"], expected, tier
            )

    def test_sandbox_modes_match_contract(self):
        for tier, expected in EXPECTED_SANDBOX.items():
            self.assertEqual(self.agents[tier]["sandbox_mode"], expected, tier)

    def test_scout_is_explicitly_read_only_and_non_implementing(self):
        data = self.agents["scout"]
        instructions = data["developer_instructions"].lower()
        self.assertEqual(data["sandbox_mode"], "read-only")
        self.assertIn("stay read-only", instructions)
        self.assertIn("do not implement", instructions)

    def test_worker_and_executor_are_workspace_write(self):
        for tier in ("worker", "executor"):
            self.assertEqual(
                self.agents[tier]["sandbox_mode"], "workspace-write", tier
            )

    def test_agent_responsibilities_are_distinct(self):
        descriptions = {data["description"] for data in self.agents.values()}
        instructions = {
            data["developer_instructions"] for data in self.agents.values()
        }
        self.assertEqual(len(descriptions), 3)
        self.assertEqual(len(instructions), 3)
        self.assertIn("one already specified", self.agents["worker"][
            "developer_instructions"
        ])
        self.assertIn("cross-module", self.agents["executor"][
            "developer_instructions"
        ])

    def test_every_agent_forbids_reviewer_and_git_expansion(self):
        for tier, data in self.agents.items():
            text = " ".join(data["developer_instructions"].lower().split())
            self.assertIn("do not start an external reviewer", text, tier)
            self.assertIn("do not commit", text, tier)
            self.assertIn("push", text, tier)
            self.assertIn("git authorization", text, tier)
            self.assertIn("do not claim governance", text, tier)

    def test_every_agent_forbids_retry_fallback_and_chaining(self):
        for tier, data in self.agents.items():
            text = " ".join(data["developer_instructions"].lower().split())
            for marker in ("never retry", "fall back", "switch models", "chain roles"):
                self.assertIn(marker, text, (tier, marker))


class SkillContractTests(unittest.TestCase):
    def test_skill_has_complete_entry_sequence(self):
        text = read(SKILL_FILE)
        for marker in ("kickoff", "go", "dispatch", "wrapup"):
            self.assertIn(marker, text)

    def test_all_references_exist_and_are_linked(self):
        skill_text = read(SKILL_FILE)
        for name in REFERENCES:
            path = SKILL_DIR / "references" / name
            self.assertTrue(path.is_file(), path)
            self.assertIn("references/%s" % name, skill_text)

    def test_kickoff_collects_plan_governance_host_and_authorization(self):
        text = read(SKILL_DIR / "references" / "kickoff.md")
        for marker in (
            "authoritative plan",
            "Governance authority",
            "Authorization issuer",
            "Acceptance owner",
            "Finding adjudicator",
            "Final ratifier",
            "codex_hosted",
            "codex_desktop",
            "27-field",
            "UNAUTHORIZED",
        ):
            self.assertIn(marker, text)

    def test_go_validates_exact_identity_scope_tests_and_separate_git_auth(self):
        text = read(SKILL_DIR / "references" / "go.md")
        for marker in (
            "status --short -uall",
            "branch --show-current",
            "rev-parse HEAD",
            "allowed and forbidden files",
            "acceptance commands",
            "stop conditions",
            "Execution authorization and Git authorization are independent",
            "Conversation memory",
        ):
            self.assertIn(marker, text)

    def test_dispatch_separates_active_host_from_external_review(self):
        text = read(SKILL_DIR / "references" / "dispatch.md")
        normalized = " ".join(text.split())
        self.assertIn("## `active_host`", text)
        self.assertIn("## `external_cli`", text)
        self.assertIn("active-host path never uses the external runner", normalized)
        self.assertIn("claude_cli", text)
        self.assertIn("claude_read_only", text)

    def test_reviewer_requires_independent_packet_and_dual_authorization(self):
        text = read(SKILL_DIR / "references" / "dispatch.md")
        self.assertIn("fresh, independent reviewer packet", text)
        self.assertGreaterEqual(text.count("ALLOW_PROVIDER_INVOCATION"), 2)
        self.assertIn("--external-authorization", text)

    def test_dispatch_forbids_automatic_fallback_retry_and_chaining(self):
        text = read(SKILL_DIR / "references" / "dispatch.md").lower()
        for marker in (
            "automatic fallback",
            "retry",
            "model switching",
            "role chaining",
        ):
            self.assertIn(marker, text)

    def test_wrapup_separates_evidence_and_defaults_next_steps_to_no(self):
        text = read(SKILL_DIR / "references" / "wrapup.md")
        self.assertIn("## Active-host evidence", text)
        self.assertIn("## External-review evidence", text)
        for marker in (
            "host thread UUID",
            "child thread/task UUID",
            "actual model evidence",
            "Git authorization",
            "Claude CLI session identity",
            "candidate findings",
            "adjudication status",
            "REAL SMOKE AUTHORIZED: NO",
            "PUSH / PR / MERGE AUTHORIZED: NO",
        ):
            self.assertIn(marker, text)


class RoutingAndRunnerTests(unittest.TestCase):
    def test_codex_adapter_is_implemented_with_native_tiers(self):
        mode = routing()["host_modes"]["codex_hosted"]
        self.assertEqual(mode["active_host"], "codex_desktop")
        self.assertEqual(mode["adapter_status"], "implemented")
        for tier in TIERS:
            self.assertEqual(mode["local_tiers"][tier]["provider"], "codex_native")
            self.assertEqual(mode["local_tiers"][tier]["profile"], tier)

    def test_claude_hosted_mapping_is_preserved(self):
        mode = routing()["host_modes"]["claude_hosted"]
        self.assertEqual(mode["active_host"], "claude_code")
        self.assertEqual(mode["adapter_status"], "implemented")
        for tier in TIERS:
            self.assertEqual(mode["local_tiers"][tier]["provider"], "claude_native")
            self.assertEqual(mode["local_tiers"][tier]["profile"], tier)
        self.assertEqual(
            mode["external_reviewer"],
            {"provider": "codex_cli", "profile": "codex_read_only"},
        )

    def test_codex_reviewer_is_fixed_to_claude_cli_read_only(self):
        reviewer = routing()["host_modes"]["codex_hosted"]["external_reviewer"]
        self.assertEqual(
            reviewer, {"provider": "claude_cli", "profile": "claude_read_only"}
        )

    def test_active_host_roles_are_never_external_runner_roles(self):
        data = routing()
        self.assertEqual(
            data["role_bindings"]["feasibility_verifier"],
            "active_host_local_tier",
        )
        self.assertEqual(
            data["role_bindings"]["implementer"], "active_host_local_tier"
        )
        runner_text = read(RUNNER_FILE)
        self.assertIn("host-native execution required", runner_text)
        self.assertIn("this external runner does not emulate the active host", runner_text)

    def test_external_reviewer_authorization_preflight_remains_dual(self):
        runner_text = read(RUNNER_FILE)
        self.assertIn("packet_auth != ALLOW_PROVIDER_INVOCATION", runner_text)
        self.assertIn("flag_auth != packet_auth", runner_text)
        self.assertIn("packet value and the caller flag", runner_text)

    def test_routing_forbids_automatic_behavior(self):
        constraints = routing()["constraints"]
        for key in (
            "host_may_auto_dispatch_reviewer",
            "implementer_may_dispatch_reviewer",
            "automatic_fallback",
            "automatic_retry",
            "automatic_role_chaining",
        ):
            self.assertIs(constraints[key], False, key)


class PacketAndDocumentationTests(unittest.TestCase):
    def test_packet_contains_exact_common_27_fields(self):
        text = read(PACKET_FILE)
        rows = {
            line.split("|")[1].strip()
            for line in text.splitlines()
            if line.startswith("|") and line.count("|") >= 3
        }
        self.assertEqual(set(COMMON_PACKET_FIELDS) - rows, set())
        self.assertEqual(len(COMMON_PACKET_FIELDS), 27)

    def test_packet_carries_codex_host_scope_and_authorizations(self):
        text = read(PACKET_FILE)
        for marker in (
            "`codex_hosted`",
            "`codex_desktop`",
            "Allowed files",
            "Forbidden files",
            "Git authorization",
            "External-side-effect authorization",
            "`NONE`",
            "ALLOW_PROVIDER_INVOCATION",
        ):
            self.assertIn(marker, text)

    def test_documentation_has_risk_matrix_and_handoff(self):
        text = read(CODEX_DOC)
        self.assertIn("## Risk-to-tier matrix", text)
        self.assertIn("## Claude reviewer handoff", text)
        for model in EXPECTED_MODELS.values():
            self.assertIn(model, text)

    def test_no_project_config_global_config_daemon_or_hook_is_installed(self):
        self.assertFalse((ROOT / ".codex" / "config.toml").exists())
        self.assertEqual(
            {p.relative_to(ROOT).as_posix() for p in (ROOT / ".codex").rglob("*") if p.is_file()},
            {
                ".codex/agents/scout.toml",
                ".codex/agents/worker.toml",
                ".codex/agents/executor.toml",
            },
        )
        text = read(CODEX_DOC)
        self.assertIn("does not install or modify global configuration", text)
        self.assertIn("a\ndaemon, or a hook", text)

    def test_path_codex_cli_is_explicitly_not_the_active_host(self):
        for path in (SKILL_FILE, SKILL_DIR / "references" / "dispatch.md", CODEX_DOC, PACKET_FILE):
            text = " ".join(read(path).split())
            self.assertIn("PATH", text, path)
            self.assertTrue(
                "not the active host" in text
                or "Never treat the PATH `codex` executable as the active host" in text,
                path,
            )

    def test_three_tier_real_smoke_is_explicitly_pending(self):
        for path in (SKILL_FILE, CODEX_DOC, PACKET_FILE):
            text = read(path).lower()
            self.assertIn("pending", text, path)
            self.assertNotIn("real smoke passed", text, path)
        doc = read(CODEX_DOC)
        for marker in (
            "real Luna, Terra, and Sol native agent spawning",
            "three distinct child thread UUIDs and actual model identities",
            "scout read-only sandbox precedence",
            "embedded Codex Desktop and standalone CLI runtime parity",
            "real fresh Claude CLI read-only reviewer result",
            "native per-file sandbox enforcement is not available",
        ):
            self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
