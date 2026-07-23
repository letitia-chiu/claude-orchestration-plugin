"""Provider-free release-candidate parity checks for dual-host version 0.7.0."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ROUTING_PATH = ROOT / "docs/playbook/agent-routing.json"
SCHEMA_PATH = ROOT / "examples/schemas/orchestration-result.schema.json"
READMES = (
    ROOT / "README.md",
    ROOT / "README.zh-TW.md",
    ROOT / "README.zh-CN.md",
    ROOT / "README.ja.md",
)
PUBLIC_DOCS = READMES + (
    ROOT / "docs/playbook/README.md",
    ROOT / "docs/playbook/orchestration.md",
    ROOT / "docs/playbook/task-routing.md",
    ROOT / "docs/playbook/codex-host.md",
    ROOT / "CHANGELOG.md",
)
CLAUDE_AGENTS = ROOT / "agents"
CODEX_AGENTS = ROOT / ".codex/agents"
PACKETS = ROOT / "examples/task-packets"
MATERIALIZER = ROOT / "scripts/init_codex_host.py"

COMMON_FIELDS = (
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

REQUIRED_README_LITERALS = (
    "Version: **0.7.0**",
    "`claude_hosted`",
    "`codex_hosted`",
    "`scout` / `worker` / `executor`",
    "Codex CLI",
    "`codex_read_only`",
    "Claude CLI",
    "`claude_read_only`",
    "/plugin marketplace add",
    "python3 scripts/init_codex_host.py",
    "--target /absolute/path/to/target-repository",
    "--check",
    "21",
    "no-overwrite",
    "`AGENTS.md`",
    "`headless_cli`",
    "`ALLOW_PROVIDER_INVOCATION`",
    "Real smoke",
    "Luna",
    "Terra",
    "Sol",
    "Xinghui Runtime adapter",
)

EXPECTED_INVENTORY = {
    "AGENTS.md",
    ".codex/agents/scout.toml",
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
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def routing() -> dict:
    return json.loads(read(ROUTING_PATH))


def parse_claude_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = read(path)
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError("missing frontmatter: %s" % path)
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields, text


def load_materializer():
    spec = importlib.util.spec_from_file_location("r4_materializer", MATERIALIZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RoutingParityTests(unittest.TestCase):
    def test_routing_schema_is_v2_and_governance_is_packet_bound(self):
        data = routing()
        self.assertEqual(data["schema_version"], 2)
        self.assertEqual(data["governance"]["binding"], "task_packet")
        self.assertTrue(data["governance"]["explicit_identity_required"])
        self.assertTrue(data["governance"]["provider_agnostic"])
        self.assertNotIn("authority", data)

    def test_both_host_adapters_are_implemented(self):
        for host in ("claude_hosted", "codex_hosted"):
            self.assertEqual(
                routing()["host_modes"][host]["adapter_status"], "implemented"
            )

    def test_both_hosts_have_the_same_three_tier_names(self):
        hosts = routing()["host_modes"]
        expected = {"scout", "worker", "executor"}
        self.assertEqual(set(hosts["claude_hosted"]["local_tiers"]), expected)
        self.assertEqual(set(hosts["codex_hosted"]["local_tiers"]), expected)

    def test_claude_tiers_are_native_and_codex_tiers_are_native(self):
        hosts = routing()["host_modes"]
        self.assertEqual(
            {tier["provider"] for tier in hosts["claude_hosted"]["local_tiers"].values()},
            {"claude_native"},
        )
        self.assertEqual(
            {tier["provider"] for tier in hosts["codex_hosted"]["local_tiers"].values()},
            {"codex_native"},
        )

    def test_reciprocal_reviewers_are_read_only(self):
        hosts = routing()["host_modes"]
        self.assertEqual(
            hosts["claude_hosted"]["external_reviewer"],
            {"provider": "codex_cli", "profile": "codex_read_only"},
        )
        self.assertEqual(
            hosts["codex_hosted"]["external_reviewer"],
            {"provider": "claude_cli", "profile": "claude_read_only"},
        )

    def test_a_host_is_never_reviewed_by_its_own_provider_family(self):
        hosts = routing()["host_modes"]
        self.assertNotEqual(
            hosts["claude_hosted"]["local_tiers"]["worker"]["provider"].split("_")[0],
            hosts["claude_hosted"]["external_reviewer"]["provider"].split("_")[0],
        )
        self.assertNotEqual(
            hosts["codex_hosted"]["local_tiers"]["worker"]["provider"].split("_")[0],
            hosts["codex_hosted"]["external_reviewer"]["provider"].split("_")[0],
        )

    def test_active_host_work_does_not_bind_to_external_runner(self):
        self.assertEqual(
            routing()["role_bindings"]["feasibility_verifier"],
            "active_host_local_tier",
        )
        self.assertEqual(
            routing()["role_bindings"]["implementer"], "active_host_local_tier"
        )
        self.assertEqual(
            routing()["role_bindings"]["adversarial_reviewer"], "external_reviewer"
        )

    def test_reviewer_requires_independent_authorization(self):
        for packet in (
            PACKETS / "claude-adversarial-review.md",
            PACKETS / "codex-adversarial-review.md",
        ):
            text = read(packet)
            self.assertTrue(
                "independent" in text.lower() or "獨立" in text,
                packet,
            )
            self.assertIn("ALLOW_PROVIDER_INVOCATION", text)

    def test_no_host_allows_automatic_review_fallback_retry_or_chaining(self):
        constraints = routing()["constraints"]
        for key in (
            "host_may_auto_dispatch_reviewer",
            "implementer_may_dispatch_reviewer",
            "automatic_fallback",
            "automatic_retry",
            "automatic_role_chaining",
        ):
            self.assertIs(constraints[key], False, key)

    def test_headless_implementation_is_disabled_by_default(self):
        headless = routing()["headless_cli_implementation"]
        self.assertIs(headless["enabled_by_default"], False)
        self.assertIs(headless["requires_separate_authorization"], True)


class SharedContractParityTests(unittest.TestCase):
    def test_host_packets_share_governance_and_packet_identity_fields(self):
        for packet in (
            PACKETS / "active-host-implementation.md",
            PACKETS / "codex-host-gate.md",
        ):
            text = read(packet)
            for field in COMMON_FIELDS:
                self.assertIn("| %s |" % field, text, (packet, field))

    def test_host_packets_share_allowed_forbidden_and_git_semantics(self):
        for packet in (
            PACKETS / "active-host-implementation.md",
            PACKETS / "codex-host-gate.md",
        ):
            text = read(packet)
            for marker in ("Allowed files", "Forbidden files", "Git authorization"):
                self.assertIn(marker, text, (packet, marker))
            self.assertIn("push", text)
            self.assertIn("merge", text)

    def test_one_result_envelope_supports_both_hosts(self):
        schema = json.loads(read(SCHEMA_PATH))
        self.assertEqual(
            schema["properties"]["host_mode"]["enum"],
            ["claude_hosted", "codex_hosted"],
        )
        for field in (
            "governance_identity",
            "host_mode",
            "execution_host",
            "host_tier",
            "invocation_path",
            "role",
            "provider",
            "profile",
            "model",
            "session_id",
        ):
            self.assertIn(field, schema["required"])

    def test_claude_agent_models_and_responsibilities_are_distinct(self):
        agents = [
            parse_claude_frontmatter(CLAUDE_AGENTS / ("%s.md" % tier))
            for tier in ("scout", "worker", "executor")
        ]
        self.assertEqual(len({fields["model"] for fields, _ in agents}), 3)
        self.assertEqual(len({fields["description"] for fields, _ in agents}), 3)

    def test_codex_agent_models_and_responsibilities_are_distinct(self):
        agents = []
        for tier in ("scout", "worker", "executor"):
            with (CODEX_AGENTS / ("%s.toml" % tier)).open("rb") as handle:
                agents.append(tomllib.load(handle))
        self.assertEqual(len({agent["model"] for agent in agents}), 3)
        self.assertEqual(len({agent["description"] for agent in agents}), 3)
        self.assertEqual(
            [agent["model"] for agent in agents],
            ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"],
        )

    def test_both_adapter_entries_are_repository_discoverable(self):
        for path in (
            ROOT / "commands/kickoff.md",
            CLAUDE_AGENTS / "scout.md",
            ROOT / "AGENTS.md",
            ROOT / ".agents/skills/orchestration-codex-host/SKILL.md",
        ):
            self.assertTrue(path.is_file(), path)

    def test_materializer_inventory_is_the_complete_21_file_contract(self):
        module = load_materializer()
        self.assertEqual(set(module.INVENTORY), EXPECTED_INVENTORY)
        self.assertEqual(len(module.INVENTORY), 21)

    def test_target_installed_shared_contracts_are_byte_identical(self):
        with tempfile.TemporaryDirectory(
            prefix="r4-parity-", dir="/private/tmp"
        ) as temp:
            target = Path(temp) / "target"
            subprocess.run(
                ["git", "init", "-q", str(target)],
                check=True,
                stdin=subprocess.DEVNULL,
                capture_output=True,
            )
            result = subprocess.run(
                [sys.executable, str(MATERIALIZER), "--target", str(target)],
                check=False,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for relative in (
                "docs/playbook/README.md",
                "docs/playbook/orchestration.md",
                "docs/playbook/task-routing.md",
                "docs/playbook/agent-routing.json",
                "examples/schemas/orchestration-result.schema.json",
            ):
                self.assertEqual(
                    (target / relative).read_bytes(),
                    (ROOT / relative).read_bytes(),
                    relative,
                )


class DocumentationParityTests(unittest.TestCase):
    def test_four_readmes_have_the_same_required_literals(self):
        for path in READMES:
            text = read(path)
            for literal in REQUIRED_README_LITERALS:
                self.assertIn(literal, text, (path.name, literal))

    def test_public_docs_do_not_fix_chatgpt_as_governance_owner(self):
        stale_claims = (
            "ChatGPT / user control window owns",
            "ChatGPT／使用者控制窗口持有",
            "ChatGPT／用户控制窗口持有",
            "ChatGPT／ユーザー制御ウィンドウが",
            "authority owners",
        )
        for path in PUBLIC_DOCS:
            text = read(path)
            for claim in stale_claims:
                self.assertNotIn(claim, text, (path, claim))

    def test_public_docs_do_not_make_prohibited_capability_claims(self):
        prohibited = (
            "production ready",
            "fully smoke tested",
            "seamless runtime hot swap",
            "arbitrary provider framework",
            "automatic provider fallback",
            "is a Xinghui Runtime adapter",
        )
        for path in PUBLIC_DOCS:
            lower = read(path).lower()
            for claim in prohibited:
                self.assertNotIn(claim.lower(), lower, (path, claim))

    def test_public_docs_mark_real_smoke_as_pending(self):
        for path in READMES:
            text = read(path)
            self.assertIn("Real smoke", text)
            self.assertRegex(text, r"Real smoke.{0,40}(pending|仍待|未実施)")

    def test_codex_install_and_conflict_rules_are_in_every_readme(self):
        for path in READMES:
            text = read(path)
            for marker in (
                "python3 scripts/init_codex_host.py",
                "--check",
                "21",
                "no-overwrite",
                "AGENTS.md",
                "conflict",
                "Plugin Directory",
            ):
                self.assertIn(marker, text, (path.name, marker))

    def test_playbook_declares_both_adapters_implemented(self):
        for path in (
            ROOT / "docs/playbook/README.md",
            ROOT / "docs/playbook/orchestration.md",
            ROOT / "docs/playbook/task-routing.md",
        ):
            text = read(path)
            self.assertNotIn("adapter 尚未實作", text)
            self.assertNotIn("adapter_status = not_implemented", text)

    def test_codex_host_doc_has_materializer_and_runtime_boundaries(self):
        text = read(ROOT / "docs/playbook/codex-host.md")
        for marker in (
            "scripts/init_codex_host.py",
            "--check",
            "21-file",
            "no-overwrite",
            "Pending real evidence",
            "Codex Plugin Directory package",
        ):
            self.assertIn(marker, text)


class ReleaseMetadataTests(unittest.TestCase):
    def test_plugin_version_is_0_7_0(self):
        plugin = json.loads(read(ROOT / ".claude-plugin/plugin.json"))
        self.assertEqual(plugin["version"], "0.7.0")

    def test_marketplace_descriptions_are_identical(self):
        marketplace = json.loads(read(ROOT / ".claude-plugin/marketplace.json"))
        self.assertEqual(
            marketplace["description"], marketplace["plugins"][0]["description"]
        )
        self.assertIn("dual-host", marketplace["description"])
        self.assertIn("Claude", marketplace["description"])
        self.assertIn("Codex", marketplace["description"])

    def test_metadata_keywords_include_dual_host_terms_without_misleading_terms(self):
        plugin = json.loads(read(ROOT / ".claude-plugin/plugin.json"))
        keywords = set(plugin["keywords"])
        self.assertTrue(
            {
                "dual-host",
                "codex-desktop",
                "claude-code",
                "adversarial-review",
                "agent-routing",
            }.issubset(keywords)
        )
        self.assertTrue(
            keywords.isdisjoint(
                {"autonomous", "hot-swap", "generic-provider", "runtime-adapter"}
            )
        )

    def test_changelog_top_release_is_0_7_0_on_release_candidate_date(self):
        headings = re.findall(r"^## \[(.+?)\] - (.+)$", read(ROOT / "CHANGELOG.md"), re.MULTILINE)
        self.assertGreater(len(headings), 0)
        self.assertEqual(headings[0], ("0.7.0", "2026-07-24"))

    def test_unreleased_0_6_0_is_not_listed_as_a_release(self):
        text = read(ROOT / "CHANGELOG.md")
        self.assertNotRegex(text, r"(?m)^## \[0\.6\.0\] - ")
        self.assertIn("supersedes the unreleased 0.6.0 candidate", text)

    def test_changelog_has_required_release_sections(self):
        release = read(ROOT / "CHANGELOG.md").split("## [0.5.0]", 1)[0]
        for heading in ("### Added", "### Changed", "### Security", "### Known limitations"):
            self.assertIn(heading, release)


if __name__ == "__main__":
    unittest.main()
