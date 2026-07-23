#!/usr/bin/env python3
"""Bounded external-agent process runner for the orchestration plugin.

This runner is a narrow process-safety wrapper. Per invocation it:

- validates the project routing file (docs/playbook/agent-routing.json);
- validates role / provider / profile compatibility (fail closed);
- starts exactly one external CLI process (codex_cli or claude_cli);
- enforces a wall-clock timeout against the whole child process group;
- captures stdout and stderr separately, unmerged;
- records pre/post Git evidence with read-only Git commands only;
- detects repository mutation for read-only roles;
- validates implementation changed paths against allow/forbid lists;
- validates the final structured result against the Batch 1 envelope;
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
import hashlib
import json
import os
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

FIXED_AUTHORITY = {
    "architecture_owner": "chatgpt",
    "authoritative_plan_owner": "chatgpt",
    "authorization_owner": "chatgpt",
    "acceptance_owner": "chatgpt",
    "final_adjudicator": "chatgpt",
}

SUPPORTED_ROLES = ("feasibility_verifier", "implementer", "adversarial_reviewer")
READ_ONLY_ROLES = frozenset({"feasibility_verifier", "adversarial_reviewer"})
PROVIDER_KINDS = frozenset({"claude_subagent", "codex_cli", "claude_cli"})
EXTERNAL_PROVIDERS = frozenset({"codex_cli", "claude_cli"})

# profile -> (provider kind, write-capable)
PROFILES = {
    "codex_read_only": ("codex_cli", False),
    "codex_workspace_write": ("codex_cli", True),
    "claude_read_only": ("claude_cli", False),
    "scout": ("claude_subagent", False),
    "worker": ("claude_subagent", True),
    "executor": ("claude_subagent", True),
}

# The only Git subcommands this runner may ever execute (evidence collection).
GIT_READ_ONLY_SUBCOMMANDS = frozenset({"rev-parse", "status", "diff", "ls-files", "version"})

ENVELOPE_REQUIRED = (
    "schema_version",
    "role",
    "provider",
    "profile",
    "model",
    "verdict",
    "summary",
    "evidence",
    "stop_reason",
    "session_id",
    "changed_files",
    "tests",
    "repository_state",
)
REVIEWER_COLLECTIONS = ("findings", "observations", "suggestions", "evidence_gaps")
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
    tracked_diff = _git_text(workdir, ["diff", "--binary"])
    cached_diff = _git_text(workdir, ["diff", "--cached", "--binary"])
    return {
        "head": head,
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
    """Return a list of configuration errors (empty when routing is valid)."""
    errors = []
    if routing.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    authority = routing.get("authority")
    if authority != FIXED_AUTHORITY:
        errors.append(
            "authority ownership must be exactly the fixed ChatGPT values; got %r" % (authority,)
        )
    roles = routing.get("roles")
    if not isinstance(roles, dict):
        errors.append("roles must be an object")
        roles = {}
    for role_name, mapping in roles.items():
        if role_name not in SUPPORTED_ROLES:
            errors.append("unknown role: %s" % role_name)
            continue
        if not isinstance(mapping, dict):
            errors.append("role %s mapping must be an object" % role_name)
            continue
        provider = mapping.get("provider")
        profile = mapping.get("profile")
        if provider not in PROVIDER_KINDS:
            errors.append("role %s: unknown provider %r" % (role_name, provider))
            continue
        if profile not in PROFILES:
            errors.append("role %s: unknown profile %r" % (role_name, profile))
            continue
        profile_provider, write_capable = PROFILES[profile]
        if profile_provider != provider:
            errors.append(
                "role %s: profile %s belongs to provider %s, not %s"
                % (role_name, profile, profile_provider, provider)
            )
        if role_name in READ_ONLY_ROLES and write_capable:
            errors.append(
                "role %s is read-only but profile %s is write-capable" % (role_name, profile)
            )
    constraints = routing.get("constraints")
    if not isinstance(constraints, dict):
        errors.append("constraints must be an object")
        constraints = {}
    if constraints.get("implementer_may_dispatch_reviewer") is not False:
        errors.append("implementer_may_dispatch_reviewer must be false")
    if constraints.get("reviewer_may_modify_repository") is not False:
        errors.append("reviewer_may_modify_repository must be false")
    if constraints.get("external_git_writes_require_separate_authorization") is not True:
        errors.append("external_git_writes_require_separate_authorization must be true")
    if constraints.get("require_distinct_implementer_and_reviewer_provider") is True:
        impl = roles.get("implementer") if isinstance(roles, dict) else None
        rev = roles.get("adversarial_reviewer") if isinstance(roles, dict) else None
        if (
            isinstance(impl, dict)
            and isinstance(rev, dict)
            and impl.get("provider") == rev.get("provider")
        ):
            errors.append(
                "implementer and adversarial_reviewer resolve to the same provider (%s)"
                % impl.get("provider")
            )
    return errors


def resolve_role(routing, role):
    mapping = routing.get("roles", {}).get(role)
    if not isinstance(mapping, dict):
        raise ConfigError("routing file does not map role %s" % role)
    return mapping["provider"], mapping["profile"]


# ---------------------------------------------------------------------------
# Provider argv construction
# ---------------------------------------------------------------------------


def build_provider_command(provider, profile, model, workdir, artifact_dir):
    """Return (argv, provider_metadata) for the single external process."""
    if provider == "codex_cli":
        sandbox = "workspace-write" if profile == "codex_workspace_write" else "read-only"
        argv = [
            "codex",
            "exec",
            "-C",
            str(workdir),
            "-s",
            sandbox,
            "-c",
            "approval_policy=never",
        ]
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
            str(RESULT_SCHEMA_FILE),
            "-m",
            model,
            "--output-last-message",
            str(artifact_dir / "final-result.json"),
            "-",
        ]
        metadata = {
            "sandbox": sandbox,
            "approval_policy": "approval_policy=never (config override; codex exec has no approval flag)",
            "network": network,
        }
        return argv, metadata
    if provider == "claude_cli":
        schema_text = RESULT_SCHEMA_FILE.read_text(encoding="utf-8")
        argv = [
            "claude",
            "-p",
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
    final_path = artifact_dir / "final-result.json"
    if not final_path.is_file():
        return None, "final structured result file was not produced"
    try:
        parsed = json.loads(final_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return None, "final result is not valid JSON: %s" % exc
    if not isinstance(parsed, dict):
        return None, "final result is not a JSON object"
    return parsed, None


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


def validate_result(result, role, provider, profile):
    """Standard-library validation aligned with the Batch 1 result schema."""
    errors = []
    if not isinstance(result, dict):
        return ["final result is not a JSON object"]
    for field in ENVELOPE_REQUIRED:
        if field not in result:
            errors.append("missing required field: %s" % field)
    if errors:
        return errors
    if result["schema_version"] != 1:
        errors.append("schema_version must be 1")
    for field, expected in (("role", role), ("provider", provider), ("profile", profile)):
        if result[field] != expected:
            errors.append(
                "%s mismatch: invocation=%s result=%r" % (field, expected, result[field])
            )
    for field in ("model", "verdict", "summary"):
        if not isinstance(result[field], str) or not result[field]:
            errors.append("%s must be a non-empty string" % field)
    if not isinstance(result["evidence"], list) or any(
        not isinstance(item, str) for item in result["evidence"]
    ):
        errors.append("evidence must be a list of strings")
    if result["stop_reason"] is not None and not isinstance(result["stop_reason"], str):
        errors.append("stop_reason must be a string or null")
    if result["session_id"] is not None and not isinstance(result["session_id"], str):
        errors.append("session_id must be a string or null")
    if not isinstance(result["changed_files"], list) or any(
        not isinstance(item, str) for item in result["changed_files"]
    ):
        errors.append("changed_files must be a list of strings")
    if not isinstance(result["tests"], list):
        errors.append("tests must be a list")
    state = result["repository_state"]
    if not isinstance(state, dict) or not isinstance(state.get("pre"), dict) or not isinstance(
        state.get("post"), dict
    ):
        errors.append("repository_state must contain pre and post objects")
    if role == "feasibility_verifier" and result["verdict"] not in FEASIBILITY_VERDICTS:
        errors.append("feasibility verdict must be one of %s" % sorted(FEASIBILITY_VERDICTS))
    if role in READ_ONLY_ROLES and result["changed_files"]:
        errors.append("read-only role must report an empty changed_files list")
    if role == "adversarial_reviewer":
        for field in REVIEWER_COLLECTIONS:
            if not isinstance(result.get(field), list):
                errors.append("reviewer result must include list field: %s" % field)
        for index, finding in enumerate(result.get("findings") or []):
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
    invocation = {
        "role": args.role,
        "provider": None,
        "profile": None,
        "model": args.model,
        "executable": None,
        "cli_version": None,
        "workdir": str(args.workdir),
        "authoritative_plan_sha": args.authoritative_plan_sha,
        "base_sha": args.base_sha,
        "target_sha": args.target_sha,
        "sandbox": None,
        "approval_policy": None,
        "network": None,
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

        routing = load_routing(args.routing_file)
        routing_errors = validate_routing(routing)
        if routing_errors:
            raise ConfigError("routing validation failed: " + "; ".join(routing_errors))
        provider, profile = resolve_role(routing, args.role)
        invocation["provider"] = provider
        invocation["profile"] = profile

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

        if provider == "claude_subagent":
            return finish(
                CAPABILITY_UNAVAILABLE,
                "provider claude_subagent must be dispatched through the Claude Code "
                "Task path; this external runner does not emulate it",
            )
        if provider not in EXTERNAL_PROVIDERS:
            raise ConfigError("unsupported external provider: %s" % provider)

        # Copy controller inputs into the bundle.
        shutil.copyfile(task_file, artifact_dir / "task.md")
        shutil.copyfile(args.routing_file, artifact_dir / "routing.json")

        pre_state = _snapshot_git(workdir)
        _write_json(artifact_dir / "pre-git.json", pre_state)

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
            provider, profile, args.model, workdir, artifact_dir
        )
        invocation["sandbox"] = provider_meta["sandbox"]
        invocation["approval_policy"] = provider_meta["approval_policy"]
        invocation["network"] = provider_meta["network"]
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
    with open(task_file, "rb") as stdin_fh, open(stdout_path, "wb") as stdout_fh, open(
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
            _write_json(artifact_dir / "final-result.json", result)
    if result is not None and isinstance(result.get("session_id"), str):
        invocation["session_id"] = result["session_id"]

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
    validation_errors = validate_result(result, args.role, provider, profile)
    if validation_errors:
        return finish(INVALID_OUTPUT, "result validation failed: " + "; ".join(validation_errors))
    outcome = map_verdict_outcome(result)
    if outcome == MODEL_REPORTED_BLOCKER:
        return finish(MODEL_REPORTED_BLOCKER, "model reported a blocker: %r" % result["stop_reason"])
    if outcome == STOPPED:
        return finish(STOPPED, "model stopped: %r" % result["stop_reason"])
    return finish(SUCCESS, "verdict=%s" % result["verdict"])


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
    run_parser.add_argument("--workdir", required=True)
    run_parser.add_argument("--task-file", required=True)
    run_parser.add_argument("--artifact-dir", required=True)
    run_parser.add_argument("--timeout-seconds", required=True, type=_positive_int)
    run_parser.add_argument("--model", required=True)
    run_parser.add_argument("--authoritative-plan-sha")
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
