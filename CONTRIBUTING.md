# Contributing

Thanks for your interest in contributing to the Orchestration Workflow plugin.

## Project structure at a glance

- `commands/` — slash commands (`/dispatch`, `/init-playbook`, `/kickoff`, `/wrapup`).
- `agents/` — subagents (scout / worker / executor) that carry out the delegated work.
- `docs/playbook/` — methodology docs describing the orchestrate-and-delegate workflow.

## Local development

To try changes locally without publishing, point Claude Code at your working copy directly:

```
claude --plugin-dir <path-to-this-repo>
```

Or register it as a local marketplace and install from there:

```
/plugin marketplace add <local-path-to-this-repo>
/plugin install orchestration@orchestration-marketplace
```

## Rules for changes

- **Commands and agents must be written in English.** This keeps the plugin maintainable across contributors.
- Every command and agent file must keep its **language-mirroring directive** near the top. This directive tells the assistant to always respond in the user's own language, regardless of the fact that the instructions themselves are in English. It is a core user-facing guarantee — do not remove or weaken it when editing a command or agent.
- The same guarantee is written into the playbook methodology the orchestrator itself follows: `docs/playbook/orchestration.md` states a **語言律 (language rule)** — the orchestrator mirrors the user's language in *all* conversation and reporting, not only inside slash commands. Keep this rule when editing the playbook or the templates embedded in `commands/init-playbook.md`.

## Contributing translations

User-facing docs are translated per-language as `README.<lang>.md`. Currently available: `zh-TW`, `zh-CN`, `ja`, and the English `README.md`.

To add a new translation or update an existing one:

1. Copy the structure of `README.md` (the English source of truth) into `README.<lang>.md` (e.g. `README.fr.md`).
2. Translate the prose; keep code blocks, command names, and file paths unchanged.
3. Link the new translation from `README.md`'s language list.

## Commits and pull requests

Keep commits focused and use clear, descriptive messages; open a pull request against `main` describing what changed and why.
