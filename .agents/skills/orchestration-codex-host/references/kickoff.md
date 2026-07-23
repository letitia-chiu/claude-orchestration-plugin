# Kickoff

Kickoff turns the controlling request and authoritative plan into a complete,
inspectable packet. It does not authorize execution.

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
- invocation path: `active_host`
- host-local tier: `scout`, `worker`, or `executor`
- exact host-local model
- repository and absolute worktree
- current branch and HEAD
- authorization statement and issuer

Then materialize the full common 27-field task packet, including the plan/base
identities, goal, exact allowed and forbidden files, required evidence,
acceptance commands, stop conditions, Git authorization, external-side-effect
authorization, and report schema.

## Stop boundary

If any identity or contract field is absent, conflicting, remembered rather than
explicitly supplied, or not traceable to the current control window, report the
gap and stop. A complete packet is still `UNAUTHORIZED` until the authorization
issuer explicitly authorizes that exact packet and batch.

Kickoff must not dispatch a tier, invoke a provider, modify the repository, or
start a reviewer.
