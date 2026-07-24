# Kickoff

Kickoff turns the controlling request and authoritative plan into a complete,
inspectable packet. It does not authorize execution.

This is a **controller-only** phase. A runner-dispatched provider whose prompt
states `Provider execution phase: substantive_only` must not repeat kickoff,
read controller-only identities from the packet, or validate them in the target
repository.

## Required inputs

Read the authoritative plan at the exact supplied branch and commit identity.
Collect all five governance identities without deriving any from a product or
model:

1. Governance authority
2. Authorization issuer
3. Acceptance owner
4. Finding adjudicator
5. Final ratifier

Collect the execution identity:

- host mode: `codex_hosted`
- active execution host: `codex_desktop`
- invocation path: `host_local_cli` for scout; `active_host` for worker/executor
- host-local tier: `scout`, `worker`, or `executor`
- exact host-local model
- exact host-local reasoning effort (`low` for Codex-hosted scout)
- repository and absolute worktree
- authoritative plan SHA
- plugin/release implementation candidate SHA
- target repository HEAD
- target repository status/dirty-state evidence
- authorization statement and issuer

Then materialize the full C2 packet, including the plan/base
identities, goal, exact allowed and forbidden files, required evidence,
acceptance commands, stop conditions, Git authorization, host-local execution
authorization, external-side-effect authorization, and report schema.

## Stop boundary

If any identity or contract field is absent, conflicting, remembered rather than
explicitly supplied, or not traceable to the current control window, report the
gap and stop. A complete packet is still `UNAUTHORIZED` until the authorization
issuer explicitly authorizes that exact packet and batch.

Kickoff must not dispatch a tier, invoke a provider, modify the repository, or
start a reviewer.
