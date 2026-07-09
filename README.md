# orchestration — an orchestrate-and-delegate workflow for Claude Code

**English** · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

A cross-project set of slash commands and subagents that package a simple idea: **the main session is your most expensive tokens, so it should only think — planning, breaking work down, verifying, and handing off — while mechanical reconnaissance, implementation, and heavy lifting go to three model-pinned subagents.** Install it on any project and your main session stops doing grunt work.

> 🌐 **Works in your language.** The commands and subagents are authored in English for maintainability, but every one of them instructs Claude to *mirror your language*. Chat in Japanese and Claude plans, asks, and reports back in Japanese; chat in Traditional Chinese and it answers in Traditional Chinese. Englishifying the internals does **not** make the assistant English-only.

## Install

From the plugin marketplace (public repo):

```
/plugin marketplace add letitia-chiu/claude-orchestration-plugin
/plugin install orchestration@orchestration-marketplace
```

To try it during development without the marketplace flow:

```
claude --plugin-dir /path/to/claude-orchestration-plugin
```

Once installed, the commands appear namespaced by the plugin: `/orchestration:kickoff`, `/orchestration:go`, `/orchestration:dispatch`, `/orchestration:wrapup`, `/orchestration:init-playbook`.

## The three-tier architecture

```
Orchestrator (main session — the strongest available model + high effort)
│  Only does: understand the request, blind-spot/questions, break work down,
│  dispatch, adversarial verification, integration, handoff.
│
├─ scout    = Haiku 4.5   read-only reconnaissance (find files / read code / summarize
│                          current state — returns conclusions only; tools locked to
│                          Read/Glob/Grep)
├─ worker   = Sonnet 5    default execution (well-specified implementation / tests /
│                          batch edits / docs)
└─ executor = Opus 4.6    hard execution (already-specified large refactors / precision
                          edits — self-reports its model ID on the first line so you
                          never silently run the wrong tier)
```

Five slash commands map to the stages of the workflow:

| Command | What it does |
|---|---|
| `/orchestration:kickoff` | Kickoff ritual: blind-spot pass → questions → plan (including how to split the dispatch) — **stops at the plan, does not start work** |
| `/orchestration:go` | Execution order: nothing is executed until the user fires this (the authorization is injected fresh at the moment of use, so it can't be diluted by long context) |
| `/orchestration:dispatch` | Turn a task into a six-field dispatch order and send it to the right tier |
| `/orchestration:wrapup` | Wrap-up ritual: verification battery → known-failures check → handoff |
| `/orchestration:init-playbook` | Generate the `docs/playbook/` skeleton in the target project (never overwrites existing files) |

The cost intuition behind the tiers (API pricing ratio, subscription quota trends the same way): **Haiku : Sonnet : Opus ≈ 1 : 3 : 15.** Every token the orchestrator spends is the most expensive token in the system — so it delegates raw reading and mechanical edits downward and keeps only judgment for itself.

## The engine, not the domain knowledge

This plugin ships the **engine**: the role split (scout/worker/executor — their model pinning and responsibility boundaries), the workflow (the kickoff / dispatch / wrap-up rituals), and one de-projectized, generic `orchestration.md` methodology.

It deliberately does **not** ship your project's domain knowledge: the hard rules of any specific codebase, the pitfalls it has hit, the details of its verification battery, its own handoff conventions. Those are things a project grows for itself; baked into a plugin they'd just become stale assumptions that get in the way on the next project.

The entry point for that domain knowledge is `/orchestration:init-playbook`: it generates an empty `docs/playbook/` skeleton in the target project (including the generic `orchestration.md`, a neutral seed of universal engineering lessons as the start of `known-failures.md`, and template files with fields to fill in), which that project then fills in one entry at a time through its own development. The engine installs anywhere; the domain knowledge can only be grown inside its own project.

## License

[MIT](LICENSE) © 2026 letitia-chiu
