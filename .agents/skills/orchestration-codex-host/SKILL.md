---
name: orchestration-codex-host
description: Formal Codex Desktop entry for governance-bound kickoff, authorization, native tier dispatch, and evidence-separated wrap-up.
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
3. [dispatch](references/dispatch.md) — route active-host work only to the
   Codex Desktop native scout/worker/executor surface; route a separately
   authorized external review only to Claude CLI read-only.
4. [wrapup](references/wrapup.md) — preserve active-host evidence separately
   from external-review evidence and default every next authorization to NO.

The task packet and current explicit authorization are the only authority
sources. Conversation memory, the selected host, model capability, prior work,
or a successful test cannot grant authority.

Never automatically dispatch a reviewer, retry, fall back, change models, change
roles, or continue into another Gate. Never treat the PATH `codex` executable as
the active host. The active implementation host is the current Codex Desktop
thread and its explicitly selected native child tier.

Real Luna/Terra/Sol child spawning, child thread/model identity, scout sandbox
precedence, embedded/standalone runtime parity, and a real Claude CLI review
remain pending independent smoke authorization.
