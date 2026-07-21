---
description: Turn a task into a dispatch order and send it to the right tier (scout/worker/executor/external model)
argument-hint: the task to dispatch
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Task to dispatch: $ARGUMENTS

Read the **target project's** `docs/playbook/orchestration.md`; if it doesn't exist, prompt the user to run `/orchestration:init-playbook` first. Follow its content:

1. **Classify the task before picking a tier.** Decide whether this is reconnaissance, independent mechanical implementation, cross-module architecture/contract work, or adversarial review. Read-only reconnaissance → scout; general work with a clear spec → worker; hard already-specified work → executor; high-risk cross-checking → an external-model review dispatch order. Things the orchestrator should do itself (judgment calls/tone/precision micro-edits/10-minute tasks) should not be dispatched.
2. **Generalize bug and review findings before writing the order.** A finding is evidence of a defect class, not merely a line to patch. State: observed instance → general defect class → authorized same-class search scope → expected proof of class closure. If the defect concerns Python runtime contracts, dataclasses, Protocols, callbacks, truthiness, enums, tuples, mappings, or frozen models, invoke the `python-runtime-contract-audit` skill and include its inventory and boundary-test requirements.
3. **Assign one invariant owner.** Production changes, shared validators, contract inventory, and boundary tests for the same invariant or defect family must stay with one executing agent/context. Do not split them across parallel workers. Parallelize only genuinely independent units with no shared invariant or contract surface.
4. **Write the internal dispatch order** with all eight sections required:
   - 【Goal】observable completion state
   - 【Scope】exact paths and workdir
   - 【No-go zones】forbidden changes and services
   - 【Invariant owner】the single owner/context for shared contract reasoning; or `not applicable`
   - 【Defect-class closure】observed instance, generalized family, same-class search scope, and exclusions; or `not applicable`
   - 【Spec】decisions already made by the orchestrator
   - 【Acceptance】mechanically verifiable commands, expected output, inventory/class-closure evidence, adversarial probes, and valid-path regression checks
   - 【Report format】conclusion → files → evidence → remaining exclusions/blockers; no large raw dumps
5. **Do not dispatch an ambiguous class-closure task.** If you cannot name the defect family or authorized search scope, inspect the code or ask the user first. Narrow scope may limit files or features, but must not prohibit checking same-class matches inside the authorized production surface.
6. Dispatch via the Task tool with the matching agent type, using the full order as the prompt. Dispatch independent orders in parallel only after the invariant-ownership check passes.
7. **Review on receipt using evidence levels.** Check: (a) inventory coverage, (b) defect-class closure, (c) adversarial/mutation probes, and (d) full regression gate. A green test count alone is not completion. The orchestrator must personally reproduce at least one adversarial item and one valid-path item for high-risk work.
8. **Control review loops.** After an external NO-GO, classify whether each finding is a new defect family or a missed member of an old one. A missed member reopens the whole family inventory; do not issue another line-item patch. Run an internal adversarial pass before spending another external-review call. If the same family returns again after fresh-context review, stop and escalate methodology or ownership instead of looping.
