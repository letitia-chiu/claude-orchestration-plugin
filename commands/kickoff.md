---
description: "Kickoff ritual: blind-spot pass → questions → plan (per the playbook)"
argument-hint: task description
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Task: $ARGUMENTS

Read the **target project's** playbook. Required files — if any is missing, prompt the user to run `/orchestration:init-playbook` first:

- `docs/playbook/README.md`
- `docs/playbook/orchestration.md`
- `docs/playbook/task-routing.md`
- `docs/playbook/agent-routing.json`

Follow the kickoff flow:

1. Read the project's latest handoff snapshot entry (if any) + `docs/playbook/unknowns-interview.md` + `docs/playbook/architecture-constraints.md` §hard rules (per the README's file map, read the corresponding docs for this task type).
2. **Blind-spot pass**: answer the interview's step-1 checklist item by item (machine/environment, task shape, behavior matrix, user experience); be honest about what you can't answer — list those as unknowns. For questions that need current code state, dispatch a read-only scout rather than reading a lot of files yourself.
3. **Questions**: ask only within the five categories, max 3 questions, each with a recommended option (interview step 2's question threshold).
4. **Plan**: write up the parts most likely to change and most in need of confirmation first; flag risk gates (situations where you must stop); preserve invariant-owner assignment and defect-class closure requirements for any known findings; then write the **dispatch breakdown by workflow role**, not by provider name:
   - local/read-only reconnaissance (scout — the active host's fast read-only tier);
   - `feasibility_verifier` — repository-local feasibility check against an authoritative plan commit, run by the **active host's own local tier** (never an external CLI);
   - `implementer` — the authorized implementation batches, run by the **active host's own worker/executor tier**;
   - `adversarial_reviewer` — fresh-context, read-only review of the candidate result by the **opposing provider's CLI** (claude_hosted → Codex CLI; codex_hosted → Claude CLI), requiring its own independent authorization;
   - orchestrator-owned judgment (things too small or too judgment-heavy to dispatch).

   The routing contract is the target project's `docs/playbook/agent-routing.json` (schema v2: governance-neutral, host-aware, tier-aware). Do not hardcode a provider as the routing rule, and never treat an external CLI as the default implementer or the host's own CLI as its own reviewer. Headless CLI implementation (`headless_cli_implementation`) exists only as a non-default, separately authorized opt-in. If the plan proposes `codex_hosted` execution, state that the Codex-host adapter is not implemented and the plan must fail closed there.

**Plan identity requirement.** A kickoff plan draft is a draft. Conversation text alone is not execution authority. State in the plan that before formal `/orchestration:go` execution, the plan must exist with a verifiable planning commit identity, and must carry at least these fields:

```text
Governance authority
Authorization issuer
Acceptance owner
Finding adjudicator
Final ratifier
Host mode (claude_hosted | codex_hosted — exactly one)
Active execution host
Host-local tier plan (which scout/worker/executor tiers for which batches)
Invocation path per role (active_host | external_cli | headless_cli)
Authoritative plan branch
Authoritative plan commit SHA
Canonical base SHA
Target branch/worktree
Current authorized batch or role
Goal
Allowed files
Forbidden files
Acceptance commands
Stop conditions
Git authorization
External-side-effect authorization
Role map (role -> binding, from agent-routing.json schema v2)
```

The governance identity fields are packet-scoped: the plugin never pins them to ChatGPT, Claude, Codex, or any product, and no provider may rewrite them mid-execution.

**External-side-effect boundary.** Kickoff never spends external provider quota on its own. Feasibility and implementation run on the active host's own tiers, but any external CLI invocation (the adversarial reviewer, or an opt-in headless implementation) is an external side effect: it must be listed in the plan, carry an explicit External-side-effect authorization plus its own independent reviewer/headless authorization, and be triggered by a later `/orchestration:go` or an explicit dispatch authorization — never by kickoff itself, and never automatically by the implementer.

Output the plan, then **stop and end your turn — do not begin execution**. Do not modify files. Do not invoke write-capable providers. Do not invoke external CLI providers without explicit authorization. This applies **regardless of how small or reversible the task looks**; "small and reversible" is not an exemption. While waiting you may answer questions, revise the plan, and run **read-only** local reconnaissance (scout) to close remaining unknowns.
