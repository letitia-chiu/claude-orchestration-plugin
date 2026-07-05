---
description: "Wrap-up ritual: verification battery → known-failures check → handoff (snapshot + commit)"
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Read the **target project's** `docs/playbook/README.md`; if it doesn't exist, prompt the user to run `/orchestration:init-playbook` first. Follow its wrap-up checklist (missing any item = not done):

1. Run the `docs/playbook/review-rubric.md` verification battery appropriate to the change type, and record the fingerprint (total test count, bundle name, etc. — project-dependent).
2. Quick-scan `docs/playbook/known-failures.md`: did you step back into an old pit? Any new pit = add it to the museum in the same commit.
3. Self-check against `docs/playbook/architecture-constraints.md` hard rules.
4. If the project has a handoff convention, update the handoff snapshot per its `docs/playbook/handoff-template.md` (insert the new entry at the top; if there are too many closed-out entries, move the old ones to a history file) + any other status files that are synced alongside handoffs, then commit (for dispatch orders, mark them done per the project's status-stamping convention).
5. Report completion in three parts: ① what changed ② where it was verified (with actual command output) ③ what the user should verify + **exactly how to try it (the precise path)**.
