---
description: Turn a task into a dispatch order and send it to the right tier (scout/worker/executor/external model)
argument-hint: the task to dispatch
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Task to dispatch: $ARGUMENTS

Read the **target project's** `docs/playbook/orchestration.md`; if it doesn't exist, prompt the user to run `/orchestration:init-playbook` first. Follow its content:

1. **Pick the tier** (decision table): read-only reconnaissance → scout; general work with a clear spec → worker; hard work that's already been spec'd → executor; high-risk cross-checking → an external-model review dispatch order (if the project has a delegation template, follow its format). Things the orchestrator should do itself (judgment calls/tone/precision micro-edits/10-minute tasks) should not be dispatched — do them directly.
2. **Write the internal dispatch order** (all six sections required): 【Goal】【Scope】【No-go zones】【Spec】【Acceptance — mechanically verifiable commands + expected output】【Report format】. If the spec is unclear, clarify it first (check the code, ask the user) — never dispatch something ambiguous.
3. Dispatch via the Task tool with the matching agent type, using the full dispatch order as the prompt; dispatch independent orders in parallel.
4. **Review on receipt**: check against the 【Acceptance】 items one by one; the orchestrator must personally spot-check at least one item. Not passing = send it back for rework or escalate to a higher tier; a blocker reported by the executing tier = the orchestrator fills in the missing spec and redispatches.
