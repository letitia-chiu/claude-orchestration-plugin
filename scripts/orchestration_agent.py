#!/usr/bin/env python3
"""Bounded external-agent process runner for the orchestration plugin.

This runner is a narrow process-safety wrapper. Per invocation it:

- validates the project routing file (docs/playbook/agent-routing.json, schema v2:
  governance-neutral, host-aware, tier-aware — governance identity comes from
  the task packet, never from the routing file);
- requires an explicit governance identity, host mode, and invocation path
  (fail closed on any missing identity field);
- resolves the role through the dual-host contract: Codex-hosted scout is a
  Desktop-dispatched host-local read-only Codex CLI tier; worker/executor remain
  native active-host tiers; adversarial_reviewer resolves to the opposing
  provider's read-only CLI; headless_cli implementation is a non-default,
  separately authorized opt-in;
- mechanically enforces the task packet's External-side-effect authorization
  before any provider spawn: the packet must carry exactly one unambiguous
  ALLOW_PROVIDER_INVOCATION value AND the caller must pass the matching
  --external-authorization flag; missing, unknown, ambiguous, or mismatched
  authorization fails closed with no child process started;
- starts exactly one external CLI process (codex_cli or claude_cli);
- for the Codex-hosted scout, preserves the complete controller packet as
  evidence but sends the provider only a marker-delimited substantive task;
- enforces a wall-clock timeout against the whole child process group;
- captures stdout and stderr separately, unmerged;
- records pre/post Git evidence with read-only Git commands only;
- detects repository mutation for read-only roles;
- validates implementation changed paths against allow/forbid lists;
- selects and sends only the role-specific provider_result definition from the
  canonical schema, validates the substantive result, applies lossless
  canonical empty-field normalization, and combines it with controller-owned
  immutable provenance in the schema-v3 final artifact;
- writes an artifact bundle plus a SHA-256 manifest;
- returns a machine-readable classified outcome.

It is NOT an orchestrator, planner, authorization engine, provider SDK,
Git controller, or Runtime adapter. It never chains roles, never retries
semantic failures, never falls back to another provider, never resumes a
session automatically, and never performs any Git write operation
(no staging, commit, push, PR, merge, reset, clean, checkout, or revert).
Standard library only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RESULT_SCHEMA_FILE = PLUGIN_ROOT / "examples" / "schemas" / "orchestration-result.schema.json"

# Outcome classes (see authoritative plan §8.4).
SUCCESS = "SUCCESS"
STOPPED = "STOPPED"
MODEL_REPORTED_BLOCKER = "MODEL_REPORTED_BLOCKER"
PROCESS_NONZERO = "PROCESS_NONZERO"
TIMEOUT = "TIMEOUT"
INTERRUPTED = "INTERRUPTED"
INVALID_OUTPUT = "INVALID_OUTPUT"
READ_ONLY_MUTATION = "READ_ONLY_MUTATION"
FORBIDDEN_PATH_CHANGED = "FORBIDDEN_PATH_CHANGED"
TEST_FAILURE = "TEST_FAILURE"  # reserved: controller-supplied evidence only; the runner never emits it itself
TRANSCRIPT_INCOMPLETE = "TRANSCRIPT_INCOMPLETE"
CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"

SUPPORTED_ROLES = ("feasibility_verifier", "implementer", "adversarial_reviewer")
READ_ONLY_ROLES = frozenset({"feasibility_verifier", "adversarial_reviewer"})
EXTERNAL_PROVIDERS = frozenset({"codex_cli", "claude_cli"})

HOST_MODES = ("claude_hosted", "codex_hosted")
INVOCATION_PATHS = ("active_host", "host_local_cli", "external_cli", "headless_cli")
HOST_TIERS = ("scout", "worker", "executor")
REASONING_EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")
GOVERNANCE_IDENTITY_FIELDS = (
    "governance_authority",
    "authorization_issuer",
    "acceptance_owner",
    "finding_adjudicator",
    "final_ratifier",
)
# Native provider family per host mode: the external reviewer must come from
# the opposing family (a host never reviews itself with its own provider).
HOST_NATIVE_CLI = {"claude_hosted": "claude_cli", "codex_hosted": "codex_cli"}
ROLE_BINDINGS_REQUIRED = {
    "feasibility_verifier": "active_host_local_tier",
    "implementer": "active_host_local_tier",
    "adversarial_reviewer": "external_reviewer",
}
CONSTRAINTS_REQUIRED = {
    "one_active_host": True,
    "tier_must_be_explicit": True,
    "host_may_auto_dispatch_reviewer": False,
    "implementer_may_dispatch_reviewer": False,
    "reviewer_may_modify_repository": False,
    "reviewer_may_dispatch_host": False,
    "external_git_writes_require_separate_authorization": True,
    "automatic_fallback": False,
    "automatic_retry": False,
    "automatic_role_chaining": False,
}

# External-side-effect authorization: the task packet field the runner parses
# mechanically before any provider spawn. Prompt wording is not a guarantee;
# the packet value and the caller flag must both equal this token.
EXTERNAL_AUTH_FIELD = "External-side-effect authorization"
ALLOW_PROVIDER_INVOCATION = "ALLOW_PROVIDER_INVOCATION"
HOST_LOCAL_AUTH_FIELD = "Host-local execution authorization"
ALLOW_HOST_LOCAL_CLI_INVOCATION = "ALLOW_HOST_LOCAL_CLI_INVOCATION"
PROVIDER_TASK_START = "<!-- BEGIN PROVIDER SUBSTANTIVE TASK -->"
PROVIDER_TASK_END = "<!-- END PROVIDER SUBSTANTIVE TASK -->"
PROVIDER_TASK_PROTECTED_LABELS = (
    "Governance authority",
    "Authorization issuer",
    "Acceptance owner",
    "Finding adjudicator",
    "Final ratifier",
    "Authoritative plan",
    "candidate SHA",
    "Target repository HEAD",
    "Target repository status",
    "Host mode",
    "Active execution host",
    "Host-local tier",
    "Host-local model",
    "Host-local reasoning effort",
    "Invocation path",
    "Provider/profile",
    "Explicit model",
    "Repository/worktree",
    "Canonical base SHA",
    "Git authorization",
    "Host-local execution authorization",
    "External-side-effect authorization",
)
FEASIBILITY_PROVIDER_PREAMBLE = """\
# Runner-dispatched feasibility provider task

Provider execution phase: `substantive_only`.

The controller has already validated immutable provenance, repository identity,
routing, authorization, model, reasoning effort, and the pre-run Git snapshot.
Do not repeat, confirm, infer, or adjudicate those controller checks. In
particular, do not use `git cat-file`, `git show-ref`, or another command to test
whether plan, candidate, governance, or authorization identities exist in the
target repository.

Execute only the substantive task below. Return only the fields required by the
selected `feasibility_verifier` provider schema. The only permitted verdicts are
`PASS_FOR_IMPLEMENTATION_AUTHORIZATION`, `PLAN_CHANGE_REQUIRED`, and
`EVIDENCE_INSUFFICIENT`.

