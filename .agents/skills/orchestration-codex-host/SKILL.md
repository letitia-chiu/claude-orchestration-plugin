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

Read and follow every reference in order:

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
recheck later proved runner read-only enforcement but exposed an over-broad
provider transport: feasibility content used reviewer-only collections and was
rejected. The canonical schema now supplies role-specific transports; a
Luna-only confirmation remains pending independent authorization. Existing
Terra/Sol and schema-v3 reviewer evidence is preserved.
