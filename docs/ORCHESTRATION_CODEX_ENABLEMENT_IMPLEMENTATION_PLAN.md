# Orchestration Codex Enablement — Authoritative Implementation Plan

- **Plan owner:** ChatGPT control window
- **Repository:** `letitia-chiu/claude-orchestration-plugin`
- **Planning branch:** `plan/orchestration-codex-enablement`
- **Canonical base commit:** `2d531112e25735bd88e85a3d4ebe6cc9339deca9`
- **Proposed implementation branch:** `feat/orchestration-codex-enablement`
- **Plan status:** **PLANNING COMMIT ONLY — NO IMPLEMENTATION AUTHORIZATION**
- **Date:** 2026-07-23

> This document is the authoritative implementation plan for adapting the development orchestration plugin so workflow roles are no longer permanently equated with one provider. It does not authorize creating an implementation branch or worktree, editing files, committing implementation changes, pushing, opening a PR, or merging.

---

## 1. Executive decision

Adopt a **thin role/provider separation** rather than either a name swap or a full provider framework.

The target workflow is:

```text
ChatGPT
= architecture, specification, authoritative plan, authorization,
  acceptance, finding adjudication, and final ratification owner

Codex
= repository-local feasibility verifier
+ primary implementation provider

Claude
= fresh-context, read-only adversarial reviewer
```

The plugin must remain reversible:

- existing Claude `scout`, `worker`, and `executor` agents remain available;
- current Claude implementation support is not deleted;
- a target project chooses providers through a small routing configuration;
- switching the implementer back to a Claude subagent, or the reviewer back to Codex, must not require restructuring commands or playbook documents;
- no generic provider SDK, runtime event layer, capability negotiation framework, or autonomous supervisor is introduced.

This work changes the **development orchestration tool** only. It is not the future Xinghui Runtime Claude/Codex adapter.

---

## 2. Repository evidence and current constraints

At the canonical base commit, the repository is a Claude Code plugin composed primarily of Markdown commands, Markdown subagents, playbook templates, and one audit skill.

Relevant existing surfaces:

```text
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
agents/scout.md
agents/worker.md
agents/executor.md
commands/kickoff.md
commands/go.md
commands/dispatch.md
commands/wrapup.md
commands/init-playbook.md
docs/playbook/README.md
docs/playbook/orchestration.md
docs/playbook/task-routing.md
examples/agents/*
skills/python-runtime-contract-audit/SKILL.md
README*.md
CHANGELOG.md
```

Current facts that the implementation must preserve:

1. `scout` is a read-only Claude subagent.
2. `worker` and `executor` are Claude implementation subagents.
3. `/orchestration:dispatch` currently maps implementation work to Claude subagents and treats an external model primarily as a reviewer.
4. `/orchestration:go` currently relies on the confirmed conversation plan rather than requiring a GitHub planning commit identity.
5. `commands/init-playbook.md` embeds copies of playbook files and has previously drifted from root playbook content.
6. The repository currently has no generic provider registry, session supervisor, timeout manager, transcript bundle, or external-provider runner.
7. The repository currently has no test fixture for Claude/Codex role routing.

The implementation must not pretend those facilities already exist.

---

## 3. Goals

### 3.1 Required goals

1. Separate workflow roles from provider names.
2. Keep ChatGPT as the only architecture, plan, authorization, acceptance, and final-adjudication owner.
3. Make the default generated routing configuration:

   ```text
   feasibility_verifier -> codex_cli / read-only
   implementer          -> codex_cli / workspace-write
   adversarial_reviewer -> claude_cli / fresh read-only
   ```

4. Preserve the existing Claude subagents as a supported fallback provider path.
5. Add fixed task-packet contracts for:
   - Codex feasibility;
   - Codex implementation;
   - Claude adversarial review.
6. Add a narrow, testable external-agent process runner for:
   - CLI invocation;
   - timeout and interrupt classification;
   - stdout/stderr/transcript preservation;
   - pre/post Git evidence;
   - read-only mutation detection;
   - implementation allowed-file validation;
   - structured result validation;
   - provider-separation validation.
7. Ensure commands do not permit the implementer to dispatch the reviewer or the reviewer to modify code.
8. Ensure generated project playbooks receive the same routing rules as the plugin root playbook.
9. Provide a no-quota test fixture using fake `codex` and `claude` executables.
10. Preserve an easy rollback to the previous Claude-implementation workflow.

### 3.2 Success condition