"""

# External CLI profile -> (provider kind, write-capable)
PROFILES = {
    "codex_read_only": ("codex_cli", False),
    "codex_workspace_write": ("codex_cli", True),
    "claude_read_only": ("claude_cli", False),
}

# The only Git subcommands this runner may ever execute (evidence collection).
GIT_READ_ONLY_SUBCOMMANDS = frozenset({"rev-parse", "status", "diff", "ls-files", "version"})

PROVIDER_RESULT_REQUIRED = (
    "verdict",
    "summary",
    "evidence",
    "stop_reason",
    "changed_files",
    "tests",
    "repository_state",
    "findings",
    "observations",
    "suggestions",
    "evidence_gaps",
)
REVIEWER_COLLECTIONS = ("findings", "observations", "suggestions", "evidence_gaps")
CONTROLLER_OWNED_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "provenance",
        "governance_identity",
        "authoritative_plan_sha",
        "candidate_sha",
        "target_repository_head",
        "host_mode",
        "execution_host",
        "host_tier",
        "role",
        "provider",
        "profile",
        "requested_model",
        "resolved_model",
        "reported_model",
        "requested_reasoning_effort",
        "resolved_reasoning_effort",
        "reported_reasoning_effort",
        "reasoning_effort",
        "model_reasoning_effort",
        "model",
        "invocation_path",
        "session_id",
    }
)
PROVIDER_TRANSPORT_DEFINITION_BY_ROLE = {
    "feasibility_verifier": "provider_result_feasibility_verifier",
    "implementer": "provider_result_implementer",
    "adversarial_reviewer": "provider_result_adversarial_reviewer",
}
PROVIDER_TRANSPORT_DEPENDENCIES_BY_ROLE = {
    "feasibility_verifier": ("test_entry", "repository_state", "git_state"),
    "implementer": ("test_entry", "repository_state", "git_state"),
    "adversarial_reviewer": (
        "test_entry",
        "repository_state",
        "git_state",
        "finding",
    ),
}

# Keywords the strict structured-output transport does not reliably support.
# The canonical schema must stay inside the strict subset; the local preflight
# fails closed before any provider is spawned.
STRICT_FORBIDDEN_KEYWORDS = frozenset(
    {
        "if",
        "then",
        "else",
        "allOf",
        "dependentSchemas",
        "unevaluatedProperties",
        "patternProperties",
    }
)
FINDING_REQUIRED = (
    "id",
    "severity",
    "violated_requirement",
    "location",
    "repository_evidence",
    "impact",
    "minimal_remediation_scope",
)
SEVERITIES = frozenset({"Blocker", "Major", "Minor"})
FEASIBILITY_VERDICTS = frozenset(
    {
        "PASS_FOR_IMPLEMENTATION_AUTHORIZATION",
        "PLAN_CHANGE_REQUIRED",
        "EVIDENCE_INSUFFICIENT",
    }
)

EXIT_BY_OUTCOME = {SUCCESS: 0, CONFIGURATION_ERROR: 2, CAPABILITY_UNAVAILABLE: 2}

MAX_RECORDED_ARG_LEN = 2000  # longer argv elements (inline schema text) are replaced by a digest marker


class ConfigError(Exception):
    """Raised for any fail-closed configuration problem before process start."""


# ---------------------------------------------------------------------------
# Git evidence (read-only)
# ---------------------------------------------------------------------------


def _run_git(workdir, args):
    """Run a read-only git command. The allowlist is the only subprocess path to git."""
    if not args or args[0] not in GIT_READ_ONLY_SUBCOMMANDS:
        raise ValueError("refused non-read-only git subcommand: %r" % (args,))
    return subprocess.run(
        ["git", "-C", str(workdir), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )


def _git_text(workdir, args):
    proc = _run_git(workdir, args)
    if proc.returncode != 0:
        raise ConfigError(
            "git %s failed in %s: %s" % (args[0], workdir, proc.stderr.decode(errors="replace").strip())
        )
    return proc.stdout


def _parse_porcelain_z(raw):
    """Parse `git status --porcelain=v1 -z` output into a list of entries."""
    fields = raw.split(b"\0")
    entries = []
    i = 0
    while i < len(fields):
        field = fields[i].decode(errors="replace")
        if not field:
            i += 1
            continue
        entry = {"status": field[:2], "path": field[3:]}
        if entry["status"][0] in "RC":
            i += 1
            entry["orig_path"] = fields[i].decode(errors="replace")
        entries.append(entry)
        i += 1
    return entries


def _snapshot_git(workdir):
    head = _git_text(workdir, ["rev-parse", "HEAD"]).decode().strip()
    status_raw = _git_text(
        workdir, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]
    )
    entries = _parse_porcelain_z(status_raw)
    status_short = _git_text(
        workdir, ["status", "--short", "--untracked-files=all"]
    ).decode(errors="replace")
    tracked_diff = _git_text(workdir, ["diff", "--binary"])
    cached_diff = _git_text(workdir, ["diff", "--cached", "--binary"])
    return {
        "head": head,
        "status_short": status_short,
        "status_entries": entries,
        "tracked_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
        "cached_diff_sha256": hashlib.sha256(cached_diff).hexdigest(),
    }


def _snapshot_differences(pre, post):
    diffs = []
    if pre["head"] != post["head"]:
        diffs.append("HEAD changed: %s -> %s" % (pre["head"], post["head"]))
    pre_entries = sorted((e["status"], e["path"]) for e in pre["status_entries"])
    post_entries = sorted((e["status"], e["path"]) for e in post["status_entries"])
    if pre_entries != post_entries:
        diffs.append(
            "status entries changed: pre=%s post=%s" % (pre_entries, post_entries)
        )
    if pre["tracked_diff_sha256"] != post["tracked_diff_sha256"]:
        diffs.append("tracked working-tree diff changed")
    if pre["cached_diff_sha256"] != post["cached_diff_sha256"]:
        diffs.append("index (cached) diff changed")
    return diffs


# ---------------------------------------------------------------------------
# Routing validation (fail closed)
# ---------------------------------------------------------------------------


def preflight_strict_schema(schema):
    """Fail-closed local validation that the schema stays in the strict subset.

    Checks, before any provider is spawned: root is an object schema; every
    object node declares additionalProperties: false and requires every one
    of its properties; no forbidden conditional/unsupported keywords appear
    anywhere; every $ref resolves inside this document. Returns a list of
    errors (empty when the schema is strict-compatible).
    """
    errors = []
    if not isinstance(schema, dict):
        return ["schema root must be a JSON object"]
    if schema.get("type") != "object":
        errors.append("schema root type must be 'object'")

    def resolve_ref(ref, location):
        if not isinstance(ref, str) or not ref.startswith("#/"):
            errors.append("%s: unresolvable $ref %r" % (location, ref))
            return
        node = schema
        for part in ref[2:].split("/"):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                errors.append("%s: unresolvable $ref %r" % (location, ref))
                return

    def walk(node, location):
        if isinstance(node, dict):
            forbidden = STRICT_FORBIDDEN_KEYWORDS.intersection(node)
            if forbidden:
                errors.append(
                    "%s: forbidden strict-subset keywords %s" % (location, sorted(forbidden))
                )
            if "$ref" in node:
                resolve_ref(node["$ref"], location)
            if node.get("type") == "object" or "properties" in node:
                properties = node.get("properties")
                if not isinstance(properties, dict):
                    errors.append("%s: object schema without a properties map" % location)
                else:
                    if node.get("additionalProperties") is not False:
                        errors.append(
                            "%s: additionalProperties must be explicitly false" % location
                        )
                    if set(node.get("required", [])) != set(properties):
                        errors.append(
                            "%s: required must list every property name" % location
                        )
            for key, value in node.items():
                walk(value, "%s.%s" % (location, key))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, "%s[%d]" % (location, index))

    walk(schema, "$")
    return errors


def load_routing(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError("routing file unreadable: %s" % exc) from exc
    try:
        routing = json.loads(raw)
    except ValueError as exc:
        raise ConfigError("routing file is not valid JSON: %s" % exc) from exc
    if not isinstance(routing, dict):
        raise ConfigError("routing file must contain a JSON object")
    return routing


def validate_routing(routing):
    """Return a list of configuration errors (empty when routing is valid).

    Schema v2 is governance-neutral: the routing file must never pin a
    governance owner to a product; identity always comes from the task packet.
    """
    errors = []
    if routing.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    if "authority" in routing:
        errors.append(
            "governance authority must not be pinned in the routing file "
            "(schema v1 'authority' block found); governance identity comes "
            "from each task packet"
        )
    governance = routing.get("governance")
    if not isinstance(governance, dict):
        errors.append("governance must be an object")
    else:
        if governance.get("binding") != "task_packet":
            errors.append("governance.binding must be 'task_packet'")
        if governance.get("explicit_identity_required") is not True:
            errors.append("governance.explicit_identity_required must be true")
        if governance.get("provider_agnostic") is not True:
            errors.append("governance.provider_agnostic must be true")

    host_modes = routing.get("host_modes")
    if not isinstance(host_modes, dict):
        errors.append("host_modes must be an object")
        host_modes = {}
    if set(host_modes) != set(HOST_MODES):
        errors.append(
            "host_modes must define exactly %s; got %s"
            % (sorted(HOST_MODES), sorted(host_modes))
        )
    for mode_name, mode in host_modes.items():
        if mode_name not in HOST_MODES:
            continue
        if not isinstance(mode, dict):
            errors.append("host mode %s must be an object" % mode_name)
            continue
        active_host = mode.get("active_host")
        if not isinstance(active_host, str) or not active_host:
            errors.append("host mode %s: active_host must be a non-empty string" % mode_name)
        if mode.get("adapter_status") not in ("implemented", "not_implemented"):
            errors.append(
                "host mode %s: adapter_status must be implemented/not_implemented" % mode_name
            )
        tiers = mode.get("local_tiers")
        if not isinstance(tiers, dict) or set(tiers) != set(HOST_TIERS):
            errors.append(
                "host mode %s: local_tiers must define exactly scout/worker/executor" % mode_name
            )
            tiers = {}
        for tier_name, tier in tiers.items():
            if not isinstance(tier, dict):
                errors.append("host mode %s tier %s must be an object" % (mode_name, tier_name))
                continue
            tier_provider = tier.get("provider")
            if not isinstance(tier_provider, str) or not tier_provider:
                errors.append(
                    "host mode %s tier %s: provider must be a non-empty string"
                    % (mode_name, tier_name)
                )
            elif tier_provider in EXTERNAL_PROVIDERS and not (
                mode_name == "codex_hosted"
                and tier_name == "scout"
                and tier_provider == "codex_cli"
            ):
                errors.append(
                    "host mode %s tier %s: only the corrective Codex-hosted scout "
                    "may use a host-local CLI provider; got %s"
                    % (mode_name, tier_name, tier_provider)
                )
            if not isinstance(tier.get("profile"), str) or not tier.get("profile"):
                errors.append(
                    "host mode %s tier %s: profile must be a non-empty string"
                    % (mode_name, tier_name)
                )
            override = tier.get("model_override", None)
            if override is not None and (not isinstance(override, str) or not override):
                errors.append(
                    "host mode %s tier %s: model_override must be a non-empty string or null"
                    % (mode_name, tier_name)
                )
            effort = tier.get("reasoning_effort", None)
            if effort is not None and effort not in REASONING_EFFORTS:
                errors.append(
                    "host mode %s tier %s: reasoning_effort must be one of %s or omitted"
                    % (mode_name, tier_name, sorted(REASONING_EFFORTS))
                )
        if mode_name == "codex_hosted" and tiers:
            scout = tiers.get("scout", {})
            expected_scout = {
                "provider": "codex_cli",
                "profile": "codex_read_only",
                "invocation_path": "host_local_cli",
                "model_override": "gpt-5.6-luna",
                "reasoning_effort": "low",
            }
            if scout != expected_scout:
                errors.append(
                    "host mode codex_hosted tier scout must be exactly %r"
                    % expected_scout
                )
            for tier_name in ("worker", "executor"):
                tier = tiers.get(tier_name, {})
                if tier.get("provider") != "codex_native":
                    errors.append(
                        "host mode codex_hosted tier %s must remain codex_native"
                        % tier_name
                    )
                if tier.get("invocation_path") != "active_host":
                    errors.append(
                        "host mode codex_hosted tier %s invocation_path must be active_host"
                        % tier_name
                    )
        reviewer = mode.get("external_reviewer")
        if not isinstance(reviewer, dict):
            errors.append("host mode %s: external_reviewer must be an object" % mode_name)
            continue
        rev_provider = reviewer.get("provider")
        rev_profile = reviewer.get("profile")
        if rev_provider not in EXTERNAL_PROVIDERS:
            errors.append(
                "host mode %s: unknown external reviewer provider %r" % (mode_name, rev_provider)
            )
            continue
        if rev_provider == HOST_NATIVE_CLI.get(mode_name):
            errors.append(
                "host mode %s: external reviewer must come from the opposing provider "
                "family, not %s (a host never reviews itself)" % (mode_name, rev_provider)
            )
        if rev_profile not in PROFILES:
            errors.append(
                "host mode %s: unknown external reviewer profile %r" % (mode_name, rev_profile)
            )
            continue
        profile_provider, write_capable = PROFILES[rev_profile]
        if profile_provider != rev_provider:
            errors.append(
                "host mode %s: reviewer profile %s belongs to provider %s, not %s"
                % (mode_name, rev_profile, profile_provider, rev_provider)
            )
        if write_capable:
            errors.append(
                "host mode %s: external reviewer is read-only but profile %s is "
                "write-capable" % (mode_name, rev_profile)
            )

    if routing.get("role_bindings") != ROLE_BINDINGS_REQUIRED:
        errors.append(
            "role_bindings must be exactly %r (feasibility/implementation belong to "
            "the active host; only adversarial_reviewer goes external)"
            % (ROLE_BINDINGS_REQUIRED,)
        )

    headless = routing.get("headless_cli_implementation")
    if not isinstance(headless, dict):
        errors.append("headless_cli_implementation must be an object")
    else:
        if headless.get("enabled_by_default") is not False:
            errors.append(
                "headless_cli_implementation.enabled_by_default must be false "
                "(headless implementation is never the default)"
            )
        if headless.get("requires_separate_authorization") is not True:
            errors.append(
                "headless_cli_implementation.requires_separate_authorization must be true"
            )
        h_provider = headless.get("provider")
        h_profile = headless.get("profile")
        if h_provider not in EXTERNAL_PROVIDERS:
            errors.append("headless_cli_implementation: unknown provider %r" % (h_provider,))
        elif h_profile not in PROFILES or PROFILES[h_profile][0] != h_provider:
            errors.append(
                "headless_cli_implementation: profile %r does not belong to provider %r"
                % (h_profile, h_provider)
            )

    constraints = routing.get("constraints")
    if not isinstance(constraints, dict):
        errors.append("constraints must be an object")
        constraints = {}
    for key, expected in CONSTRAINTS_REQUIRED.items():
        if constraints.get(key) is not expected:
            errors.append("constraints.%s must be %s" % (key, json.dumps(expected)))
    return errors


def _parse_packet_authorization(packet_text, field_name):
    """Mechanically extract one exact authorization field value.

    Scans every packet line containing the field name and takes the first
    value token after it (table cell or colon form). Returns (value, errors):
    value is the single unambiguous token, or None. Zero occurrences is a
    missing field; conflicting tokens are ambiguous; both fail closed at the
    caller. This parser never guesses: prompt prose is not authorization.
    """
    tokens = []
    for line in packet_text.splitlines():
        if field_name not in line:
            continue
        remainder = line.split(field_name, 1)[1]
        remainder = remainder.strip().lstrip(":").lstrip("|").strip()
        if remainder.endswith("|"):
            remainder = remainder[:-1].strip()
        if not remainder:
            # A bare field name with no value on the same line is a malformed
            # authorization: record it as an explicit empty token (ambiguous
            # with any real value, missing when alone).
            tokens.append("")
            continue
        tokens.append(re.split(r"[\s（(]", remainder, maxsplit=1)[0])
    unique = sorted(set(tokens))
    if not unique:
        return None, ["task packet does not carry the %r field" % field_name]
    if len(unique) > 1:
        return None, [
            "task packet %r is ambiguous: conflicting values %s"
            % (field_name, unique)
        ]
    if unique[0] == "":
        return None, ["task packet %r carries no value" % field_name]
    return unique[0], []


def parse_packet_external_authorization(packet_text):
    return _parse_packet_authorization(packet_text, EXTERNAL_AUTH_FIELD)


def parse_packet_host_local_authorization(packet_text):
    return _parse_packet_authorization(packet_text, HOST_LOCAL_AUTH_FIELD)


def _parse_packet_identity(packet_text, field_names):
    """Return one unambiguous same-line packet identity value."""
    values = []
    for line in packet_text.splitlines():
        for field_name in field_names:
            if field_name not in line:
                continue
            remainder = line.split(field_name, 1)[1]
            remainder = remainder.strip().lstrip(":").lstrip("|").strip()
            if remainder.endswith("|"):
                remainder = remainder[:-1].strip()
            remainder = remainder.strip("`")
            if remainder:
                values.append(remainder)
            break
    unique = sorted(set(values))
    if len(unique) != 1:
        return None, "packet field %s must have one unambiguous value" % field_names[0]
    return unique[0], None


def _status_evidence(status_short):
    """Compact exact evidence token suitable for a one-line packet field."""
    if status_short == "":
        return "CLEAN"
    return "sha256:" + hashlib.sha256(status_short.encode("utf-8")).hexdigest()


def resolve_host_mode(routing, host_mode):
    if host_mode not in HOST_MODES:
        raise ConfigError(
            "host mode must be explicit and one of %s; got %r"
            % (sorted(HOST_MODES), host_mode)
        )
    mode = routing.get("host_modes", {}).get(host_mode)
    if not isinstance(mode, dict):
        raise ConfigError("routing file does not define host mode %s" % host_mode)
    return mode


def resolve_external_reviewer(routing, host_mode):
    reviewer = resolve_host_mode(routing, host_mode)["external_reviewer"]
    return reviewer["provider"], reviewer["profile"]


def resolve_tier_model(routing, host_mode, tier):
    """Return the project-local model override for a host tier (None = use the
    host adapter's pinned default, e.g. the agent frontmatter model)."""
    tiers = resolve_host_mode(routing, host_mode)["local_tiers"]
    if tier not in tiers:
        raise ConfigError("host mode %s does not define tier %s" % (host_mode, tier))
    return tiers[tier].get("model_override")


def resolve_tier_reasoning_effort(routing, host_mode, tier):
    """Return the controller-owned reasoning effort for a host tier."""
    tiers = resolve_host_mode(routing, host_mode)["local_tiers"]
    if tier not in tiers:
        raise ConfigError("host mode %s does not define tier %s" % (host_mode, tier))
    return tiers[tier].get("reasoning_effort")


# ---------------------------------------------------------------------------
# Provider argv construction
# ---------------------------------------------------------------------------


def extract_provider_result_schema(canonical_schema, role):
    """Mechanically select one role transport from the canonical schema SSOT."""
    definition_name = PROVIDER_TRANSPORT_DEFINITION_BY_ROLE.get(role)
    if definition_name is None:
        raise ConfigError("unsupported provider-result role: %r" % role)
    try:
        canonical_defs = canonical_schema["$defs"]
        provider_schema = copy.deepcopy(canonical_defs[definition_name])
    except (KeyError, TypeError) as exc:
        raise ConfigError(
            "canonical schema does not define $defs.%s" % definition_name
        ) from exc
    if not isinstance(provider_schema, dict):
        raise ConfigError("$defs.%s must be an object schema" % definition_name)
    if "$defs" in provider_schema:
        raise ConfigError("$defs.%s must not contain a nested $defs" % definition_name)
    dependencies = {}
    for dependency_name in PROVIDER_TRANSPORT_DEPENDENCIES_BY_ROLE[role]:
        dependency = canonical_defs.get(dependency_name)
        if not isinstance(dependency, dict):
            raise ConfigError(
                "canonical schema does not define object $defs.%s" % dependency_name
            )
        dependencies[dependency_name] = copy.deepcopy(dependency)
    provider_schema["$defs"] = dependencies
    return provider_schema


def extract_provider_substantive_task(packet_text, role, invocation_path):
    """Return a provider-only prompt for the corrective host-local scout.

    The complete packet remains the controller's evidence and authorization
    input. The provider receives only the one explicitly delimited substantive
    section, so it cannot be asked to repeat controller-owned provenance checks.
    Other established runner paths retain their existing prompt contract.
    """
    if role != "feasibility_verifier" or invocation_path != "host_local_cli":
        return packet_text, "full_packet"
    if packet_text.count(PROVIDER_TASK_START) != 1:
        raise ConfigError(
            "host-local feasibility packet must contain exactly one provider "
            "substantive task start marker"
        )
    if packet_text.count(PROVIDER_TASK_END) != 1:
        raise ConfigError(
            "host-local feasibility packet must contain exactly one provider "
            "substantive task end marker"
        )
    start = packet_text.index(PROVIDER_TASK_START) + len(PROVIDER_TASK_START)
    end = packet_text.index(PROVIDER_TASK_END)
    if end <= start:
        raise ConfigError("provider substantive task markers are out of order")
    substantive = packet_text[start:end].strip()
    if not substantive:
        raise ConfigError("provider substantive task must not be empty")
    protected = [
        label for label in PROVIDER_TASK_PROTECTED_LABELS if label.lower() in substantive.lower()
    ]
    if protected:
        raise ConfigError(
            "provider substantive task contains controller-only packet labels: "
            + ", ".join(protected)
        )
    return FEASIBILITY_PROVIDER_PREAMBLE + substantive + "\n", "substantive_only"


def validate_provider_transport_result(result, provider_schema):
    """Validate the exact selected transport surface before normalization."""
    if not isinstance(result, dict):
        return ["provider result is not a JSON object"]
    properties = provider_schema.get("properties")
    required = provider_schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        return ["selected provider transport schema is malformed"]
    expected = set(properties)
    errors = []
    missing = sorted(set(required) - set(result))
    if missing:
        errors.append("provider transport missing required fields: %s" % ", ".join(missing))
    extra = sorted(set(result) - expected)
    controller_owned = sorted(set(extra).intersection(CONTROLLER_OWNED_RESULT_FIELDS))
    if controller_owned:
        errors.append(
            "provider transport contains controller-owned fields: %s"
            % ", ".join(controller_owned)
        )
    other_extra = sorted(set(extra) - set(controller_owned))
    if other_extra:
        errors.append(
            "provider transport contains fields outside the selected role schema: %s"
            % ", ".join(other_extra)
        )
    verdict_schema = properties.get("verdict")
    if (
        isinstance(verdict_schema, dict)
        and isinstance(verdict_schema.get("enum"), list)
        and result.get("verdict") not in verdict_schema["enum"]
    ):
        errors.append(
            "provider transport verdict must be one of %s"
            % sorted(verdict_schema["enum"])
        )
    return errors


def normalize_provider_result(result, role):
    """Add only lossless canonical empty fields after transport validation."""
    if role not in PROVIDER_TRANSPORT_DEFINITION_BY_ROLE:
        raise ConfigError("unsupported provider-result role: %r" % role)
    normalized = copy.deepcopy(result)
    defaults = {}
    if role == "feasibility_verifier":
        defaults["changed_files"] = []
    if role != "adversarial_reviewer":
        defaults.update({field: [] for field in REVIEWER_COLLECTIONS})
    illegal = sorted(set(normalized).intersection(defaults))
    if illegal:
        raise ConfigError(
            "provider supplied canonical-only fields before normalization: %s"
            % ", ".join(illegal)
        )
    normalized.update(defaults)
    return normalized


def build_provider_command(
    provider,
    profile,
    model,
    reasoning_effort,
    workdir,
    artifact_dir,
    provider_schema_file,
):
    """Return (argv, provider_metadata) for the single external process."""
    if provider == "codex_cli":
        sandbox = "workspace-write" if profile == "codex_workspace_write" else "read-only"
        argv = [
            "codex",
            "exec",
        ]
        if reasoning_effort is not None:
            if reasoning_effort not in REASONING_EFFORTS:
                raise ConfigError(
                    "unsupported Codex reasoning effort: %r" % reasoning_effort
                )
            argv += ["--ignore-user-config", "--strict-config"]
        argv += [
            "-C",
            str(workdir),
            "-s",
            sandbox,
            "-c",
            "approval_policy=never",
        ]
        if reasoning_effort is not None:
            argv += ["-c", "model_reasoning_effort=%s" % reasoning_effort]
        network = None
        if profile == "codex_workspace_write":
            argv += ["-c", "sandbox_workspace_write.network_access=false"]
            network = {
                "requested_config": "sandbox_workspace_write.network_access=false",
                "verified_by_real_cli": False,
                "note": (
                    "config override request recorded only; actual network "
                    "enforcement is verified in the opt-in real-CLI smoke test"
                ),
            }
        argv += [
            "--json",
            "--output-schema",
            str(provider_schema_file),
            "-m",
            model,
            "--output-last-message",
            str(artifact_dir / "provider-result.json"),
            "-",
        ]
        metadata = {
            "sandbox": sandbox,
            "approval_policy": "approval_policy=never (config override; codex exec has no approval flag)",
            "network": network,
            "user_config_ignored": reasoning_effort is not None,
            "strict_config": reasoning_effort is not None,
        }
        return argv, metadata
    if provider == "claude_cli":
        schema_text = provider_schema_file.read_text(encoding="utf-8")
        argv = [
            "claude",
            "-p",
            "--verbose",
            "--model",
            model,
            "--permission-mode",
            "plan",
            "--tools",
            "Read,Glob,Grep",
            "--disallowedTools",
            "Bash,Edit,Write,NotebookEdit,Task",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--output-format",
            "stream-json",
            "--json-schema",
            schema_text,
        ]
        forbidden_flags = ("--resume", "--continue", "--fork-session", "--mcp-config")
        for flag in forbidden_flags:
            if flag in argv:
                raise ConfigError("internal error: forbidden flag %s in claude argv" % flag)
        metadata = {
            "sandbox": "permission-mode=plan; tools allowlist Read,Glob,Grep; deny Bash,Edit,Write,NotebookEdit,Task; strict MCP (none); slash commands disabled",
            "approval_policy": "n/a (non-interactive -p, plan permission mode)",
            "network": None,
            "user_config_ignored": None,
            "strict_config": None,
        }
        return argv, metadata
    raise ConfigError("no external command semantics for provider %s" % provider)


def sanitize_argv(argv):
    sanitized = []
    for element in argv:
        if len(element) > MAX_RECORDED_ARG_LEN:
            digest = hashlib.sha256(element.encode("utf-8")).hexdigest()
            sanitized.append("<inline-argument sha256=%s len=%d>" % (digest, len(element)))
        else:
            sanitized.append(element)
    return sanitized


# ---------------------------------------------------------------------------
# Child process management
# ---------------------------------------------------------------------------


def _capture_cli_version(executable):
    try:
        proc = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.decode(errors="replace").strip() or None


def _spawn_child(argv, workdir, stdin_fh, stdout_fh, stderr_fh):
    """Start the single external CLI process in its own session/process group."""
    return subprocess.Popen(
        argv,
        cwd=str(workdir),
        stdin=stdin_fh,
        stdout=stdout_fh,
        stderr=stderr_fh,
        start_new_session=True,
    )


def _terminate_process_group(proc, grace_seconds):
    """SIGTERM the whole child process group, escalate to SIGKILL after grace."""
    try:
        pgid = os.getpgid(proc.pid)
    except ProcessLookupError:
        proc.wait()
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


# ---------------------------------------------------------------------------
# Structured result extraction and validation
# ---------------------------------------------------------------------------


def _extract_codex_result(artifact_dir):
    final_path = artifact_dir / "provider-result.json"
    if not final_path.is_file():
        return None, "final structured result file was not produced"
    try:
        parsed = json.loads(final_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return None, "final result is not valid JSON: %s" % exc
    if not isinstance(parsed, dict):
        return None, "final result is not a JSON object"
    return parsed, None


def _extract_provider_metadata(stdout_path):
    """Read provider-owned event metadata without trusting substantive output.

    Model aliases may expand. The runner records requested_model separately
    and preserves any CLI-reported model as evidence; inequality is not an
    output-validation failure. Session/thread IDs are likewise event evidence.
    """
    reported_model = None
    reported_reasoning_effort = None
    session_id = None

    def visit(value):
        nonlocal reported_model, reported_reasoning_effort, session_id
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "model" and isinstance(item, str) and item:
                    reported_model = item
                elif (
                    key in ("reasoning_effort", "model_reasoning_effort")
                    and isinstance(item, str)
                    and item
                ):
                    reported_reasoning_effort = item
                elif key in ("session_id", "thread_id") and isinstance(item, str) and item:
                    session_id = item
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    try:
        with open(stdout_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    visit(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return {
        "reported_model": reported_model,
        "reported_reasoning_effort": reported_reasoning_effort,
        "session_id": session_id,
    }


def _extract_claude_result(stdout_path):
    last_result_event = None
    try:
        with open(stdout_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if isinstance(obj, dict) and obj.get("type") == "result":
                    last_result_event = obj
    except OSError as exc:
        return None, "stdout transcript unreadable: %s" % exc
    if last_result_event is None:
        return None, "no result event found in stream-json output"
    structured = last_result_event.get("structured_output")
    if isinstance(structured, dict):
        return structured, None
    raw = last_result_event.get("result")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except ValueError:
            return None, "result event payload is not valid JSON"
        if isinstance(parsed, dict):
            return parsed, None
    return None, "result event carries no structured output object"


def validate_result(result, role):
    """Validate provider-owned substantive content only.

    The strict provider transport schema rejects extra provenance-like fields;
    this local validation repeats the exact-field and role-specific checks so
    fake transports and post-processing fail closed in the same way. The
    provider is never asked to echo authority, host, invocation, model, or
    session metadata.
    """
    errors = []
    if not isinstance(result, dict):
        return ["provider result is not a JSON object"]
    for field in PROVIDER_RESULT_REQUIRED:
        if field not in result:
            errors.append("missing required field: %s" % field)
    extra = sorted(set(result) - set(PROVIDER_RESULT_REQUIRED))
    if extra:
        errors.append(
            "provider result contains controller-owned or unknown fields: %s"
            % ", ".join(extra)
        )
    if errors:
        return errors
    for field in ("verdict", "summary"):
        if not isinstance(result[field], str) or not result[field]:
            errors.append("%s must be a non-empty string" % field)
    if not isinstance(result["evidence"], list) or any(
        not isinstance(item, str) for item in result["evidence"]
    ):
        errors.append("evidence must be a list of strings")
    if result["stop_reason"] is not None and not isinstance(result["stop_reason"], str):
        errors.append("stop_reason must be a string or null")
    if not isinstance(result["changed_files"], list) or any(
        not isinstance(item, str) for item in result["changed_files"]
    ):
        errors.append("changed_files must be a list of strings")
    if not isinstance(result["tests"], list):
        errors.append("tests must be a list")
    else:
        for index, entry in enumerate(result["tests"]):
            if not isinstance(entry, dict):
                errors.append("tests[%d] must be an object" % index)
                continue
            if not isinstance(entry.get("command"), str) or not entry.get("command"):
                errors.append("tests[%d].command must be a non-empty string" % index)
            if entry.get("status") not in {"passed", "failed", "skipped"}:
                errors.append("tests[%d].status must be passed/failed/skipped" % index)
            if "output_digest" not in entry or not (
                entry["output_digest"] is None or isinstance(entry["output_digest"], str)
            ):
                errors.append("tests[%d].output_digest must be a string or null" % index)
    state = result["repository_state"]
    if (
        not isinstance(state, dict)
        or set(state) != {"pre", "post"}
        or not isinstance(state.get("pre"), dict)
        or not isinstance(state.get("post"), dict)
    ):
        errors.append("repository_state must contain pre and post objects")
    else:
        for point in ("pre", "post"):
            git_state = state[point]
            if set(git_state) != {"head_sha", "status_short"}:
                errors.append(
                    "repository_state.%s must contain exactly head_sha/status_short"
                    % point
                )
            elif not isinstance(git_state["head_sha"], str) or not isinstance(
                git_state["status_short"], str
            ):
                errors.append(
                    "repository_state.%s head_sha/status_short must be strings" % point
                )
    if role == "feasibility_verifier" and result["verdict"] not in FEASIBILITY_VERDICTS:
        errors.append("feasibility verdict must be one of %s" % sorted(FEASIBILITY_VERDICTS))
    if role in READ_ONLY_ROLES and result["changed_files"]:
        errors.append("read-only role must report an empty changed_files list")
    for field in REVIEWER_COLLECTIONS:
        if not isinstance(result[field], list):
            errors.append("%s must be a list" % field)
    if role == "adversarial_reviewer":
        for field in ("observations", "suggestions", "evidence_gaps"):
            if isinstance(result[field], list) and any(
                not isinstance(item, str) for item in result[field]
            ):
                errors.append("%s must be a list of strings" % field)
        for index, finding in enumerate(
            result["findings"] if isinstance(result["findings"], list) else []
        ):
            if not isinstance(finding, dict):
                errors.append("findings[%d] must be an object" % index)
                continue
            for field in FINDING_REQUIRED:
                value = finding.get(field)
                if not isinstance(value, str) or not value:
                    errors.append(
                        "findings[%d] missing/empty required field: %s" % (index, field)
                    )
            severity = finding.get("severity")
            if severity is not None and severity not in SEVERITIES:
                errors.append(
                    "findings[%d] severity must be one of %s" % (index, sorted(SEVERITIES))
                )
    else:
        for field in REVIEWER_COLLECTIONS:
            if isinstance(result[field], list) and result[field]:
                errors.append(
                    "non-reviewer role must report an empty %s list" % field
                )
    return errors


def map_verdict_outcome(result):
    """Explicit verdict mapping — never natural-language guessing."""
    verdict = result["verdict"]
    if verdict == "MODEL_REPORTED_BLOCKER":
        return MODEL_REPORTED_BLOCKER
    if verdict == "STOPPED":
        return STOPPED
    if result["stop_reason"] is not None:
        return STOPPED
    return SUCCESS


# ---------------------------------------------------------------------------
# Artifact bundle and manifest
# ---------------------------------------------------------------------------


def _write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_manifest(artifact_dir):
    manifest_path = artifact_dir / "manifest.sha256"
    lines = []
    for path in sorted(artifact_dir.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        rel = path.relative_to(artifact_dir).as_posix()
        lines.append("%s  %s" % (_sha256_file(path), rel))
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest_path


def verify_manifest(artifact_dir):
    """Return (ok, problems). Strict: hashes, missing files, and extra files all fail."""
    artifact_dir = Path(artifact_dir)
    manifest_path = artifact_dir / "manifest.sha256"
    problems = []
    if not manifest_path.is_file():
        return False, ["manifest.sha256 is missing"]
    recorded = {}
    for line_number, line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            digest, rel = line.split("  ", 1)
        except ValueError:
            problems.append("manifest line %d is malformed" % line_number)
            continue
        recorded[rel] = digest
    actual = {}
    for path in sorted(artifact_dir.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        rel = path.relative_to(artifact_dir).as_posix()
        actual[rel] = _sha256_file(path)
    for rel in sorted(set(recorded) - set(actual)):
        problems.append("missing artifact: %s" % rel)
    for rel in sorted(set(actual) - set(recorded)):
        problems.append("unlisted artifact present: %s" % rel)
    for rel in sorted(set(recorded) & set(actual)):
        if recorded[rel] != actual[rel]:
            problems.append("hash mismatch: %s" % rel)
    return not problems, problems


# ---------------------------------------------------------------------------
# run subcommand
# ---------------------------------------------------------------------------


def _positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _positive_float(value):
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive number")
    return number


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _changed_paths_from_entries(entries):
    paths = set()
    for entry in entries:
        paths.add(entry["path"])
        if "orig_path" in entry:
            paths.add(entry["orig_path"])
    return paths


def cmd_run(args):
    governance_identity = {
        field: getattr(args, field, None) for field in GOVERNANCE_IDENTITY_FIELDS
    }
    invocation = {
        "role": args.role,
        "host_mode": args.host_mode,
        "invocation_path": args.invocation_path,
        "governance_identity": governance_identity,
        "external_side_effect_authorization": None,
        "host_local_execution_authorization": None,
        "execution_host": None,
        "host_tier": args.host_tier,
        "host_adapter_status": None,
        "provider": None,
        "profile": None,
        "requested_model": args.model,
        "resolved_model": None,
        "reported_model": None,
        "requested_reasoning_effort": args.reasoning_effort,
        "resolved_reasoning_effort": None,
        "reported_reasoning_effort": None,
        "executable": None,
        "cli_version": None,
        "workdir": str(args.workdir),
        "authoritative_plan_sha": args.authoritative_plan_sha,
        "candidate_sha": args.candidate_sha,
        "target_repository_head": args.target_repository_head,
        "target_repository_status": args.target_repository_status,
        "base_sha": args.base_sha,
        "target_sha": args.target_sha,
        "sandbox": None,
        "approval_policy": None,
        "network": None,
        "user_config_ignored": None,
        "strict_config": None,
        "allowed_files": sorted(args.allowed_file or []),
        "forbidden_files": sorted(args.forbidden_file or []),
        "started_at": None,
        "ended_at": None,
        "duration_seconds": None,
        "timeout_seconds": args.timeout_seconds,
        "child_exit_code": None,
        "child_signal": None,
        "session_id": None,
        "resume_session_id": args.resume_session_id,
        "outcome": None,
        "detail": None,
        "argv": None,
        "provider_task_mode": None,
        "provider_task_sha256": None,
    }
    artifact_dir = Path(args.artifact_dir)

    def finish(outcome, detail):
        invocation["outcome"] = outcome
        invocation["detail"] = detail
        if artifact_dir.is_dir():
            _write_json(artifact_dir / "invocation.json", invocation)
            generate_manifest(artifact_dir)
        print(
            json.dumps(
                {"outcome": outcome, "detail": detail, "artifact_dir": str(artifact_dir)}
            )
        )
        return EXIT_BY_OUTCOME.get(outcome, 1)

    # ---- configuration validation (fail closed, before any process start) ----
    try:
        workdir = Path(args.workdir)
        if not workdir.is_absolute() or not workdir.is_dir():
            raise ConfigError("workdir must be an existing absolute directory")
        task_file = Path(args.task_file)
        if not task_file.is_absolute() or not task_file.is_file():
            raise ConfigError("task-file must be an existing absolute file path")
        packet_text = task_file.read_text(encoding="utf-8", errors="replace")
        if not artifact_dir.is_absolute():
            raise ConfigError("artifact-dir must be an absolute path")
        try:
            artifact_dir.relative_to(workdir)
            raise ConfigError("artifact-dir must not be inside the workdir (would pollute Git evidence)")
        except ValueError:
            pass
        if artifact_dir.exists():
            if not artifact_dir.is_dir() or any(artifact_dir.iterdir()):
                raise ConfigError("artifact-dir must be a new or empty directory")
        else:
            artifact_dir.mkdir(parents=True)
        if not RESULT_SCHEMA_FILE.is_file():
            raise ConfigError("result schema file missing: %s" % RESULT_SCHEMA_FILE)
        try:
            schema_doc = json.loads(RESULT_SCHEMA_FILE.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ConfigError("result schema is not valid JSON: %s" % exc) from exc
        schema_errors = preflight_strict_schema(schema_doc)
        if schema_errors:
            # Fail closed before any provider spawn: no quota is consumed.
            raise ConfigError(
                "schema strict-subset preflight failed: " + "; ".join(schema_errors)
            )
        # Governance identity is packet-supplied and mandatory (fail closed).
        missing_identity = sorted(
            field
            for field, value in governance_identity.items()
            if not isinstance(value, str) or not value
        )
        if missing_identity:
            raise ConfigError(
                "governance identity missing or empty (fail closed): %s; the task "
                "packet must state every governance identity field explicitly"
                % ", ".join(missing_identity)
            )
        identity_values = {
            "authoritative plan SHA": args.authoritative_plan_sha,
            "candidate SHA": args.candidate_sha,
            "target repository HEAD": args.target_repository_head,
        }
        for label, value in identity_values.items():
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", value):
                raise ConfigError("%s must be an explicit 40-hex identity" % label)
        if args.target_repository_status is None:
            raise ConfigError(
                "target repository status/dirty-state evidence must be explicit"
            )
        packet_identity_contract = (
            (
                ("Authoritative plan commit SHA", "Authoritative plan SHA"),
                args.authoritative_plan_sha,
            ),
            (
                (
                    "Release/implementation candidate SHA",
                    "Release／implementation candidate SHA",
                    "Candidate SHA",
                ),
                args.candidate_sha,
            ),
            (("Target repository HEAD",), args.target_repository_head),
            (
                (
                    "Target repository status/dirty-state evidence",
                    "Target repository status／dirty-state evidence",
                ),
                args.target_repository_status,
            ),
        )
        for field_names, expected in packet_identity_contract:
            packet_value, packet_error = _parse_packet_identity(
                packet_text, field_names
            )
            if packet_error:
                raise ConfigError(packet_error)
            if packet_value != expected:
                raise ConfigError(
                    "packet/invocation identity mismatch for %s: packet=%r "
                    "invocation=%r" % (field_names[0], packet_value, expected)
                )

        routing = load_routing(args.routing_file)
        routing_errors = validate_routing(routing)
        if routing_errors:
            raise ConfigError("routing validation failed: " + "; ".join(routing_errors))

        host_conf = resolve_host_mode(routing, args.host_mode)
        invocation["execution_host"] = host_conf["active_host"]
        invocation["host_adapter_status"] = host_conf["adapter_status"]

        if args.invocation_path not in INVOCATION_PATHS:
            raise ConfigError(
                "invocation path must be explicit and one of %s; got %r"
                % (sorted(INVOCATION_PATHS), args.invocation_path)
            )
        if args.host_tier is not None and args.host_tier not in HOST_TIERS:
            raise ConfigError("host tier must be one of %s or omitted" % sorted(HOST_TIERS))

        # Session boundary rules. One invocation executes exactly one role;
        # nothing here ever chains, retries, falls back, or auto-resumes.
        if args.resume_session_id is not None:
            if args.role in READ_ONLY_ROLES:
                raise ConfigError(
                    "session resume is not permitted for role %s (fresh session required)"
                    % args.role
                )
            # implementer resume: deferred fail closed — the full resume
            # metadata contract is not implemented in this batch, and resume
            # must not be pretended to work.
            return finish(
                CAPABILITY_UNAVAILABLE,
                "implementer session resume is not supported yet (fail closed; "
                "requires the recorded-session metadata contract)",
            )

        # Dual-host role/path matrix. Feasibility and implementation belong to
        # the active host; only the adversarial reviewer (and the separately
        # authorized headless implementer) ever reach an external CLI here.
        if args.role == "adversarial_reviewer":
            if args.reasoning_effort is not None:
                raise ConfigError(
                    "reasoning effort is controller-owned only for the "
                    "Codex-hosted host_local_cli scout"
                )
            if args.invocation_path != "external_cli":
                raise ConfigError(
                    "adversarial_reviewer runs only via invocation path external_cli"
                )
            if args.host_tier is not None:
                raise ConfigError("external reviewer must not claim a host-local tier")
            provider, profile = resolve_external_reviewer(routing, args.host_mode)
        elif args.role == "feasibility_verifier":
            if args.host_mode == "codex_hosted":
                if args.invocation_path != "host_local_cli":
                    raise ConfigError(
                        "codex_hosted feasibility_verifier must use host_local_cli"
                    )
                if args.host_tier != "scout":
                    raise ConfigError(
                        "codex_hosted host_local_cli feasibility requires host tier scout"
                    )
                scout = host_conf["local_tiers"]["scout"]
                provider, profile = scout["provider"], scout["profile"]
                resolved_model = scout.get("model_override")
                resolved_reasoning_effort = scout.get("reasoning_effort")
                if (
                    provider != "codex_cli"
                    or profile != "codex_read_only"
                    or resolved_model != "gpt-5.6-luna"
                    or resolved_reasoning_effort != "low"
                    or args.model != resolved_model
                    or args.reasoning_effort != resolved_reasoning_effort
                ):
                    raise ConfigError(
                        "host_local_cli is restricted to codex_hosted/"
                        "feasibility_verifier/scout/codex_cli/codex_read_only/"
                        "gpt-5.6-luna/reasoning_effort=low"
                    )
                packet_effort, packet_effort_error = _parse_packet_identity(
                    packet_text,
                    (
                        "Host-local reasoning effort",
                        "Requested reasoning effort",
                        "Reasoning effort",
                    ),
                )
                if packet_effort_error or packet_effort != resolved_reasoning_effort:
                    raise ConfigError(
                        "host-local scout packet, routing, and CLI must all "
                        "specify reasoning effort low"
                    )
                invocation["resolved_model"] = resolved_model
                invocation["resolved_reasoning_effort"] = resolved_reasoning_effort
            elif args.invocation_path != "active_host":
                raise ConfigError(
                    "feasibility_verifier is an active-host responsibility "
                    "(invocation path active_host); external CLI feasibility is "
                    "not part of the dual-host contract"
                )
            elif host_conf["adapter_status"] != "implemented":
                return finish(
                    CAPABILITY_UNAVAILABLE,
                    "host-native execution required, but host mode %s adapter "
                    "is unavailable (fail closed)" % args.host_mode,
                )
            else:
                return finish(
                CAPABILITY_UNAVAILABLE,
                "host-native execution required: feasibility_verifier runs on "
                "the active host (%s) through its own host-local tier dispatch "
                "path; this external runner does not emulate the active host"
                    % host_conf["active_host"],
                )
        elif args.role == "implementer":
            if args.reasoning_effort is not None:
                raise ConfigError(
                    "reasoning effort is controller-owned only for the "
                    "Codex-hosted host_local_cli scout"
                )
            if args.invocation_path == "active_host":
                if args.host_tier not in ("worker", "executor"):
                    raise ConfigError(
                        "active-host implementer requires host tier worker or executor"
                    )
                if host_conf["adapter_status"] != "implemented":
                    return finish(
                        CAPABILITY_UNAVAILABLE,
                        "host-native execution required, but host mode %s adapter "
                        "is unavailable (fail closed)" % args.host_mode,
                    )
                return finish(
                    CAPABILITY_UNAVAILABLE,
                    "host-native execution required: implementer runs on the "
                    "active host (%s) through its own host-local worker/executor "
                    "tier; headless CLI implementation is a non-default opt-in "
                    "requiring --invocation-path headless_cli plus separate "
                    "authorization" % host_conf["active_host"],
                )
            if args.invocation_path != "headless_cli":
                raise ConfigError(
                    "implementer accepts only invocation paths active_host (default "
                    "contract) or headless_cli (separately authorized opt-in); "
                    "external_cli is not a valid implementer path"
                )
            if args.host_tier is not None:
                raise ConfigError("headless_cli implementer must not claim a host-local tier")
            headless = routing["headless_cli_implementation"]
            provider, profile = headless["provider"], headless["profile"]
        else:
            raise ConfigError("unsupported role: %s" % args.role)

        invocation["provider"] = provider
        invocation["profile"] = profile
        if invocation["resolved_model"] is None:
            invocation["resolved_model"] = args.model
        if provider not in EXTERNAL_PROVIDERS:
            raise ConfigError("unsupported external provider: %s" % provider)

        # Mechanical authorization preflight. host_local_cli execution and
        # external reviewer/headless invocation are distinct grants; neither
        # token authorizes the other path.
        # Prompt/command wording is never authorization; the packet field and
        # the caller flag must both carry ALLOW_PROVIDER_INVOCATION and agree,
        # per invocation — an implementer authorization never covers a
        # reviewer invocation, and vice versa. Any failure here happens before
        # the child process exists (no quota, no side effect).
        if args.invocation_path == "host_local_cli":
            if args.external_authorization is not None:
                raise ConfigError(
                    "external provider authorization cannot authorize host_local_cli"
                )
            packet_auth, auth_errors = parse_packet_host_local_authorization(packet_text)
            if auth_errors:
                raise ConfigError(
                    "host-local execution authorization preflight failed: "
                    + "; ".join(auth_errors)
                )
            if (
                args.host_local_authorization != packet_auth
                or packet_auth != ALLOW_HOST_LOCAL_CLI_INVOCATION
            ):
                raise ConfigError(
                    "host-local execution requires matching packet and CLI "
                    "ALLOW_HOST_LOCAL_CLI_INVOCATION authorization"
                )
            external_packet_auth, external_errors = parse_packet_external_authorization(
                packet_text
            )
            if external_errors or external_packet_auth == ALLOW_PROVIDER_INVOCATION:
                raise ConfigError(
                    "host-local scout packet must explicitly withhold external "
                    "provider authorization"
                )
            invocation["host_local_execution_authorization"] = packet_auth
        else:
            if args.host_local_authorization is not None:
                raise ConfigError(
                    "host-local execution authorization cannot authorize external_cli "
                    "or headless_cli"
                )
            packet_auth, auth_errors = parse_packet_external_authorization(packet_text)
            if auth_errors:
                raise ConfigError(
                    "external-side-effect authorization preflight failed: "
                    + "; ".join(auth_errors)
                )
            flag_auth = args.external_authorization
            if flag_auth is None or flag_auth != packet_auth:
                raise ConfigError(
                    "external-side-effect authorization mismatch between packet "
                    "and --external-authorization"
                )
            if packet_auth != ALLOW_PROVIDER_INVOCATION:
                raise ConfigError(
                    "external provider invocation is not authorized: packet carries "
                    "%r, expected %s; provider not spawned"
                    % (packet_auth, ALLOW_PROVIDER_INVOCATION)
                )
            invocation["external_side_effect_authorization"] = packet_auth

        # The parsed role mechanically selects its provider transport
        # definition from the one canonical schema. The caller has no schema
        # selector, and every selected transport is strict-preflighted before
        # a provider process may start.
        provider_schema = extract_provider_result_schema(schema_doc, args.role)
        provider_schema_errors = preflight_strict_schema(provider_schema)
        if provider_schema_errors:
            raise ConfigError(
                "provider_result schema strict-subset preflight failed: "
                + "; ".join(provider_schema_errors)
            )
        provider_schema_file = artifact_dir / "provider-result.schema.json"
        _write_json(provider_schema_file, provider_schema)

        # Preserve the complete controller packet, but expose only the
        # marker-delimited substantive section to the corrective host-local
        # scout. This prevents the provider from repeating or adjudicating
        # controller-owned identity and authorization checks.
        shutil.copyfile(task_file, artifact_dir / "task.md")
        shutil.copyfile(args.routing_file, artifact_dir / "routing.json")
        provider_task, provider_task_mode = extract_provider_substantive_task(
            packet_text, args.role, args.invocation_path
        )
        provider_task_path = artifact_dir / "provider-task.md"
        provider_task_path.write_text(provider_task, encoding="utf-8")
        invocation["provider_task_mode"] = provider_task_mode
        invocation["provider_task_sha256"] = hashlib.sha256(
            provider_task.encode("utf-8")
        ).hexdigest()

        pre_state = _snapshot_git(workdir)
        _write_json(artifact_dir / "pre-git.json", pre_state)
        if pre_state["head"] != args.target_repository_head:
            raise ConfigError(
                "target repository HEAD mismatch: packet/invocation=%s actual=%s"
                % (args.target_repository_head, pre_state["head"])
            )
        if _status_evidence(pre_state["status_short"]) != args.target_repository_status:
            raise ConfigError(
                "target repository status/dirty-state evidence mismatch"
            )

        if args.role == "implementer" and (
            pre_state["status_entries"]
            or pre_state["tracked_diff_sha256"] != hashlib.sha256(b"").hexdigest()
            or pre_state["cached_diff_sha256"] != hashlib.sha256(b"").hexdigest()
        ):
            # Fail closed: with a dirty pre-state we cannot reliably attribute
            # deltas to the agent, and we must never clean existing user work.
            raise ConfigError(
                "implementer requires a clean worktree; pre-existing changes present "
                "(runner never cleans or reverts them)"
            )

        argv, provider_meta = build_provider_command(
            provider,
            profile,
            invocation["resolved_model"],
            invocation["resolved_reasoning_effort"],
            workdir,
            artifact_dir,
            provider_schema_file,
        )
        invocation["sandbox"] = provider_meta["sandbox"]
        invocation["approval_policy"] = provider_meta["approval_policy"]
        invocation["network"] = provider_meta["network"]
        invocation["user_config_ignored"] = provider_meta["user_config_ignored"]
        invocation["strict_config"] = provider_meta["strict_config"]
        invocation["argv"] = sanitize_argv(argv)
        invocation["executable"] = shutil.which(argv[0])
        if invocation["executable"] is None:
            raise ConfigError("executable not found on PATH: %s" % argv[0])
        invocation["cli_version"] = _capture_cli_version(argv[0])
    except ConfigError as exc:
        return finish(CONFIGURATION_ERROR, str(exc))

    # ---- single child process execution ----
    stdout_path = artifact_dir / "stdout.jsonl"
    stderr_path = artifact_dir / "stderr.log"
    timed_out = False
    interrupted = False
    invocation["started_at"] = _utc_now()
    start_clock = time.monotonic()
    with open(provider_task_path, "rb") as stdin_fh, open(stdout_path, "wb") as stdout_fh, open(
        stderr_path, "wb"
    ) as stderr_fh:
        try:
            child = _spawn_child(argv, workdir, stdin_fh, stdout_fh, stderr_fh)
        except OSError as exc:
            return finish(CONFIGURATION_ERROR, "failed to start child process: %s" % exc)
        try:
            child.wait(timeout=args.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_process_group(child, args.grace_seconds)
        except KeyboardInterrupt:
            interrupted = True
            _terminate_process_group(child, args.grace_seconds)
    invocation["ended_at"] = _utc_now()
    invocation["duration_seconds"] = round(time.monotonic() - start_clock, 3)
    invocation["child_exit_code"] = child.returncode if child.returncode >= 0 else None
    invocation["child_signal"] = -child.returncode if child.returncode < 0 else None

    # ---- post evidence (always captured, including on timeout/interrupt) ----
    try:
        post_state = _snapshot_git(workdir)
    except ConfigError as exc:
        return finish(CONFIGURATION_ERROR, "post-run git evidence failed: %s" % exc)
    _write_json(artifact_dir / "post-git.json", post_state)

    differences = _snapshot_differences(pre_state, post_state)
    changed_paths = sorted(
        _changed_paths_from_entries(post_state["status_entries"])
        - _changed_paths_from_entries(pre_state["status_entries"])
    )
    allowed = set(invocation["allowed_files"])
    forbidden = set(invocation["forbidden_files"])
    violations = sorted(
        path for path in changed_paths if path in forbidden or path not in allowed
    )
    head_changed = pre_state["head"] != post_state["head"]
    index_changed = pre_state["cached_diff_sha256"] != post_state["cached_diff_sha256"]
    _write_json(
        artifact_dir / "changed-paths.json",
        {
            "read_only_role": args.role in READ_ONLY_ROLES,
            "differences": differences,
            "changed_paths": changed_paths,
            "allowed_files": sorted(allowed),
            "forbidden_files": sorted(forbidden),
            "violations": violations,
            "head_changed": head_changed,
            "index_changed": index_changed,
        },
    )

    # ---- structured result extraction (evidence even when a safety class wins) ----
    result = None
    result_error = None
    if provider == "codex_cli":
        result, result_error = _extract_codex_result(artifact_dir)
    else:
        result, result_error = _extract_claude_result(stdout_path)
        if result is not None:
            _write_json(artifact_dir / "provider-result.json", result)
    provider_metadata = _extract_provider_metadata(stdout_path)
    invocation["reported_model"] = provider_metadata["reported_model"]
    invocation["reported_reasoning_effort"] = provider_metadata[
        "reported_reasoning_effort"
    ]
    invocation["session_id"] = provider_metadata["session_id"]

    # ---- classification (priority: never let a lesser class mask a safety failure) ----
    if timed_out:
        return finish(TIMEOUT, "child exceeded %ds wall-clock timeout; process group terminated" % args.timeout_seconds)
    if interrupted:
        return finish(INTERRUPTED, "runner interrupted; child process group terminated")
    if not stdout_path.is_file() or not stderr_path.is_file():
        return finish(TRANSCRIPT_INCOMPLETE, "raw transcript artifact missing after run")
    if args.role in READ_ONLY_ROLES and differences:
        return finish(
            READ_ONLY_MUTATION,
            "repository changed during read-only role: " + "; ".join(differences),
        )
    if args.role == "implementer" and (head_changed or index_changed):
        return finish(
            FORBIDDEN_PATH_CHANGED,
            "unauthorized Git write detected (HEAD or index changed); evidence preserved",
        )
    if args.role == "implementer" and violations:
        return finish(
            FORBIDDEN_PATH_CHANGED,
            "changed paths outside the allowed set: %s" % ", ".join(violations),
        )
    if child.returncode != 0:
        return finish(
            PROCESS_NONZERO,
            "child exited with %s (stderr preserved separately)"
            % (
                "signal %d" % -child.returncode
                if child.returncode < 0
                else "code %d" % child.returncode
            ),
        )
    if result is None:
        return finish(INVALID_OUTPUT, result_error or "final structured result missing")
    if args.invocation_path == "host_local_cli":
        if (
            provider_metadata["reported_model"] is not None
            and provider_metadata["reported_model"] != invocation["resolved_model"]
        ):
            return finish(
                INVALID_OUTPUT,
                "host-local scout reported model %r, expected %r"
                % (
                    provider_metadata["reported_model"],
                    invocation["resolved_model"],
                ),
            )
        if (
            provider_metadata["reported_reasoning_effort"] is not None
            and provider_metadata["reported_reasoning_effort"]
            != invocation["resolved_reasoning_effort"]
        ):
            return finish(
                INVALID_OUTPUT,
                "host-local scout reported reasoning effort %r, expected %r"
                % (
                    provider_metadata["reported_reasoning_effort"],
                    invocation["resolved_reasoning_effort"],
                ),
            )
    transport_errors = validate_provider_transport_result(result, provider_schema)
    if transport_errors:
        return finish(
            INVALID_OUTPUT,
            "provider transport validation failed: " + "; ".join(transport_errors),
        )
    try:
        normalized_result = normalize_provider_result(result, args.role)
    except ConfigError as exc:
        return finish(INVALID_OUTPUT, "provider normalization failed: %s" % exc)
    validation_errors = validate_result(normalized_result, args.role)
    if validation_errors:
        return finish(INVALID_OUTPUT, "result validation failed: " + "; ".join(validation_errors))
    provenance = {
        "governance_identity": governance_identity,
        "authoritative_plan_sha": args.authoritative_plan_sha,
        "candidate_sha": args.candidate_sha,
        "target_repository_head": args.target_repository_head,
        "host_mode": args.host_mode,
        "execution_host": invocation["execution_host"],
        "host_tier": args.host_tier,
        "role": args.role,
        "provider": provider,
        "profile": profile,
        "requested_model": args.model,
        "resolved_model": invocation["resolved_model"],
        "reported_model": provider_metadata["reported_model"],
        "requested_reasoning_effort": args.reasoning_effort,
        "resolved_reasoning_effort": invocation["resolved_reasoning_effort"],
        "reported_reasoning_effort": provider_metadata[
            "reported_reasoning_effort"
        ],
        "invocation_path": args.invocation_path,
        "session_id": provider_metadata["session_id"],
    }
    canonical_result = {
        "schema_version": 3,
        "provenance": provenance,
        "provider_result": normalized_result,
    }
    _write_json(artifact_dir / "final-result.json", canonical_result)
    outcome = map_verdict_outcome(normalized_result)
    if outcome == MODEL_REPORTED_BLOCKER:
        return finish(
            MODEL_REPORTED_BLOCKER,
            "model reported a blocker: %r" % normalized_result["stop_reason"],
        )
    if outcome == STOPPED:
        return finish(STOPPED, "model stopped: %r" % normalized_result["stop_reason"])
    return finish(SUCCESS, "verdict=%s" % normalized_result["verdict"])


def cmd_verify_manifest(args):
    ok, problems = verify_manifest(args.artifact_dir)
    print(json.dumps({"manifest": "PASS" if ok else "FAIL", "problems": problems}))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="orchestration_agent.py",
        description="Bounded external-agent process runner (single role, single process).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run one external-agent invocation")
    run_parser.add_argument("--routing-file", required=True)
    run_parser.add_argument("--role", required=True, choices=SUPPORTED_ROLES)
    # Host/tier and governance identity are validated fail-closed inside
    # cmd_run (CONFIGURATION_ERROR with evidence), not by argparse.
    run_parser.add_argument("--host-mode")
    run_parser.add_argument("--host-tier")
    run_parser.add_argument("--invocation-path")
    run_parser.add_argument("--governance-authority", dest="governance_authority")
    run_parser.add_argument("--authorization-issuer", dest="authorization_issuer")
    run_parser.add_argument("--acceptance-owner", dest="acceptance_owner")
    run_parser.add_argument("--finding-adjudicator", dest="finding_adjudicator")
    run_parser.add_argument("--final-ratifier", dest="final_ratifier")
    run_parser.add_argument(
        "--external-authorization",
        dest="external_authorization",
        help="must equal the task packet's External-side-effect authorization "
        "value; both are required before any provider spawn (fail closed)",
    )
    run_parser.add_argument(
        "--host-local-authorization",
        dest="host_local_authorization",
        help="must equal the packet's Host-local execution authorization; "
        "valid only for the Codex-hosted scout host_local_cli path",
    )
    run_parser.add_argument("--workdir", required=True)
    run_parser.add_argument("--task-file", required=True)
    run_parser.add_argument("--artifact-dir", required=True)
    run_parser.add_argument("--timeout-seconds", required=True, type=_positive_int)
    run_parser.add_argument("--model", required=True)
    run_parser.add_argument(
        "--reasoning-effort",
        help="controller-owned Codex reasoning effort; required and fixed to "
        "low only for the Codex-hosted host_local_cli scout",
    )
    run_parser.add_argument("--authoritative-plan-sha")
    run_parser.add_argument("--candidate-sha")
    run_parser.add_argument("--target-repository-head")
    run_parser.add_argument("--target-repository-status")
    run_parser.add_argument("--base-sha")
    run_parser.add_argument("--target-sha")
    run_parser.add_argument("--allowed-file", action="append", default=[])
    run_parser.add_argument("--forbidden-file", action="append", default=[])
    run_parser.add_argument("--resume-session-id")
    run_parser.add_argument(
        "--grace-seconds",
        type=_positive_float,
        default=5.0,
        help="grace period between SIGTERM and SIGKILL on timeout/interrupt",
    )
    run_parser.set_defaults(func=cmd_run)

    verify_parser = sub.add_parser("verify-manifest", help="re-verify an artifact manifest")
    verify_parser.add_argument("--artifact-dir", required=True)
    verify_parser.set_defaults(func=cmd_verify_manifest)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
