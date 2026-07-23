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
└─ executor = Opus 4.8    hard execution (already-specified large refactors / precision
                          edits — self-reports its model ID on the first line so you
                          never silently run the wrong tier)
```

Five slash commands map to the stages of the workflow:

| Command | What it does |
|---|---|
| `/orchestration:kickoff` | Kickoff ritual: blind-spot pass → questions → plan (including how to split the dispatch) — **stops at the plan, does not start work** |
| `/orchestration:go` | Execution order: verifies the authoritative plan identity (planning branch / plan commit SHA / canonical base) and authorizes exactly one role or batch — conversation memory alone is not execution authority |
| `/orchestration:dispatch` | Turn a task into a complete task packet, classify its workflow role, and route it via `agent-routing.json` to the Claude subagent tiers or the bounded external runner |
| `/orchestration:wrapup` | Wrap-up ritual: verification battery → known-failures check → provider/session/artifact evidence → handoff |
| `/orchestration:init-playbook` | Generate the `docs/playbook/` skeleton — 11 files including `agent-routing.json` — in the target project (never overwrites existing files; embedded templates are drift-protected by automated tests) |

The cost intuition behind the tiers (API pricing ratio, subscription quota trends the same way): **Haiku : Sonnet : Opus ≈ 1 : 3 : 15.** Every token the orchestrator spends is the most expensive token in the system — so it delegates raw reading and mechanical edits downward and keeps only judgment for itself.

## Role-first provider routing (0.6.0)

Since 0.6.0 the workflow separates **what a task is** (its workflow role) from **which engine runs it** (provider/profile). The routing SSOT is the target project's `docs/playbook/agent-routing.json`; switching providers is a routing-file + task-packet change, not a rewrite of the commands or the methodology.

```text
role             = what the work is (behavior contract)
provider/profile = which engine executes it, and with which permission boundary
```

**Authority stays with the control window.** The ChatGPT / user control window owns architecture, authoritative planning, authorization, acceptance, finding adjudication, and final ratification. An executable provider only carries out an explicitly authorized task packet — it never becomes the plan or acceptance owner.

Default routing generated for new projects:

```text
feasibility_verifier -> codex_cli / codex_read_only
implementer          -> codex_cli / codex_workspace_write
adversarial_reviewer -> claude_cli / claude_read_only
```

Exactly three provider kinds are supported: `claude_subagent`, `codex_cli`, and `claude_cli`. There is no arbitrary-provider support, no dynamic provider discovery, no capability negotiation, no automatic fallback, and no cross-provider session migration.

**The Claude tiers remain, as the `claude_subagent` path.** `scout`, `worker`, and `executor` are unchanged and fully supported — they are the routing fallback (mapping `implementer` back to worker/executor is a one-line routing change), not deleted legacy, and not the permanently fixed implementer.

**Bounded external-agent runner.** External CLI providers are invoked only through `scripts/orchestration_agent.py`, a narrow process-safety wrapper providing: routing and provider/profile validation, single-role process invocation, wall-clock timeout and interrupt classification, separate stdout/stderr capture, structured-result validation against the shared schema (`examples/schemas/orchestration-result.schema.json`), pre/post Git evidence, read-only mutation detection, implementation changed-path allowlist validation, an artifact SHA-256 manifest, and fail-closed outcome classification. It does **not** plan, chain roles, retry or fall back automatically, commit/push/PR/merge, or clean up violating changes — and it is neither a generic provider SDK nor a Xinghui Runtime provider adapter.

**Git and side-effect boundaries.** Execution authorization is not Git authorization: commit, push, PR, and merge each require their own explicit grant. A real external CLI invocation requires the task packet to carry `External-side-effect authorization: ALLOW_PROVIDER_INVOCATION`. The implementer may not dispatch the reviewer; the reviewer is read-only and may not repair code; reviewer findings are candidate findings until the control window adjudicates them. Task-packet templates live in `examples/task-packets/`.

**Real-CLI status.** Automated tests use fake Codex and Claude executables. A separately authorized real-CLI smoke test is still required before using this workflow on a production implementation Gate — real network isolation, real schema/stream compatibility, and real quota/timeout behavior are not yet verified. This release adapts the development orchestration plugin; it does not implement the future Xinghui Runtime Claude/Codex adapter.

## Customizing the model per tier (update-safe)

The tiers ship with pinned defaults: `scout` = `claude-haiku-4-5-20251001`, `worker` = `claude-sonnet-5`, `executor` = `claude-opus-4-8`. These are sensible starting points, not a lock-in.

To run a tier on a different model, **do not edit the plugin's `agents/*.md`** — a plugin update overwrites them and your change is lost. Claude Code has no per-agent model switch in `settings.json` either. The one update-safe mechanism is **agent shadowing**: a subagent with the same `name:` in your own scope fully replaces the plugin's version, and lives where updates never touch it. Precedence, highest to lowest: project `.claude/agents/` → user `~/.claude/agents/` → plugin.

Ready-to-copy overrides live in [`examples/agents/`](examples/agents/) — copy the tiers you want to change and edit only the `model:` line:

```
# apply everywhere (user scope) …
cp examples/agents/executor.md ~/.claude/agents/executor.md
# … or just one project (project scope)
cp examples/agents/worker.md   .claude/agents/worker.md
# then open the file and change the `model:` line
```

Two caveats, both spelled out in the example files' header comments:

- An override **replaces the plugin agent wholesale** (body included), so later improvements to the plugin's agent instructions won't reach your copy — re-sync by hand if you want them.
- The `executor` carries a model-self-report probe that halts on mismatch; if you change its `model:`, update the matching model ID in its body too.

If you'd rather push *every* tier onto one model temporarily (not per-tier), the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable overrides all subagents at once.

## The engine, not the domain knowledge

This plugin ships the **engine**: the role split (scout/worker/executor — their model pinning and responsibility boundaries), the workflow (the kickoff / dispatch / wrap-up rituals), and one de-projectized, generic `orchestration.md` methodology.

It deliberately does **not** ship your project's domain knowledge: the hard rules of any specific codebase, the pitfalls it has hit, the details of its verification battery, its own handoff conventions. Those are things a project grows for itself; baked into a plugin they'd just become stale assumptions that get in the way on the next project.

The entry point for that domain knowledge is `/orchestration:init-playbook`: it generates an empty `docs/playbook/` skeleton in the target project (including the generic `orchestration.md`, a neutral seed of universal engineering lessons as the start of `known-failures.md`, and template files with fields to fill in), which that project then fills in one entry at a time through its own development. The engine installs anywhere; the domain knowledge can only be grown inside its own project.

## License

[MIT](LICENSE) © 2026 letitia-chiu