A target project can change provider assignment by editing one generated routing file, while the commands, packets, safety checks, and reporting structure continue to work without role-specific rewrites.

---

## 4. Non-goals and hard exclusions

The following are explicitly outside this work package:

- modifying `letitia-chiu/dream-home`;
- modifying any Xinghui Runtime phase, Gate, production file, test, handoff, or closure record;
- implementing Runtime `AgentPort` or provider adapters;
- normalized Claude/Codex runtime events;
- provider capability negotiation;
- cross-provider Runtime session migration;
- autonomous agent loops;
- production provider hot swap;
- a network service, daemon, dashboard, queue, or transcript database;
- generic support for arbitrary providers;
- changing Claude model pins in `agents/*.md`;
- deleting or weakening `scout`, `worker`, or `executor`;
- automatic commit, push, PR creation, merge, or branch deletion;
- automatic review dispatch after implementation;
- bypassing permissions through `--yolo`, `--dangerously-skip-permissions`, or an equivalent flag;
- installing hooks into target projects;
- using a real Codex or Claude account in automated tests;
- changing licensing.

Any need to enter one of these areas is a stop condition and requires a new ChatGPT planning commit.

---

## 5. Target architecture

### 5.1 Authority layer

The following ownership is immutable in the generated default routing contract:

```text
architecture_owner        = chatgpt
authoritative_plan_owner  = chatgpt
authorization_owner       = chatgpt
acceptance_owner          = chatgpt
final_adjudicator         = chatgpt
```

The external-agent runner must not accept any of those as executable roles.

### 5.2 Executable workflow roles

The supported executable roles are:

```text
feasibility_verifier
implementer
adversarial_reviewer
```

Each role owns a behavior contract independent of the selected provider.

#### `feasibility_verifier`

- read-only;
- new session;
- checks repository-local feasibility against an authoritative plan commit;
- may inspect and run explicitly permitted non-mutating checks;
- may not create a branch/worktree, edit, commit, push, dispatch another provider, or begin implementation;
- output verdict is one of:
  - `PASS_FOR_IMPLEMENTATION_AUTHORIZATION`;
  - `PLAN_CHANGE_REQUIRED`;
  - `EVIDENCE_INSUFFICIENT`.

#### `implementer`

- starts only after a separate ChatGPT authorization;
- works in the exact authorized worktree;
- may modify only allowed files;
- must stop on a forbidden-file dependency or specification contradiction;
- may run required tests;
- may not dispatch the reviewer;
- may not push, open a PR, merge, or continue to an unapproved batch;
- does not become plan or acceptance owner.

#### `adversarial_reviewer`

- fresh session, never an implementation-session resume;
- read-only;
- receives the authoritative plan, base/target SHA, complete delta, exclusions, and evidence packet;
- may produce candidate findings, observations, suggestions, and evidence gaps;
- may not modify the repository, repair code, dispatch the implementer, or ratify findings;
- only ChatGPT may classify a candidate finding as established.

### 5.3 Provider kinds

Only these provider invocation kinds are in scope:

```text
claude_subagent
codex_cli
claude_cli
```

- `claude_subagent` uses the existing Claude Code `Task` path and existing plugin agents.
- `codex_cli` and `claude_cli` use the bounded external-agent runner.
- adding another provider kind requires another work package.

### 5.4 Default routing file

Add a generated project-local machine-readable file:

```text
docs/playbook/agent-routing.json
```

Default content shape:

```json
{
  "schema_version": 1,
  "authority": {
    "architecture_owner": "chatgpt",
    "authoritative_plan_owner": "chatgpt",
    "authorization_owner": "chatgpt",
    "acceptance_owner": "chatgpt",
    "final_adjudicator": "chatgpt"
  },
  "roles": {
    "feasibility_verifier": {
      "provider": "codex_cli",
      "profile": "codex_read_only"
    },
    "implementer": {
      "provider": "codex_cli",
      "profile": "codex_workspace_write"
    },
    "adversarial_reviewer": {
      "provider": "claude_cli",
      "profile": "claude_read_only"
    }
  },
  "constraints": {
    "require_distinct_implementer_and_reviewer_provider": true,
    "implementer_may_dispatch_reviewer": false,
    "reviewer_may_modify_repository": false,
    "external_git_writes_require_separate_authorization": true
  }
}
```

Validation must fail closed when:

- authority ownership differs from the fixed ChatGPT values;
- an unknown role/provider/profile is present;
- implementer and reviewer resolve to the same provider while the separation constraint is enabled;
- a read-only role maps to a write-capable profile;
- a profile requires a CLI capability not available in the installed version.

