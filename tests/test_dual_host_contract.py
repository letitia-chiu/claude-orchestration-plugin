"""Dual-host recovery contract tests (R1+R2).

Static, provider-free checks that the shared contract and the Claude-hosted
adapter honor the four-way separation:

    governance authority != active execution host
                         != host-local execution tier
                         != external adversarial reviewer

No real provider is invoked and the repository is never modified.
"""

from __future__ import annotations

import json
import re
import unittest
from importlib import util as importlib_util
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = PLUGIN_ROOT / "scripts" / "orchestration_agent.py"
ROUTING_FILE = PLUGIN_ROOT / "docs" / "playbook" / "agent-routing.json"
AGENTS_DIR = PLUGIN_ROOT / "agents"
COMMANDS_DIR = PLUGIN_ROOT / "commands"
PACKETS_DIR = PLUGIN_ROOT / "examples" / "task-packets"

_spec = importlib_util.spec_from_file_location("orchestration_agent_dh", RUNNER_PATH)
oa = importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(oa)


def routing():
    return json.loads(ROUTING_FILE.read_text(encoding="utf-8"))


def parse_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "missing frontmatter in %s" % path
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields, text


# ---------------------------------------------------------------------------
# Governance neutrality
# ---------------------------------------------------------------------------


class GovernanceNeutralityTests(unittest.TestCase):
    def test_routing_has_no_fixed_governance_owner(self):
        data = routing()
        self.assertNotIn("authority", data)
        raw = ROUTING_FILE.read_text(encoding="utf-8").lower()
        self.assertNotIn("chatgpt", raw)
        self.assertEqual(data["governance"]["binding"], "task_packet")
        self.assertIs(data["governance"]["explicit_identity_required"], True)
        self.assertIs(data["governance"]["provider_agnostic"], True)

    def test_validate_routing_rejects_any_pinned_owner_shape(self):
        data = routing()
        data["authority"] = {
            "architecture_owner": "claude",
            "final_adjudicator": "codex",
        }
        errors = oa.validate_routing(data)
        self.assertTrue(any("must not be pinned" in e for e in errors), errors)

    def test_governance_identity_fields_are_the_packet_contract(self):
        self.assertEqual(
            set(oa.GOVERNANCE_IDENTITY_FIELDS),
            {
                "governance_authority",
                "authorization_issuer",
                "acceptance_owner",
                "finding_adjudicator",
                "final_ratifier",
            },
        )


# ---------------------------------------------------------------------------
# Host modes and role bindings
# ---------------------------------------------------------------------------


class HostModeContractTests(unittest.TestCase):
    def test_exactly_two_host_modes_defined(self):
        data = routing()
        self.assertEqual(set(data["host_modes"]), {"claude_hosted", "codex_hosted"})

    def test_claude_hosted_reviewer_is_codex_cli(self):
        reviewer = routing()["host_modes"]["claude_hosted"]["external_reviewer"]
        self.assertEqual(reviewer["provider"], "codex_cli")
        self.assertEqual(reviewer["profile"], "codex_read_only")

    def test_codex_hosted_reviewer_is_claude_cli(self):
        reviewer = routing()["host_modes"]["codex_hosted"]["external_reviewer"]
        self.assertEqual(reviewer["provider"], "claude_cli")
        self.assertEqual(reviewer["profile"], "claude_read_only")

    def test_codex_cli_is_not_a_claude_hosted_local_tier(self):
        tiers = routing()["host_modes"]["claude_hosted"]["local_tiers"]
        for tier_name, tier in tiers.items():
            self.assertNotIn(
                tier["provider"], ("codex_cli", "claude_cli"), tier_name
            )

    def test_role_bindings_route_implementation_to_active_host(self):
        data = routing()
        self.assertEqual(
            data["role_bindings"],
            {
                "feasibility_verifier": "active_host_local_tier",
                "implementer": "active_host_local_tier",
                "adversarial_reviewer": "external_reviewer",
            },
        )

    def test_both_host_adapters_are_declared_implemented(self):
        self.assertEqual(
            routing()["host_modes"]["codex_hosted"]["adapter_status"], "implemented"
        )
        self.assertEqual(
            routing()["host_modes"]["claude_hosted"]["adapter_status"], "implemented"
        )

    def test_headless_is_declared_non_default_opt_in(self):
        headless = routing()["headless_cli_implementation"]
        self.assertIs(headless["enabled_by_default"], False)
        self.assertIs(headless["requires_separate_authorization"], True)
        self.assertEqual(headless["provider"], "codex_cli")
        self.assertEqual(headless["profile"], "codex_workspace_write")

    def test_no_auto_dispatch_fallback_or_chaining(self):
        constraints = routing()["constraints"]
        self.assertIs(constraints["one_active_host"], True)
        self.assertIs(constraints["tier_must_be_explicit"], True)
        for key in (
            "host_may_auto_dispatch_reviewer",
            "implementer_may_dispatch_reviewer",
            "reviewer_may_modify_repository",
            "reviewer_may_dispatch_host",
            "automatic_fallback",
            "automatic_retry",
            "automatic_role_chaining",
        ):
            self.assertIs(constraints[key], False, key)


