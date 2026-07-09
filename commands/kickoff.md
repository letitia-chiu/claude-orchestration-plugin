---
description: "Kickoff ritual: blind-spot pass → questions → plan (per the playbook)"
argument-hint: task description
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Task: $ARGUMENTS

Read the **target project's** `docs/playbook/README.md`; if it doesn't exist, prompt the user to run `/orchestration:init-playbook` first. Follow its kickoff flow:

1. Read the project's latest handoff snapshot entry (if any) + `docs/playbook/unknowns-interview.md` + `docs/playbook/architecture-constraints.md` §hard rules (per the README's file map, read the corresponding docs for this task type).
2. **Blind-spot pass**: answer the interview's step-1 checklist item by item (machine/environment, task shape, behavior matrix, user experience); be honest about what you can't answer — list those as unknowns. For questions that need current code state, dispatch a scout rather than reading a lot of files yourself.
3. **Questions**: ask only within the five categories, max 3 questions, each with a recommended option (interview step 2's question threshold).
4. **Plan**: write up the parts most likely to change and most in need of confirmation first; flag risk gates (situations where you must stop); flag the **dispatch breakdown** (what you do yourself vs. what you dispatch to scout/worker/executor/an external model for review — decision criteria in `docs/playbook/orchestration.md`).

Output the above four items, then **stop and end your turn — do not begin execution**. Do not modify files and do not dispatch write-capable agents (worker/executor) until the user issues the execution order — `/orchestration:go` — or unambiguously tells you to start in their own words. This applies **regardless of how small or reversible the task looks**; "small and reversible" is not an exemption. While waiting you may answer questions, revise the plan, and run **read-only** reconnaissance (scout) to close remaining unknowns.
