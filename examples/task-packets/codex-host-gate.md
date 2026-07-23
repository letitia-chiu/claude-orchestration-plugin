# Task Packet — Codex-Hosted Gate

> Formal 27-field packet for one Codex Desktop active-host feasibility or
> implementation Gate. Replace every `<...>` value from the current control
> window. Packet completeness is not authorization.

## Common header（27 fields required）

| Field | Value |
|---|---|
| Governance authority | `<explicit governance authority identity>` |
| Authorization issuer | `<issuer for this exact Gate>` |
| Acceptance owner | `<acceptance owner>` |
| Finding adjudicator | `<candidate-finding adjudicator>` |
| Final ratifier | `<final ratifier>` |
| Host mode | `codex_hosted` |
| Active execution host | `codex_desktop` |
| Host-local tier | `<scout, worker, or executor>` |
| Host-local model | `<gpt-5.6-luna, gpt-5.6-terra, or gpt-5.6-sol matching the selected tier, unless an explicit project-local override is authorized>` |
| Invocation path | `active_host` |
| External reviewer provider/profile/model | `not applicable` — the implementer cannot dispatch a reviewer; review needs a new packet and authorization |
| Role | `<feasibility_verifier or implementer>` |
| Provider/profile | `codex_native / <scout, worker, or executor>` |
| Explicit model | `<exact model ID>` |
| Repository/worktree | `<absolute authorized worktree path>` |
| Authoritative plan branch | `<plan branch>` |
| Authoritative plan commit SHA | `<exact plan SHA>` |
| Canonical base SHA | `<exact canonical base SHA>` |
| Target SHA or batch base SHA | `<exact pre-Gate HEAD>` |
| Goal | `<one Gate, one observable outcome>` |
| Allowed files | `<exhaustive repo-relative paths; every unlisted path is forbidden>` |
| Forbidden files | `<explicit forbidden paths>`; fixed addition: every path not in Allowed files |
| Required evidence | `<pre/post Git, changed files, tier/thread/model identity, commands, tests, expected results>` |
| Stop conditions | `<Gate-specific stops>`; fixed: identity mismatch, missing authorization, unavailable model, forbidden-file need, plan/repository conflict, or ambiguous specification |
| Git authorization | `<NONE by default, or one exact separately authorized Git action; commit never implies push/PR/merge>` |
| External-side-effect authorization | `NONE` — active-host work cannot invoke Claude CLI or another provider |
| Report schema | `examples/schemas/orchestration-result.schema.json` with `invocation_path=active_host` |

## Fixed contract

- Governance authority, active host, host-local tier, and external reviewer are
  independent identities.
- Read the authoritative plan at the exact SHA and verify the exact worktree,
  branch, HEAD, and clean status before work.
- `scout` is read-only inventory/feasibility. `worker` owns one specified
  invariant or defect family. `executor` owns authorized cross-module or
  high-risk closure. A higher model tier grants no additional authority.
- Work only in Allowed files, honor Forbidden files, run only the named
  acceptance commands, and stop at every listed condition.
- Execution authorization and Git authorization are separate. `NONE` forbids
  commit, push, pull request, merge, amend, rebase, tag, branch, and worktree
  writes.
- Conversation memory and previous sessions are not authorization.
- The active host never calls the external runner for feasibility or
  implementation. The PATH Codex CLI is not the active host.
- The implementer cannot dispatch a reviewer. Claude CLI review requires a
  fresh `adversarial_reviewer` packet, independent authorization, and
  `ALLOW_PROVIDER_INVOCATION` in both packet and runner CLI.
- Never automatically retry, fall back, switch models, resume, or chain roles.
- Report active-host evidence with external runner session/manifest recorded as
  `not applicable`.
- All next-step authorization defaults to NO after this Gate.

## Required wrap-up

Record the governance and plan identities, Codex Desktop host thread UUID,
native child thread/task UUID, selected tier, configured and actual model,
pre/post Git evidence, exact changed files, test commands/results, Git actions,
unsupported capabilities, and evidence gaps.

Do not infer real-smoke success from static configuration. Luna/Terra/Sol real
spawn, distinct child/model evidence, scout sandbox precedence,
embedded/standalone runtime parity, and real Claude reviewer evidence remain
pending separate authorization.
