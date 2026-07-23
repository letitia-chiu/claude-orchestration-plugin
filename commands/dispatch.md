---
description: Turn a task into a dispatch order and route it by workflow role (role → agent-routing.json v2 → host mode / host-local tier / external reviewer)
argument-hint: the task to dispatch
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Task to dispatch: $ARGUMENTS

Read the **target project's** `docs/playbook/orchestration.md`, `docs/playbook/task-routing.md`, and `docs/playbook/agent-routing.json` (schema v2); if any is missing, prompt the user to run `/orchestration:init-playbook` first. Dispatch is role-first under the four-way separation **governance authority ≠ active execution host ≠ host-local execution tier ≠ external reviewer**: decide **what** the work is (workflow role), then let the routing file's host mode decide **who** executes it — feasibility and implementation belong to the active host's own scout/worker/executor tiers; the adversarial reviewer is the opposing provider's read-only CLI. The external CLI is never the default implementer, and the host's own CLI is never its own reviewer.

## 1. Classify the workflow role first

Decide which of these the task is — or that it is orchestrator-owned judgment (tone, precision micro-edits, ten-minute tasks) that should not be dispatched at all:

- **local read-only reconnaissance** — current-state/file/surface inventory (the active host's scout tier);
- **`feasibility_verifier`** — repository-local feasibility check against an authoritative plan commit; read-only, fresh session, three verdicts only; runs on the **active host's own local tier** (invocation path `active_host`), never an external CLI;
- **`implementer`** — one explicitly authorized implementation batch with exact allowed/forbidden paths; runs on the **active host's own worker/executor tier** (invocation path `active_host`); `headless_cli` is a non-default, separately authorized opt-in;
- **`adversarial_reviewer`** — fresh-context, read-only review of a frozen candidate by the **opposing provider's CLI** (invocation path `external_cli`); findings are candidates until the packet-named finding adjudicator rules on them.

Preserve the existing methodology while classifying — none of it is displaced by role routing:

1. **Generalize bug and review findings before writing the order.** A finding is evidence of a defect class, not merely a line to patch. State: observed instance → general defect class → authorized same-class search scope → expected proof of class closure. If the defect concerns Python runtime contracts, dataclasses, Protocols, callbacks, truthiness, enums, tuples, mappings, or frozen models, invoke the `python-runtime-contract-audit` skill and include its inventory and boundary-test requirements.
2. **Assign one invariant owner.** Production changes, shared validators, contract inventory, and boundary tests for the same invariant or defect family must stay with one executing agent/context. Do not split them across parallel executors. Parallelize only genuinely independent units with no shared invariant or contract surface.
3. **Do not dispatch an ambiguous class-closure task.** If you cannot name the defect family or authorized search scope, inspect the code or ask the user first.

## 2. Validate the task packet

Every dispatch needs a complete task packet (templates: `examples/task-packets/` in this plugin — active-host-feasibility / active-host-implementation / codex-adversarial-review / claude-adversarial-review / headless-codex-implementation). All 27 common fields are required — a missing field stops the dispatch; never guess a value in:

```text
Governance authority / Authorization issuer / Acceptance owner /
Finding adjudicator / Final ratifier /
Host mode / Active execution host / Host-local tier / Host-local model /
Invocation path / External reviewer provider/profile/model /
Role / Provider/profile / Explicit model / Repository/worktree /
Authoritative plan branch / Authoritative plan commit SHA / Canonical base SHA /
Target SHA or batch base SHA / Goal / Allowed files / Forbidden files /
Required evidence / Stop conditions / Git authorization /
External-side-effect authorization / Report schema
```

Governance identity is packet-scoped: the plugin never fixes it to ChatGPT, Claude, Codex, or any product, and no provider may rewrite these fields (the runner rejects a result whose identity fields differ from the packet).

The internal dispatch-order sections remain mandatory inside the packet body: 【Goal】【Scope】【No-go zones】【Invariant owner】【Defect-class closure】【Spec】【Acceptance】【Report format】. "Invariant owner" and "Defect-class closure" may be `not applicable` only when stated explicitly.

## 3. Resolve the route from the routing file

Read `<target-project>/docs/playbook/agent-routing.json` (schema v2), take the packet's `Host mode` (exactly one of `claude_hosted` / `codex_hosted`), and resolve:

- `feasibility_verifier` / `implementer` → the active host's local tier named in the packet (`role_bindings = active_host_local_tier`);
- `adversarial_reviewer` → that host mode's `external_reviewer` (claude_hosted → `codex_cli / codex_read_only`; codex_hosted → `claude_cli / claude_read_only`);
- check the resolution matches the packet's `Provider/profile`, `Host-local tier`, and `Invocation path` fields.

Stop before any spawn on: mismatch; unknown role/provider/profile/tier/host mode/invocation path; a routing file that pins a governance owner (a v1-style fixed `authority` block); a packet missing any governance identity field; a read-only role mapped to a write-capable profile; a host-local tier mapped to an external CLI; a host paired with its own provider family as reviewer; or `codex_hosted` active-host execution — **the Codex-host adapter is not implemented; fail closed, do not pretend it is available**.

## 4. Active-host tier path (Claude-hosted: Task tool)

When the role binding is `active_host_local_tier` under `claude_hosted`, dispatch via the Claude Code Task tool, selecting the existing agent by the packet's `Host-local tier` (`scout`, `worker`, `executor`). Requirements:

- pass the full task packet as the prompt;
- keep the invariant owner intact — one owner per invariant, never split;
- worker/executor are the tier selected for this dispatch by risk, not a permanent implementer identity;
- a higher tier grants no extra authority: the subagent must not dispatch a next role, and receives no Git or external-side-effect authority beyond what the packet lists;
- the tier's model comes from the agent definition's pin, or the project-local `model_override` in `agent-routing.json` (update-safe; init never overwrites it); a missing model = stop, never substitute;
- never modify the agent definitions.

## 5. External CLI path (bounded runner — reviewer, and opt-in headless only)

Only two dispatches ever reach an external CLI: the **adversarial reviewer** (after its own independent reviewer authorization) and the separately authorized **headless implementation** (`--invocation-path headless_cli`). Invoke the bounded runner — never a raw provider CLI call:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/orchestration_agent.py" run \
  --routing-file "<absolute-project>/docs/playbook/agent-routing.json" \
  --role "<role>" \
  --host-mode "<claude_hosted|codex_hosted>" \
  --invocation-path "<external_cli|headless_cli>" \
  --governance-authority "<packet value>" \
  --authorization-issuer "<packet value>" \
  --acceptance-owner "<packet value>" \
  --finding-adjudicator "<packet value>" \
  --final-ratifier "<packet value>" \
  --external-authorization "ALLOW_PROVIDER_INVOCATION" \
  --workdir "<absolute-worktree>" \
  --task-file "<absolute-task-packet>" \
  --artifact-dir "<absolute-artifact-directory>" \
  --timeout-seconds "<authorized-timeout>" \
  --model "<explicit-model>" \
  --authoritative-plan-sha "<plan-sha>" \
  --base-sha "<base-sha>" \
  [--target-sha "<target-sha>"] \
  [--allowed-file "<repo-relative-path>"]... \
  [--forbidden-file "<repo-relative-path>"]...
```

The runner fails closed when governance identity, host mode, or invocation path is missing; when the role/path combination is outside the dual-host contract (external feasibility, external default implementation); or when the routing file violates schema v2.

- `${CLAUDE_PLUGIN_ROOT}` resolves inside plugin command content to the plugin's install directory; do not assume the variable exists in an arbitrary shell, do not hunt for the runner via target-project relative paths, do not copy the runner into the target project, and do not install hooks.
- **Session resume:** implementer resume is currently `CAPABILITY_UNAVAILABLE` in the runner (fail closed). Do not claim resume is available and do not pass `--resume-session-id` — it becomes usable only if a future batch implements and separately authorizes it. Reviewer/cross-role resume is always refused.
- **Task-file materialization:** write the packet to an authorized artifact/scratch location — preferably outside the target repository; inside it only if that path is explicitly allowed. The packet content must match the authorization verbatim, contain no secrets, and its path must be recorded in the dispatch report. Creating the packet file is not a target source change. No authorized writable location = stop and ask for one.
- **Artifact directory:** must come from the authorization or the project's convention (e.g. `var/orchestration/<run-id>/` — but never assume `var/` is ignored). Never pick a location that pollutes the source tree.
- **External-side-effect authorization (mechanically enforced):** every real Codex/Claude CLI invocation consumes quota and is an external side effect. The runner itself parses the packet's `External-side-effect authorization` field before any spawn: the packet must carry exactly one unambiguous `ALLOW_PROVIDER_INVOCATION` value AND `--external-authorization` must match it — missing field, `NONE`/`DENY`/unknown value, ambiguity, or packet/flag mismatch = `CONFIGURATION_ERROR` with no child process started (preflight evidence preserved in the artifact bundle). This is per invocation: an implementer authorization never covers a reviewer invocation, and each external review needs its own packet authorization. Without authorization, produce the dispatch order, then stop.

## 6. Separation rules (hard boundaries)

- **One role per invocation.** No automatic role chaining, no automatic reviewer dispatch after implementation, no automatic implementation after feasibility, no automatic fallback to another provider or host, no automatic retry of a semantic failure.
- **Implementer may not dispatch the reviewer.** If the dispatch request originates from implementer output, an implementer session, an implementer task packet, or any automatic workflow continuation, refuse to start `adversarial_reviewer`. Reviewer dispatch requires a fresh, independent authorization from the packet-named authorization issuer.
- **Reviewer may not repair code.** For `adversarial_reviewer`: the profile must be the host mode's read-only reviewer profile (claude_hosted → `codex_read_only`; codex_hosted → `claude_read_only`); grant no write authority; do not turn findings into patches; do not dispatch the implementer or the active host; the output is candidate evidence only — the packet-named finding adjudicator rules on it.
- The executable provider never becomes governance authority, authorization issuer, acceptance owner, finding adjudicator, or final ratifier. Those identities stay exactly where the packet placed them; a higher host tier changes capability and cost only, never authority.

## 7. Result receipt

On completion of an external runner invocation, check and report — without retrying or falling back on a non-`SUCCESS` outcome:

- classified outcome (SUCCESS / STOPPED / MODEL_REPORTED_BLOCKER / TIMEOUT / … as returned);
- governance identity / host mode / execution host / host tier / invocation path as echoed in the result (any provider rewrite of the identity fields = INVALID_OUTPUT);
- provider/profile/model actually invoked; session ID;
- artifact directory path and `verify-manifest` result;
- pre/post Git evidence and the changed-path/allowed-forbidden result;
- final-result validity against the report schema;
- remaining blockers.

For active-host tier dispatches (Task path), review on receipt with the evidence levels: (a) inventory coverage, (b) defect-class closure, (c) adversarial/mutation probes, (d) full regression gate. A green test count alone is not completion; the orchestrator personally reproduces at least one adversarial item and one valid-path item for high-risk work.

**Review-loop control (unchanged):** after an external NO-GO, classify each finding as a new defect family or a missed member of an old one; a missed member reopens the whole family inventory — do not issue another line-item patch. If the same family returns again after fresh-context review, stop and escalate methodology or ownership instead of looping.

Note on capability claims: the runner requests/enforces the configured profile mechanically; real-provider behavior (schema compatibility, network isolation, stream event shapes, real timeout/quota behavior) still requires the separately authorized smoke test.
