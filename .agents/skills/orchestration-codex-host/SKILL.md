---
name: orchestration-codex-host
description: Formal Codex Desktop entry for governance-bound kickoff, authorization, host-local scout/native implementation dispatch, and evidence-separated wrap-up.
---

# Codex-host orchestration

Use this skill only when the task packet explicitly selects
`host_mode = codex_hosted` and `active_host = codex_desktop`.

This skill preserves four separate identities:

```text
governance authority
!= active execution host
!= host-local execution tier
!= external reviewer
```

## Execution-phase boundary

There are two non-interchangeable modes:

- **Controller mode** builds and validates the complete packet. In this mode,
  read and follow every reference below in order.
- **Runner-dispatched provider mode** is active only when the provider prompt
  says `Provider execution phase: substantive_only`. The controller has already
  completed kickoff/go identity, authorization, routing, model/effort, and Git
  preflight. In this mode, do not execute the controller references, do not
  inspect whether plan/candidate/governance identities exist in the target
  repository, and do not adjudicate them. Execute only the provider substantive
  task and return only the selected role schema.

In controller mode, read and follow every reference in order:

1. [kickoff](references/kickoff.md) — identify the authoritative plan and
   materialize the complete packet, then stop while authorization is absent.
2. [go](references/go.md) — validate exact Git/worktree identity, authority,
   tier/model, scope, tests, and separate execution/Git authorization.
3. [dispatch](references/dispatch.md) — route scout to the Desktop-controlled
   host-local read-only Codex CLI path, worker/executor to native Desktop
   agents, and separately authorized external review only to Claude CLI.
4. [wrapup](references/wrapup.md) — preserve active-host evidence separately
   from external-review evidence and default every next authorization to NO.

The task packet and current explicit authorization are the only authority
sources. Conversation memory, the selected host, model capability, prior work,
or a successful test cannot grant authority.

Never automatically dispatch a reviewer, retry, fall back, change models, change
roles, or continue into another Gate. The PATH `codex` executable is not the
active host. It may execute scout only when Codex Desktop dispatches the exact
`host_local_cli` contract; worker/executor remain native child tiers.

The prior native scout sandbox was shown not to enforce read-only in the
observed embedded runtime and is not a security boundary. The host-local Luna
rechecks proved runner read-only enforcement. The first exposed an over-broad
provider transport; a later Luna/low formal run passed transport validation but
repeated controller-only identity checks and returned the unsupported verdict
`BLOCKED`. The runner now keeps the complete packet controller-side, sends Luna
only a marker-delimited substantive task, and constrains feasibility verdicts
in the role schema. A post-corrective real confirmation remains pending
separate authorization. Existing Terra/Sol and schema-v3 reviewer evidence is
preserved.
