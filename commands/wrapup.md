---
description: "Wrap-up ritual: verification battery → known-failures check → provider evidence → handoff (snapshot + commit)"
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Read the **target project's** `docs/playbook/README.md`; if it doesn't exist, prompt the user to run `/orchestration:init-playbook` first. Follow its wrap-up checklist (missing any item = not done):

1. Run the `docs/playbook/review-rubric.md` verification battery appropriate to the change type, and record the fingerprint (total test count, bundle name, commit/hash candidate set, etc. — project-dependent).
2. For every bug or external-review finding, verify the closure record contains: observed instance → generalized defect family → same-class search scope → every match's disposition → tests proving class closure. A patch and a green suite without this record are incomplete when the finding can generalize.
3. For high-risk contract, trust, persistence, identity, delivery, security, or authorization changes, require four evidence layers before declaring done: inventory coverage, defect-class closure, adversarial/mutation probes, and valid-path/full-suite regression. The orchestrator must personally reproduce at least one adversarial case and one valid path.
4. If the work concerns Python runtime contracts, dataclasses, Protocols, callbacks, truthiness, enums, tuples, mappings, or frozen objects, apply the `python-runtime-contract-audit` skill and confirm there is no unreviewed contract field or external boolean boundary in the authorized scope.
5. Quick-scan `docs/playbook/known-failures.md`: did you step back into an old pit? Any new pit = add it to the museum in the same commit. A repeated external-review finding from the same defect family must be recorded as a methodology failure, not merely another bug instance.
6. Self-check against `docs/playbook/architecture-constraints.md` hard rules.
7. Review-loop stop rule: after an external NO-GO, classify each finding as a new family or a missed member of an old family. A missed member reopens the family inventory. Run an internal adversarial pass before another external call. If the same family returns again after fresh-context review, stop and escalate methodology or ownership rather than continuing line-item repair loops.
8. **Provider execution evidence.** For every dispatched role in this work, record:

   ```text
   role / provider / profile / explicit model
   session ID + fresh-vs-resumed state
   task packet identity (path or content hash)
   artifact directory
   runner classified outcome
   manifest verification result (verify-manifest)
   pre/post Git state
   changed paths + allowed/forbidden result
   stdout/stderr/final-result artifact identity
   timeout/interrupt/process exit status
   ```

   **Keep active-host evidence and external-review evidence separate — never merge them into one undifferentiated list.** For an active-host tier dispatch (Task path) there is no external-runner artifact bundle — mark it explicitly as `invocation path = active_host / external manifest = not applicable`. Never fabricate an external artifact bundle that does not exist. For every entry also record the identity fields: governance identity, host mode, execution host, host tier (null for external invocations), and invocation path.
9. **Adversarial reviewer evidence.** Report the external review as its own evidence section, separate from the active-host implementation evidence. List findings / observations / suggestions / evidence gaps separately. Verify each finding carries its violated requirement and repository evidence — an item missing either is not a valid finding and may only be reported as an observation or evidence gap. Until the packet-named finding adjudicator rules, every finding is a **candidate finding**; a review outcome is not automatically an acceptance verdict, and the reviewer never becomes the adjudicator or ratifier.
10. **Git and authorization evidence.** Report explicitly: Git authorization actually granted; Git writes actually performed; push authorization; PR authorization; merge authorization; current HEAD; `git status --short`; remote state. If the project has a handoff convention, update the handoff snapshot per `docs/playbook/handoff-template.md` plus any synced status files — then commit **only** when the user's workflow authorizes commit. Never commit merely because the work is finished.
11. Report completion in three parts: ① what changed ② evidence by layer, with actual command/probe output ③ what the user should verify and exactly how to try it. List remaining exclusions and assumptions explicitly; never equate test count with proof of an invariant. End the wrap-up with the explicit authorization state — unless the current authorization packet explicitly says otherwise:

    ```text
    NEXT ROLE AUTHORIZED: NO
    NEXT BATCH AUTHORIZED: NO
    ```

    Wrap-up never starts the next role or batch on its own.
