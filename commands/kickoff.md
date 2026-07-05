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

Output the above four items and wait for confirmation before proceeding; if the task is clearly small and reversible you may proceed directly, but still write out your assumptions.
