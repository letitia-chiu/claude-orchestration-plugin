---
description: "Execution order: the user authorizes the exact planned role/batch — verify plan identity, then start"
argument-hint: optional final adjustments
---
> **Language — always respond in the user's language.** This file is written in English for maintainability. English is the language of these *instructions*, not of your *output*. Converse with, question, and report to the user in the same language they write to you in: Traditional Chinese in → Traditional Chinese out; Simplified Chinese → Simplified Chinese; Japanese → Japanese; English → English. Never switch to English just because this file happens to be in English.

Execution order from the user. Final adjustments (may be empty): $ARGUMENTS

This command is the formal start-work signal that `/orchestration:kickoff` waits for. It authorizes execution of **exactly one currently authorized role or batch** — nothing more.

1. **Locate the formal execution authority.** Conversation memory alone is not authority. The authorization must reference an authoritative plan with a verifiable identity:
   - governance identity (Governance authority / Authorization issuer / Acceptance owner / Finding adjudicator / Final ratifier — packet-scoped, never assumed, never pinned to a product by the plugin);
   - host mode (`claude_hosted` or `codex_hosted` — exactly one active host; missing host mode = stop);
   - host-local tier authorization (which scout/worker/executor tier this batch may use) and invocation path (`active_host` / `external_cli` / `headless_cli`);
   - authoritative planning branch;
   - authoritative plan commit SHA;
   - canonical base SHA;
   - the exact authorized role or batch;
   - allowed files and forbidden files;
   - acceptance commands;
   - stop conditions;
   - Git authorization;
   - External-side-effect authorization.

   Chat revisions count only if they are already reflected in the authoritative plan commit, or are explicitly recorded as a narrow supplement to this authorization packet. Vague recollection of "what we agreed" is not authority.

2. **Verify the plan identity before executing.** Adapt the exact refs/paths to the target project's convention, but the semantics are fixed — the planning ref must resolve, the plan SHA must match exactly, base/target identity must be verifiable, the worktree state must match the authorization, and the plan content must be readable:

   ```bash
   git status --short
   git branch --show-current
   git rev-parse HEAD
   git fetch origin
   git rev-parse <planning-ref>
   git show <plan-sha>:<plan-file>
   ```

   If verification fails, or the requested work exceeds what the plan authorizes (scope drift), stop before any execution.

3. **Resolve routing, then execute through the dispatch contract.** Determine the executable role for this authorization (`feasibility_verifier`, `implementer`, or `adversarial_reviewer` — or orchestrator-owned work that needs no dispatch), read the target project's `docs/playbook/agent-routing.json` (schema v2), and resolve through the dual-host contract:
   - **Claude-hosted feasibility/implementation** runs on the active Claude host via the Task/agent path, using the host's own scout/worker/executor tier named in the authorization — never an external CLI by default;
   - **Codex-hosted feasibility** runs only as `host_local_cli / scout / codex_cli / codex_read_only / gpt-5.6-luna`, with matching packet and CLI `ALLOW_HOST_LOCAL_CLI_INVOCATION`; its external reviewer authorization must remain separate;
   - **Codex-hosted implementation** remains native Desktop worker/executor;
   - **the adversarial reviewer** resolves to the opposing provider's CLI (claude_hosted → Codex CLI read-only) and requires its own independent reviewer authorization — `/go` for an implementation batch never implies it;
   - **headless CLI implementation** requires the authorization to name `headless_cli` explicitly — it is never inferred;
   - validate authoritative plan SHA, release/implementation candidate SHA, target repository HEAD, and target dirty-state evidence independently; status evidence is `CLEAN` or the controller-produced `sha256:<digest>` of exact `git status --short --untracked-files=all` UTF-8 bytes, and none of these identities substitutes for another.

   Hand off per the `/orchestration:dispatch` contract. Unknown or unsafe routing stops before any spawn. Do not re-ask for permission for the exact authorized scope — this command *is* that permission.

4. **Missing authority = stop.** If identity fields are missing, stop and list them, including governance identity, plan SHA, candidate SHA, target repository HEAD, target dirty-state evidence, host/tier/path, scope, Git authorization, host-local execution authorization, and external-side-effect authorization.

Scope rules:

- This authorization covers the one named role/batch only. It does not imply the next batch, a reviewer dispatch, or any follow-on role. Genuinely new work discovered mid-execution is a scope change — bring it back to the user instead of folding it in silently.
- **Git authorization is separate from execution authorization.** `/go` means "execute the exact authorized role/batch". It does not grant commit, push, PR, merge, rebase, force push, or branch/worktree deletion. Git writes happen only when the task packet's `Git authorization` field explicitly lists them, and only exactly what is listed.
