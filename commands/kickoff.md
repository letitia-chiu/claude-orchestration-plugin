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
   - local/read-only reconnaissance (scout via the `claude_subagent` path);
   - `feasibility_verifier` — repository-local feasibility check against an authoritative plan commit;
   - `implementer` — the authorized implementation batches;
   - `adversarial_reviewer` — fresh-context, read-only review of the candidate result;
   - orchestrator-owned judgment (things too small or too judgment-heavy to dispatch).

   For each role, the provider/profile comes from the target project's `docs/playbook/agent-routing.json` — do not hardcode worker/executor/an external model as the routing rule. You may note that the `claude_subagent` fallback path (scout/worker/executor) exists, but it is a routing option, not the fixed default.

**Plan identity requirement.** A kickoff plan draft is a draft. Conversation text alone is not execution authority. State in the plan that before formal `/orchestration:go` execution, the plan must exist with a verifiable planning commit identity, and must carry at least these fields:

```text
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
Role map (role -> provider/profile, from agent-routing.json)
```

**External-side-effect boundary.** Kickoff never spends external provider quota on its own. Even though `feasibility_verifier` is read-only, invoking an external CLI provider is an external side effect: it must be listed in the plan, carry an explicit External-side-effect authorization, and be triggered by a later `/orchestration:go` or an explicit dispatch authorization — never by kickoff itself.

Output the plan, then **stop and end your turn — do not begin execution**. Do not modify files. Do not invoke write-capable providers. Do not invoke external CLI providers without explicit authorization. This applies **regardless of how small or reversible the task looks**; "small and reversible" is not an exemption. While waiting you may answer questions, revise the plan, and run **read-only** local reconnaissance (scout) to close remaining unknowns.