# ---------------------------------------------------------------------------
# Host-local tier and model mapping
# ---------------------------------------------------------------------------


class TierModelMappingTests(unittest.TestCase):
    def test_default_mapping_uses_agent_pins_via_null_override(self):
        for tier in ("scout", "worker", "executor"):
            self.assertIsNone(oa.resolve_tier_model(routing(), "claude_hosted", tier))

    def test_model_override_is_honored_and_validates(self):
        data = routing()
        data["host_modes"]["claude_hosted"]["local_tiers"]["scout"][
            "model_override"
        ] = "claude-haiku-4-5-20251001"
        self.assertEqual(oa.validate_routing(data), [])
        self.assertEqual(
            oa.resolve_tier_model(data, "claude_hosted", "scout"),
            "claude-haiku-4-5-20251001",
        )

    def test_non_string_override_fails_validation(self):
        data = routing()
        data["host_modes"]["claude_hosted"]["local_tiers"]["worker"]["model_override"] = 7
        errors = oa.validate_routing(data)
        self.assertTrue(any("model_override" in e for e in errors), errors)

    def test_unknown_tier_fails_closed(self):
        with self.assertRaises(oa.ConfigError):
            oa.resolve_tier_model(routing(), "claude_hosted", "hyperexecutor")

    def test_codex_scout_reasoning_effort_is_controller_pinned_low(self):
        self.assertEqual(
            oa.resolve_tier_reasoning_effort(
                routing(), "codex_hosted", "scout"
            ),
            "low",
        )

    def test_codex_native_worker_executor_routing_is_unchanged(self):
        tiers = routing()["host_modes"]["codex_hosted"]["local_tiers"]
        for tier in ("worker", "executor"):
            self.assertEqual(tiers[tier]["provider"], "codex_native")
            self.assertEqual(tiers[tier]["invocation_path"], "active_host")
            self.assertNotIn("reasoning_effort", tiers[tier])

    def test_missing_tier_definition_fails_validation(self):
        data = routing()
        del data["host_modes"]["claude_hosted"]["local_tiers"]["scout"]
        errors = oa.validate_routing(data)
        self.assertTrue(any("scout/worker/executor" in e for e in errors), errors)


# ---------------------------------------------------------------------------
# Claude-native tier agents (preserved, distinct, no extra authority)
# ---------------------------------------------------------------------------


class ClaudeTierAgentTests(unittest.TestCase):
    def setUp(self):
        self.agents = {}
        for name in ("scout", "worker", "executor"):
            path = AGENTS_DIR / ("%s.md" % name)
            self.assertTrue(path.is_file(), path)
            self.agents[name] = parse_frontmatter(path)

    def test_three_tiers_exist_with_matching_names(self):
        for name, (fields, _) in self.agents.items():
            self.assertEqual(fields["name"], name)

    def test_tiers_pin_distinct_models(self):
        models = {fields["model"] for fields, _ in self.agents.values()}
        self.assertEqual(len(models), 3, models)

    def test_scout_is_read_only(self):
        fields, _ = self.agents["scout"]
        self.assertEqual(
            {tool.strip() for tool in fields["tools"].split(",")},
            {"Read", "Glob", "Grep"},
        )

    def test_tiers_have_distinct_responsibilities(self):
        descriptions = {fields["description"] for fields, _ in self.agents.values()}
        self.assertEqual(len(descriptions), 3)
        self.assertIn("Read-only reconnaissance", self.agents["scout"][0]["description"])
        self.assertIn("Default execution tier", self.agents["worker"][0]["description"])
        self.assertIn("Hard-execution tier", self.agents["executor"][0]["description"])

    def test_no_agent_claims_git_or_governance_authority(self):
        for name, (_, text) in self.agents.items():
            lowered = text.lower()
            for token in ("git push", "merge authority", "final ratifier", "adjudicat"):
                self.assertNotIn(token, lowered, (name, token))


