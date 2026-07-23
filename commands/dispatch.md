---
description: Turn a task into a dispatch order and route it by workflow role (role → agent-routing.json → provider/profile)
argument-hint: the task to dispatch
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Task to dispatch: $ARGUMENTS

Read the **target project's** `docs/playbook/orchestration.md`, `docs/playbook/task-routing.md`, and `docs/playbook/agent-routing.json`; if any is missing, prompt the user to run `/orchestration:init-playbook` first. Dispatch is role-first: decide **what** the work is (workflow role), then let the routing file decide **which engine** executes it (provider/profile). Implementation is not permanently equated with worker/executor, and an external model is not permanently equated with the reviewer.

## 1. Classify the workflow role first

Decide which of these the task is — or that it is orchestrator-owned judgment (tone, precision micro-edits, ten-minute tasks) that should not be dispatched at all:

- **local read-only reconnaissance** — current-state/file/surface inventory;
- **`feasibility_verifier`** — repository-local feasibility check against an authoritative plan commit; read-only, fresh session, three verdicts only;
- **`implementer`** — one explicitly authorized implementation batch with exact allowed/forbidden paths;
- **`adversarial_reviewer`** — fresh-context, read-only review of a frozen candidate; findings are candidates until adjudicated.

Preserve the existing methodology while classifying — none of it is displaced by role routing:

1. **Generalize bug and review findings before writing the order.** A finding is evidence of a defect class, not merely a line to patch. State: observed instance → general defect class → authorized same-class search scope → expected proof of class closure. If the defect concerns Python runtime contracts, dataclasses, Protocols, callbacks, truthiness, enums, tuples, mappings, or frozen models, invoke the `python-runtime-contract-audit` skill and include its inventory and boundary-test requirements.
2. **Assign one invariant owner.** Production changes, shared validators, contract inventory, and boundary tests for the same invariant or defect family must stay with one executing agent/context. Do not split them across parallel executors. Parallelize only genuinely independent units with no shared invariant or contract surface.
3. **Do not dispatch an ambiguous class-closure task.** If you cannot name the defect family or authorized search scope, inspect the code or ask the user first.

## 2. Validate the task packet

Every dispatch needs a complete task packet (templates: `examples/task-packets/` in this plugin). All 16 common fields are required — a missing field stops the dispatch; never guess a value in:

```text
Role / Provider/profile / Explicit model / Repository/worktree /
Authoritative plan branch / Authoritative plan commit SHA / Canonical base SHA /
Target SHA or batch base SHA / Goal / Allowed files / Forbidden files /
Required evidence / Stop conditions / Git authorization /
External-side-effect authorization / Report schema
```

The internal dispatch-order sections remain mandatory inside the packet body: 【Goal】【Scope】【No-go zones】【Invariant owner】【Defect-class closure】【Spec】【Acceptance】【Report format】. "Invariant owner" and "Defect-class closure" may be `not applicable` only when stated explicitly.

## 3. Resolve the provider from the routing file

Read `<target-project>/docs/playbook/agent-routing.json`, resolve the role to provider/profile, and check it matches the packet's `Provider/profile` field. Mismatch, unknown role/provider/profile, an authority owner not fixed to the ChatGPT/user control window, or a read-only role mapped to a write-capable profile = stop before any spawn.

## 4. `claude_subagent` path (Task tool)

Only when the routing file resolves the role's provider to `claude_subagent` may you dispatch via the Claude Code Task tool, selecting the existing agent by profile (`scout`, `worker`, `executor`). Requirements:

- pass the full task packet as the prompt;
- keep the invariant owner intact — one owner per invariant, never split;
- worker/executor are the routing-selected engine for this dispatch, not the permanent implementer;
- the subagent must not dispatch a next role, and receives no Git or external-side-effect authority beyond what the packet lists;
- never modify the agent definitions.

## 5. External CLI path (bounded runner)

When the provider is `codex_cli` or `claude_cli`, invoke the Batch-2 bounded runner — never a raw provider CLI call:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/orchestration_agent.py" run \
  --routing-file "<absolute-project>/docs/playbook/agent-routing.json" \
  --role "<role>" \
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

- `${CLAUDE_PLUGIN_ROOT}` resolves inside plugin command content to the plugin's install directory; do not assume the variable exists in an arbitrary shell, do not hunt for the runner via target-project relative paths, do not copy the runner into the target project, and do not install hooks.
- **Session resume:** implementer resume is currently `CAPABILITY_UNAVAILABLE` in the runner (fail closed). Do not claim resume is available and do not pass `--resume-session-id` — it becomes usable only if a future batch implements and separately authorizes it. Reviewer/cross-role resume is always refused.
- **Task-file materialization:** write the packet to an authorized artifact/scratch location — preferably outside the target repository; inside it only if that path is explicitly allowed. The packet content must match the authorization verbatim, contain no secrets, and its path must be recorded in the dispatch report. Creating the packet file is not a target source change. No authorized writable location = stop and ask for one.
- **Artifact directory:** must come from the authorization or the project's convention (e.g. `var/orchestration/<run-id>/` — but never assume `var/` is ignored). Never pick a location that pollutes the source tree.
- **External-side-effect authorization:** every real Codex/Claude CLI invocation consumes quota and is an external side effect. Spawn only when the packet carries `External-side-effect authorization: ALLOW_PROVIDER_INVOCATION`. Without it, produce the dispatch order, then stop — do not spawn the provider.

## 6. Separation rules (hard boundaries)

- **One role per invocation.** No automatic role chaining, no automatic reviewer dispatch after implementation, no automatic implementation after feasibility, no automatic fallback to another provider, no automatic retry of a semantic failure.
- **Implementer may not dispatch the reviewer.** If the dispatch request originates from implementer output, an implementer session, an implementer task packet, or any automatic workflow continuation, refuse to start `adversarial_reviewer`. Reviewer dispatch requires a fresh authorization from the ChatGPT/user control window.
- **Reviewer may not repair code.** For `adversarial_reviewer`: profile must be `claude_read_only`; grant no write authority; do not turn findings into patches; do not dispatch the implementer; the output is candidate evidence only — the control window adjudicates.
- The executable provider never becomes architecture owner, plan owner, authorization owner, acceptance owner, or final adjudicator. Those stay with the ChatGPT/user control workflow.

## 7. Result receipt

On completion of an external runner invocation, check and report — without retrying or falling back on a non-`SUCCESS` outcome:

- classified outcome (SUCCESS / STOPPED / MODEL_REPORTED_BLOCKER / TIMEOUT / … as returned);
- provider/profile/model actually invoked; session ID;
- artifact directory path and `verify-manifest` result;
- pre/post Git evidence and the changed-path/allowed-forbidden result;
- final-result validity against the report schema;
- remaining blockers.

For `claude_subagent` dispatches, review on receipt with the evidence levels: (a) inventory coverage, (b) defect-class closure, (c) adversarial/mutation probes, (d) full regression gate. A green test count alone is not completion; the orchestrator personally reproduces at least one adversarial item and one valid-path item for high-risk work.

**Review-loop control (unchanged):** after an external NO-GO, classify each finding as a new defect family or a missed member of an old one; a missed member reopens the whole family inventory — do not issue another line-item patch. If the same family returns again after fresh-context review, stop and escalate methodology or ownership instead of looping.

Note on capability claims: the runner requests/enforces the configured profile mechanically; real-provider behavior (schema compatibility, network isolation, stream event shapes, real timeout/quota behavior) still requires the separately authorized smoke test.
