---
description: "Execution order: the user approves the confirmed plan — start work now"
argument-hint: optional final adjustments
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Execution order from the user. Final adjustments (may be empty): $ARGUMENTS

This command is the formal start-work signal that `/orchestration:kickoff` waits for. The user has approved the plan and is authorizing execution **now**.

1. **Locate the confirmed plan**: the most recent plan in this conversation that the user signed off on (typically the kickoff output plus any revisions agreed in discussion). Fold any final adjustments from the arguments above into it before starting.
2. **Execute without re-asking**: dispatch per the plan's breakdown, report stage-by-stage progress, and run the target project's verification battery before reporting done. Do not ask for permission again — this command *is* the permission.
3. **If no confirmed plan exists in context** — or the discussion has drifted so far that the plan no longer matches — do not guess and do not start. Restate in one short block what you believe you are being asked to execute, and ask the user to confirm once.

Scope note: this authorization covers the confirmed plan only. Genuinely new work discovered mid-execution is a scope change — bring it back to the user instead of folding it in silently.