# ---------------------------------------------------------------------------
# Command surface contract markers
# ---------------------------------------------------------------------------


class CommandContractTests(unittest.TestCase):
    def read(self, name):
        return (COMMANDS_DIR / name).read_text(encoding="utf-8")

    def test_dispatch_routes_implementation_to_active_host(self):
        text = self.read("dispatch.md")
        self.assertIn("native worker/executor", text)
        self.assertIn("host_local_cli", text)
        self.assertIn("gpt-5.6-luna", text)
        self.assertIn("--invocation-path", text)
        self.assertIn("--governance-authority", text)

    def test_dispatch_requires_independent_reviewer_authorization(self):
        text = self.read("dispatch.md")
        self.assertIn("Implementer may not dispatch the reviewer.", text)
        self.assertIn("independent", text)
        self.assertIn("headless", text)

    def test_kickoff_carries_governance_and_host_identity(self):
        text = self.read("kickoff.md")
        for marker in (
            "Governance authority",
            "Authorization issuer",
            "Finding adjudicator",
            "Final ratifier",
            "Host mode (claude_hosted | codex_hosted",
            "Invocation path per role",
        ):
            self.assertIn(marker, text, marker)
        self.assertIn("never pins them to ChatGPT, Claude, Codex, or any product", text)

    def test_go_requires_explicit_host_mode_and_tier_authorization(self):
        text = self.read("go.md")
        self.assertIn("Codex-hosted feasibility", text)
        self.assertIn("ALLOW_HOST_LOCAL_CLI_INVOCATION", text)
        self.assertIn("target repository HEAD", text)
        self.assertIn("independent reviewer authorization", text)

    def test_wrapup_separates_active_host_and_external_review_evidence(self):
        text = self.read("wrapup.md")
        self.assertIn(
            "Keep active-host evidence and external-review evidence separate", text
        )
        self.assertIn(
            "invocation path = active_host / external manifest = not applicable", text
        )
        self.assertIn("packet-named finding adjudicator", text)

    def test_no_command_fixes_governance_to_a_product(self):
        for name in ("kickoff.md", "go.md", "dispatch.md", "wrapup.md"):
            text = self.read(name).lower()
            self.assertNotIn("chatgpt/user control window", text, name)
            self.assertNotIn("authorization owner (chatgpt)", text, name)

    def test_init_playbook_keeps_no_overwrite_protection(self):
        text = self.read("init-playbook.md")
        self.assertIn("**Exists = skip, don't overwrite**", text)
        self.assertIn(
            "The same no-overwrite rule applies to `docs/playbook/agent-routing.json`",
            text,
        )
        # The embedded routing template must be the v2 contract.
        self.assertIn('"schema_version": 2', text)
        self.assertNotIn('"schema_version": 1', text)


# ---------------------------------------------------------------------------
# Task packet templates
# ---------------------------------------------------------------------------


class TaskPacketTemplateTests(unittest.TestCase):
    EXPECTED = {
        "active-host-feasibility.md",
        "active-host-implementation.md",
        "codex-host-gate.md",
        "codex-adversarial-review.md",
        "claude-adversarial-review.md",
        "headless-codex-implementation.md",
    }

    IDENTITY_FIELDS = (
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
    )

    def test_expected_packet_set_exists(self):
        actual = {p.name for p in PACKETS_DIR.glob("*.md")}
        self.assertEqual(actual, self.EXPECTED)

    def test_every_packet_carries_the_identity_fields(self):
        for name in self.EXPECTED:
            text = (PACKETS_DIR / name).read_text(encoding="utf-8")
            for field in self.IDENTITY_FIELDS:
                self.assertIn(field, text, (name, field))

    def test_headless_packet_is_marked_non_default(self):
        text = (PACKETS_DIR / "headless-codex-implementation.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("headless_cli", text)
        self.assertIn("非預設", text)

    def test_reviewer_packets_are_reciprocal(self):
        codex_review = (PACKETS_DIR / "codex-adversarial-review.md").read_text(
            encoding="utf-8"
        )
        claude_review = (PACKETS_DIR / "claude-adversarial-review.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("claude_hosted", codex_review)
        self.assertIn("codex_cli / codex_read_only", codex_review)
        self.assertIn("codex_hosted", claude_review)
        self.assertIn("claude_cli / claude_read_only", claude_review)


if __name__ == "__main__":
    unittest.main()