### 5.5 Reversibility requirement

The following future change must require configuration and packet changes only, not command restructuring:

```json
"implementer": {
  "provider": "claude_subagent",
  "profile": "executor"
}
```

The existing `worker` and `executor` agents therefore remain intact.

---

## 6. Local feasibility gate before implementation

Claude must perform this section read-only from the local `main` checkout before any implementation authorization.

### 6.1 Repository checks

Report:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin
git rev-parse origin/main
git rev-parse origin/plan/orchestration-codex-enablement
```

Required state:

- current branch is `main`;
- local working tree has no unapproved tracked changes;
- `origin/main` is the canonical base or any advancement is explicitly reported;
- the plan file is readable from the planning branch without switching branches.

### 6.2 CLI capability checks

Capture the actual local outputs of:

```bash
codex --version
codex exec --help
codex exec resume --help
claude --version
claude --help
python3 --version
```

Confirm, using local help rather than memory, the exact supported flags for:

- non-interactive execution;
- working-directory selection;
- read-only and workspace-write sandboxing;
- approval policy;
- JSONL/streaming output;
- final output schema;
- session identity/resume;
- Claude plan/read-only mode;
- Claude tool allow/deny controls;
- disabling write tools, Bash, Task/subagent dispatch, MCP, and slash commands if supported;
- session persistence controls if supported.

### 6.3 Plugin-root helper resolution

Before implementing a helper invocation inside command Markdown, confirm from the locally installed Claude Code/plugin behavior whether `${CLAUDE_PLUGIN_ROOT}` is available and stable for plugin-bundled scripts.

A minimal harmless probe may be performed without writing repository files. If plugin-root script resolution cannot be verified, stop with `PLAN_CHANGE_REQUIRED`; do not invent a path convention.

### 6.4 Feasibility verdict

Return exactly one:

```text
PASS_FOR_IMPLEMENTATION_AUTHORIZATION
PLAN_CHANGE_REQUIRED
EVIDENCE_INSUFFICIENT
```

No implementation branch, worktree, or file modification is permitted during this gate.

---

## 7. Planned file changes

### 7.1 Existing files to modify

| File | Required change |
|---|---|
| `commands/kickoff.md` | Plan dispatches by workflow role first; provider comes from target `agent-routing.json`. Kickoff still stops before execution. |
| `commands/go.md` | Require authoritative planning branch, plan commit SHA, canonical base SHA, role map, allowed/forbidden files, tests, stop conditions, and explicit Git authorization. Conversation text alone cannot replace the plan commit. |
| `commands/dispatch.md` | Resolve role then provider. Route `claude_subagent` through Task; route CLI providers through the bounded runner. External provider is no longer synonymous with reviewer. Reject implementer-triggered reviewer dispatch. |
| `commands/wrapup.md` | Require provider identity, session separation, transcript manifest, timeout/exit classification, Git evidence, allowlist result, and ChatGPT adjudication status. |
| `commands/init-playbook.md` | Generate the updated role-first playbook plus `agent-routing.json`. Synchronize embedded templates exactly. Never overwrite existing project files. |
| `docs/playbook/README.md` | Add the routing file and provider packet map to the file map. |
| `docs/playbook/orchestration.md` | Replace provider-fixed workflow claims with role-first contracts; preserve existing invariant-owner, defect-class, evidence, and review-loop rules. |
| `docs/playbook/task-routing.md` | Define supported provider kinds, profiles, role map, packet requirements, session separation, and invocation safety. |
| `.claude-plugin/plugin.json` | Update description/keywords and bump version only in the final documentation batch after all tests pass. |
| `.claude-plugin/marketplace.json` | Update description to mention role/provider routing without claiming arbitrary-provider support. |
| `README.md` | Document role-first routing, current default assignment, fallback Claude subagents, and safety boundaries. |
| `README.zh-TW.md` | Keep semantically synchronized with English README. |
| `README.zh-CN.md` | Keep semantically synchronized with English README. |
| `README.ja.md` | Keep semantically synchronized with English README. |
| `CHANGELOG.md` | Add the release entry only after implementation and tests are complete. |

### 7.2 New files to add

```text
docs/playbook/agent-routing.json
examples/task-packets/codex-feasibility.md
examples/task-packets/codex-implementation.md
examples/task-packets/claude-adversarial-review.md
examples/schemas/orchestration-result.schema.json
scripts/orchestration_agent.py
tests/test_orchestration_agent.py
tests/test_playbook_template_sync.py
tests/fixtures/orchestration-agent/repo/*
tests/fixtures/orchestration-agent/bin/codex
tests/fixtures/orchestration-agent/bin/claude
```

The exact fixture layout may be adjusted during feasibility if needed, but the behavior coverage in §11 may not be reduced.

### 7.3 Files forbidden from modification

```text
agents/scout.md
agents/worker.md
agents/executor.md
examples/agents/*
skills/python-runtime-contract-audit/SKILL.md
LICENSE
.gitignore
```

If implementation requires changing one of these, stop and request a plan amendment.

---

## 8. External-agent runner contract

### 8.1 Purpose

`scripts/orchestration_agent.py` is a narrow process-safety wrapper, not an orchestrator or agent framework.

It may:

- validate routing configuration;
- validate role/provider/profile compatibility;
- start one external CLI process;
- impose a wall-clock timeout;
- forward an interrupt to the child process group and escalate termination if needed;
- capture stdout and stderr separately;
- preserve streaming JSON/JSONL unchanged;
- capture the final structured result;
- record CLI version and invocation metadata;
- record pre/post Git evidence;
- verify no repository mutation for read-only roles;
- validate implementation changed paths against allowlist and forbidden paths;
- generate a SHA-256 artifact manifest;
- return a machine-readable outcome.

It may not:

- write or revise an authoritative plan;
- decide architecture;
- issue implementation authorization;
- chain roles automatically;
- resume a different provider automatically;
- commit, push, create a PR, merge, or delete a branch/worktree;
- decide whether a reviewer finding is established;
- silently downgrade sandbox or tool restrictions;
- retry semantic failures;
- use dangerous permission bypass flags.

### 8.2 Proposed command shape

Exact flags may change only to match locally verified CLI help; semantic requirements may not change.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/orchestration_agent.py" run \
  --routing-file <project>/docs/playbook/agent-routing.json \
  --role <feasibility_verifier|implementer|adversarial_reviewer> \
  --workdir <absolute-worktree> \
  --task-file <absolute-task-file> \
  --artifact-dir <absolute-artifact-dir> \
  --timeout-seconds <positive-integer> \
  --model <explicit-model> \
  [--authoritative-plan-sha <sha>] \
  [--base-sha <sha>] \
  [--target-sha <sha>] \
  [--allowed-file <repo-relative-path>]... \
  [--forbidden-file <repo-relative-path>]...
```

### 8.3 Required artifact bundle

Each run must save:

```text
task.md
routing.json
invocation.json
stdout.jsonl or stdout.log
stderr.log
final-result.json
pre-git.json
post-git.json
changed-paths.json
tests/                 # when supplied by the controller
manifest.sha256
```

`invocation.json` must include:

- role;
- provider/profile;
- explicit model;
- executable and CLI version;
- working directory;
- plan/base/target SHA when applicable;
- sandbox and approval mode;
- allowed/forbidden paths;
- start/end time and duration;
- timeout;
- child exit code or signal;
- session ID when present;
- final classified outcome.

### 8.4 Outcome classes

At minimum:

```text
SUCCESS
STOPPED
MODEL_REPORTED_BLOCKER
PROCESS_NONZERO
TIMEOUT
INTERRUPTED
INVALID_OUTPUT
READ_ONLY_MUTATION
FORBIDDEN_PATH_CHANGED
TEST_FAILURE
TRANSCRIPT_INCOMPLETE
CONFIGURATION_ERROR
CAPABILITY_UNAVAILABLE
```

Timeout, model finding, invalid output, and test failure must never collapse into the same result.

### 8.5 Git controls

For read-only roles:

- record HEAD, index, tracked diff, and untracked paths before execution;
- compare them after execution;
- any delta yields `READ_ONLY_MUTATION`;
- do not clean or revert automatically, because that could destroy pre-existing user work.

For implementation:

- compare changed paths to the allowed set;
- a forbidden or unlisted path yields `FORBIDDEN_PATH_CHANGED`;
- do not stage, commit, clean, reset, or revert automatically;
- the controller reports the evidence to ChatGPT for the next authorization.

### 8.6 Session controls

- feasibility and implementation must never share a session ID;
- adversarial review must always be a fresh session;
- the runner may permit implementation resume only when the caller supplies the recorded implementation session ID and the same role/provider/worktree identity;
- the runner must reject reviewer resume and cross-role resume;
- session resume is never automatic.

---

## 9. Provider profile requirements

### 9.1 `codex_read_only`

Required semantics:

- non-interactive `codex exec`;
- exact working directory;
- read-only sandbox;
- approval policy that cannot authorize a write during unattended execution;
- structured streaming output;
- explicit model;
- no dangerous bypass flags;
- no branch/worktree creation, commit, push, PR, merge, or reviewer dispatch in the task packet;
- repository mutation detected independently by the runner.

### 9.2 `codex_workspace_write`

Required semantics:

- non-interactive `codex exec`;
- exact authorized worktree;
- workspace-write sandbox, never danger-full-access;
- explicit model;
- structured streaming output;
- network disabled unless a separate ChatGPT authorization explicitly enables it;
- prompt-level allowed/forbidden paths plus independent post-run path validation;
- no automatic commit/push/PR/merge;
- batch stop conditions represented in the result schema.

### 9.3 `claude_read_only`

Required semantics:

- fresh non-interactive `claude -p` session;
- plan/read-only permission mode;
- only read/search tools;
- Bash, Edit, Write, Notebook edit, Task/subagent dispatch, MCP tools, and other mutation paths denied;
- slash commands/skills disabled when the installed CLI supports a mechanical flag;
- structured streaming output and final schema validation;
- explicit model;
- no session resume or continuation;
- repository mutation independently detected by the runner.

If the locally installed Claude Code cannot mechanically deny all write and dispatch paths, feasibility must return `PLAN_CHANGE_REQUIRED` rather than relying only on prompt wording.

### 9.4 `claude_subagent`

This path preserves the existing plugin agents.

- `scout` remains read-only reconnaissance;
- `worker` remains a general Claude implementation fallback;
- `executor` remains a hard Claude implementation fallback;
- Task dispatch remains subject to the target project’s routing map and ChatGPT authorization;
- no changes to the agent files are authorized in this work package.

---

## 10. Task-packet contracts

### 10.1 Common header

Every packet must contain:

```text
Role
Provider/profile
Explicit model
Repository/worktree
Authoritative plan branch
Authoritative plan commit SHA
Canonical base SHA
Target SHA or batch base SHA
Goal
Allowed files
Forbidden files
Required evidence
Stop conditions
Git authorization
External-side-effect authorization
Report schema
```

### 10.2 Codex feasibility packet

Must state:

- read-only only;
- no branch/worktree creation;
- no file changes;
- no implementation suggestions presented as an implementation result;
- identify repository facts contradicting the plan;
- return one of the three feasibility verdicts;
- include exact file/symbol/command evidence;
- stop rather than invent missing specifications.

### 10.3 Codex implementation packet

Must state:

- this batch is the only authorized batch;
- exact allowed and forbidden paths;
- exact tests and expected outputs;
- no unapproved abstraction or adjacent cleanup;
- stop on plan/repository contradiction;
- stop if a forbidden file is required;
- do not dispatch Claude;
- do not commit, push, create PR, or merge unless the packet carries a separate explicit Git authorization;
- report changed files, test results, HEAD, status, remaining deviations, and session ID.

### 10.4 Claude adversarial-review packet

Must state:

- fresh context;
- review-only;
- no code repair;
- authoritative plan and candidate SHA are inputs, not suggestions to rewrite;
- findings need violated requirement, concrete evidence, impact, and minimal remediation scope;
- style preferences and optional improvements belong in `suggestions`, not `findings`;
- closed Gates and explicit exclusions may not be reopened;
- ChatGPT adjudicates all findings.

---

## 11. Result schema

`examples/schemas/orchestration-result.schema.json` must support role-specific results while preserving a common envelope.

Required common fields:

```text
schema_version
role
provider
profile
model
verdict
summary
evidence
stop_reason
session_id
changed_files
tests
repository_state
```

Reviewer result must separate:

```text
findings[]
observations[]
suggestions[]
evidence_gaps[]
```

Each reviewer finding requires:

```text
id
severity                # Blocker | Major | Minor
violated_requirement
location
repository_evidence
impact
minimal_remediation_scope
```

A missing requirement or evidence must make the item invalid as a finding; it may be returned only as an observation or evidence gap.

---

## 12. Implementation batches

Implementation starts only after ChatGPT issues a separate authorization containing the final plan commit SHA, base SHA, implementation branch/worktree, and batch permission.

### Batch 1 — Role and routing contracts

**Goal:** establish role-first semantics and the generated routing file without invoking external CLIs.

**Allowed files:**

```text
docs/playbook/README.md
docs/playbook/orchestration.md
docs/playbook/task-routing.md
docs/playbook/agent-routing.json
examples/task-packets/*
examples/schemas/orchestration-result.schema.json
```

**Forbidden:** all other files.

**Acceptance:**

- valid JSON routing file;
- all authority owners fixed to ChatGPT;
- implementer/reviewer provider-separation constraint present;
- task packets contain every common header field;
- no claim of arbitrary-provider support;
- existing invariant-owner and defect-class rules preserved.

**Commit boundary:**

```text
docs: define role-provider orchestration contracts
```

### Batch 2 — Bounded external-agent runner

**Goal:** add the process-safety wrapper and fake CLI fixtures.

**Allowed files:**

```text
scripts/orchestration_agent.py
tests/test_orchestration_agent.py
tests/fixtures/orchestration-agent/**
```

**Forbidden:** commands, playbook, agent definitions, README, manifests.

**Acceptance:**

- standard-library Python only;
- fake CLIs only in automated tests;
- timeout kills the child process group and preserves partial logs;
- read-only mutation is detected without cleanup;
- forbidden path mutation is detected without cleanup;
- stdout/stderr remain separate;
- manifest verifies all saved artifacts;
- same-provider implementer/reviewer routing fails closed;
- reviewer/cross-role resume fails closed;
- no staging, commit, push, PR, merge, reset, or clean operation exists in runner code.

**Commit boundary:**

```text
feat: add bounded external agent runner
```

### Batch 3 — Command routing integration

**Goal:** make plugin commands resolve role first and invoke either Claude Task agents or the external runner.

**Allowed files:**

```text
commands/kickoff.md
commands/go.md
commands/dispatch.md
commands/wrapup.md
```

**Forbidden:** runner implementation, agents, playbook templates.

**Acceptance:**

- kickoff stops at plan;
- go requires planning commit identity and explicit authorization;
- dispatch reads target `agent-routing.json`;
- implementation no longer automatically means Claude worker/executor;
- external model no longer automatically means reviewer;
- implementer cannot dispatch reviewer;
- reviewer cannot repair code;
- unknown or unsafe routing stops before dispatch;
- commands use `${CLAUDE_PLUGIN_ROOT}` only if feasibility verified it.

**Commit boundary:**

```text
feat: route orchestration commands by workflow role
```

### Batch 4 — Init template and drift protection

**Goal:** generate the new routing/playbook files and prevent embedded-template drift.

**Allowed files:**

```text
commands/init-playbook.md
tests/test_playbook_template_sync.py
```

**Forbidden:** root playbook content except to correct a proven sync mismatch through a plan amendment.

**Acceptance:**

- init-playbook file count and report are correct;
- existing target files remain skip/no-overwrite;
- embedded `README.md`, `orchestration.md`, `task-routing.md`, and `agent-routing.json` match root sources byte-for-byte after extraction;
- test fails when any embedded copy drifts.

**Commit boundary:**

```text
test: protect generated orchestration templates from drift
```

### Batch 5 — Documentation and release metadata

**Goal:** publish the new workflow accurately after behavior and tests are stable.

**Allowed files:**

```text
README.md
README.zh-TW.md
README.zh-CN.md
README.ja.md
CHANGELOG.md
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
```

**Forbidden:** code, commands, task packets, tests, agents.

**Acceptance:**

- four READMEs are semantically aligned;
- current default role map is documented;
- Claude subagent fallback remains documented;
- no claim that the plugin supports arbitrary providers;
- no claim that prompt wording alone creates a file allowlist;
- version bump is consistent in metadata and changelog;
- release entry distinguishes plugin enablement from Xinghui Runtime adapters.

**Commit boundary:**

```text
docs: publish role-provider orchestration workflow
```

### Batch 6 — Full validation and smoke-test preparation

**Goal:** prove the branch is ready for an opt-in real-CLI smoke test.

**Allowed files:** test-only fixes inside already authorized files. Any production change requires returning to the relevant earlier batch and a new authorization.

**Acceptance commands:**

```bash
python3 -m unittest discover -s tests -v
git diff --check
git status --short
```

Also run static searches proving:

- dangerous bypass flags do not exist;
- runner code contains no Git write command;
- agent files are unchanged from the canonical base;
- role/provider mapping is not duplicated inconsistently;
- init-playbook embedded templates are synchronized.

No commit is required if no files change.

---

## 13. Automated test matrix

Automated tests must use fixture repositories and fake executables; they must not consume a real account quota.

| Test | Required result |
|---|---|
| Valid default route map | loads successfully |
| Authority owner changed from ChatGPT | `CONFIGURATION_ERROR` |
| Implementer and reviewer same provider | `CONFIGURATION_ERROR` |
| Unknown provider/profile | `CONFIGURATION_ERROR` |
| Codex read-only happy path | `SUCCESS`, no Git delta |
| Read-only fake CLI writes a file | `READ_ONLY_MUTATION` |
| Implementation changes only allowed files | `SUCCESS` |
| Implementation changes forbidden/unlisted file | `FORBIDDEN_PATH_CHANGED` |
| Child exits non-zero | `PROCESS_NONZERO` with stderr retained |
| Child exceeds timeout | `TIMEOUT`, process group terminated, partial transcript retained |
| Interrupt | `INTERRUPTED` |
| Invalid/missing final JSON | `INVALID_OUTPUT` |
| Missing transcript artifact | `TRANSCRIPT_INCOMPLETE` |
| Reviewer resume requested | `CONFIGURATION_ERROR` |
| Cross-role resume requested | `CONFIGURATION_ERROR` |
| Manifest altered after generation | verification fails |
| Runner source contains Git write command | static test fails |
| Embedded playbook differs from root | sync test fails |

The fixture must include at least one permanently forbidden file and one closed-Gate analogue to prove the workflow does not reopen or rewrite excluded work.

---

## 14. Opt-in real-CLI smoke test

A real-CLI smoke test is mandatory before using the workflow on a production Gate, but it is **not** part of automated tests and requires explicit user authorization because it consumes provider quota.

Use a disposable fixture repository, never `dream-home` and never this plugin’s main worktree.

Required sequence:

```text
1. Codex feasibility — fresh, read-only, zero repository delta
2. Codex implementation — fresh implementation session, allowed files only
3. Controller validation — tests, changed paths, transcript manifest
4. Claude adversarial review — fresh, read-only, zero repository delta
5. ChatGPT adjudication — one real defect and one suggestion correctly separated
```

Additional negative probes:

- task attempts to induce a forbidden-file edit;
- task asks the implementer to push;
- task asks the implementer to dispatch the reviewer;
- reviewer packet asks Claude to repair the defect;
- reviewer packet contains a closed-Gate lure;
- timeout is intentionally triggered using a harmless long-running fixture command.

The smoke-test report must include exact CLI versions, model IDs, profiles, artifact paths, exit classifications, pre/post Git evidence, and quota sentinel result when the target project requires one.

---

## 15. Stop conditions

Implementation must stop and return to ChatGPT when any of the following occurs:

1. local `origin/main` differs from the plan base in a way that changes relevant commands, agents, playbook, or plugin layout;
2. the planning branch or plan commit cannot be verified;
3. `${CLAUDE_PLUGIN_ROOT}` cannot be verified for bundled helper execution;
4. current Codex CLI cannot provide required read-only/workspace-write semantics;
5. current Claude CLI cannot mechanically deny repository mutation and Task dispatch for reviewer mode;
6. implementation requires editing `agents/*.md` or another forbidden file;
7. implementation requires a daemon, service, database, hook installation, or target-project modification;
8. safe CLI flags differ materially enough that the plan’s profile semantics cannot be met;
9. a test would require a real account or external network;
10. an implementation batch requires an unlisted file;
11. the routing abstraction begins to resemble Runtime provider adapters or capability negotiation;
12. any step would automatically commit, push, open a PR, or merge;
13. a closed Xinghui Gate or `dream-home` file is pulled into scope;
14. the implementer attempts to self-authorize the reviewer or next batch.

Do not guess or silently weaken acceptance criteria.

---

## 16. Git and authorization rules

### 16.1 Before implementation authorization

Allowed:

- `git fetch`;
- read files from `origin/plan/orchestration-codex-enablement`;
- inspect code and history;
- run non-mutating checks;
- report feasibility.

Forbidden:

- create implementation branch/worktree;
- edit files;
- commit;
- push;
- open PR;
- merge.

### 16.2 After implementation authorization

The authorization must explicitly include:

```text
plan branch
plan commit SHA
canonical base SHA
implementation branch
worktree path
current batch
allowed files
forbidden files
acceptance commands
stop conditions
commit permission
push/PR/merge permission
```

An authorization for one batch does not authorize the next batch.

### 16.3 Commit discipline

- one batch, one intent, one commit;
- no rebase or force push;
- no squash that destroys planning ancestry when ancestry is an acceptance artifact;
- before each commit: tests, `git diff --check`, staged-file review, and forbidden-path check;
- every report includes new commit SHA, branch HEAD, remote state when applicable, and `git status --short`.

---

## 17. Required reports

### 17.1 Feasibility report

```text
Verdict
Local branch / HEAD / status
origin/main SHA
Planning branch / plan commit SHA
Plan file read evidence
Relevant repository inventory
Codex version and confirmed capabilities
Claude version and confirmed capabilities
Plugin-root helper resolution result
Blockers or plan contradictions
No-write proof
```

### 17.2 Per-batch implementation report

```text
Batch and conclusion
Plan SHA / batch base SHA / resulting HEAD
Files changed
Invariant owner
Defect-class inventory when applicable
Commands and actual outputs
Adversarial and valid-path evidence
Allowed/forbidden path result
Remaining deviations or blockers
Session and transcript artifact identity
Git status
Whether next batch is authorized: NO unless ChatGPT says otherwise
```

### 17.3 Final implementation candidate report

```text
Candidate SHA and complete commit range
All batch commits
Full test fingerprint
Static safety searches
Fixture test matrix
Real-CLI smoke-test status
Known limitations
Rollback procedure
No push/PR/merge assertion unless separately authorized
```

---

## 18. Acceptance criteria for final ratification

ChatGPT may ratify the implementation candidate only when all of the following are true:

1. default routing maps Codex to feasibility and implementation, Claude to adversarial review;
2. ChatGPT authority roles are fixed and validated;
3. changing implementation back to `claude_subagent` requires only routing configuration and an authorized task packet;
4. existing Claude agents are byte-identical to the canonical base;
5. Codex feasibility is mechanically read-only and detects any mutation;
6. Codex implementation is constrained to an authorized worktree and post-validated allowed paths;
7. Claude review is fresh-context and mechanically denied write/dispatch tools;
8. implementer and reviewer provider equality fails closed by default;
9. implementer cannot automatically dispatch reviewer;
10. reviewer cannot repair code;
11. timeout, interrupt, process failure, invalid output, test failure, and model blocker are distinct;
12. complete transcript and manifest artifacts are retained;
13. runner performs no Git write operation;
14. generated templates match root playbook sources;
15. fake-CLI tests pass without network or quota;
16. opt-in real-CLI smoke test passes in a disposable fixture before production-Gate use;
17. no `dream-home` or Runtime file was modified;
18. no push, PR, or merge occurred without a separate authorization.

---

## 19. Rollback

Rollback must remain simple:

1. disable the external CLI mappings in target `agent-routing.json`;
2. map implementation back to `claude_subagent` with `worker` or `executor`;
3. map review back to `codex_cli` read-only if desired;
4. preserve all transcripts and routing history;
5. do not delete existing Claude agents;
6. if the release itself must be reverted, revert the enablement commits without rewriting history.

No Runtime or target-project migration is part of rollback.

---

## 20. Deferred hardening

Do not add these during this work package:

- OS-level per-file sandbox profiles;
- signed task packets;
- centralized transcript index;
- provider discovery or dynamic capability negotiation;
- arbitrary-provider plugin API;
- automatic provider fallback;
- cross-provider session conversion;
- remote execution;
- concurrency scheduler;
- UI/dashboard;
- GitHub Actions integration;
- automatic PR review publishing;
- usage/cost dashboard beyond existing project-local quota checks.

Each requires separate evidence and authorization.

---

## 21. Official references to revalidate during feasibility

Use current official documentation and local CLI help as the source of truth:

- Anthropic Claude Code CLI reference: `https://docs.anthropic.com/en/docs/claude-code/cli-reference`
- Anthropic Claude Code permissions/settings documentation: `https://docs.anthropic.com/en/docs/claude-code/settings`
- Anthropic Claude Code plugin documentation: `https://docs.anthropic.com/en/docs/claude-code/plugins`
- OpenAI Codex CLI reference: `https://developers.openai.com/codex/cli/reference`

If documentation and local help conflict, report the exact difference. Do not silently assume one behavior.

---

## 22. Immediate next action

From the local plugin repository `main` checkout, start a fresh Claude Code session and perform only the read-only feasibility gate in §6.

The next ChatGPT control-window action after receiving that report is one of:

```text
AUTHORIZE IMPLEMENTATION BATCH 1
AMEND THE AUTHORITATIVE PLAN
STOP — EVIDENCE INSUFFICIENT
```
