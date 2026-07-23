# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.6.0] - 2026-07-23

### Added

- Role-first / provider-second routing contract: workflow roles (`feasibility_verifier`, `implementer`, `adversarial_reviewer`) are resolved to a provider/profile via the project-local routing SSOT `docs/playbook/agent-routing.json`; authority owners (architecture / authoritative plan / authorization / acceptance / final adjudication) stay fixed to the ChatGPT/user control window.
- `docs/playbook/agent-routing.json` default routing file: Codex feasibility + implementation, Claude adversarial review, with fail-closed provider-separation constraints.
- Task-packet templates `examples/task-packets/codex-feasibility.md`, `examples/task-packets/codex-implementation.md`, and `examples/task-packets/claude-adversarial-review.md` (16 mandatory common header fields, fixed role behavior contracts).
- Common structured-result schema `examples/schemas/orchestration-result.schema.json`: shared envelope plus reviewer findings/observations/suggestions/evidence-gaps separation, seven mandatory finding fields, and the Blocker/Major/Minor severity enum.
- Bounded external-agent runner `scripts/orchestration_agent.py`: single-role CLI invocation, process-group timeout/interrupt control, separate stdout/stderr capture, pre/post Git evidence, read-only mutation detection, changed-path allowlist validation, artifact SHA-256 manifest with `verify-manifest`, and fail-closed outcome classification.
- Fake-CLI safety test suite (43 tests, zero quota / zero network) plus embedded-template drift protection (15 tests).

### Changed

- `/orchestration:kickoff` now requires formal planning-identity fields in the plan draft (plan branch/SHA, canonical base, allowed/forbidden files, Git and external-side-effect authorization, role map) and still stops before execution; the dispatch breakdown is written by workflow role.
- `/orchestration:go` now requires an authoritative plan commit identity — a conversation-only confirmed plan is no longer execution authority.
- `/orchestration:dispatch` resolves the workflow role first, then the provider from `agent-routing.json`; external CLI paths go through the bounded runner; the implementer cannot dispatch the reviewer and the reviewer cannot repair code.
- `/orchestration:wrapup` now records provider/session/artifact/Git-authority evidence and ends with an explicit `NEXT ROLE AUTHORIZED: NO` / `NEXT BATCH AUTHORIZED: NO` state.
- `/orchestration:init-playbook` now generates 11 files (adding `agent-routing.json`), keeps skip-don't-overwrite semantics for every existing target file including custom routing, and its embedded templates use four-backtick outer fences protected by automated byte-level drift tests.
- Default role mapping becomes Codex feasibility + implementation with Claude adversarial review; the existing Claude `scout`/`worker`/`executor` agents remain byte-unchanged as the `claude_subagent` fallback path.

### Security

- No automatic role chaining, reviewer dispatch, provider fallback, or semantic retry in the runner or the commands.
- The runner performs no Git writes (a read-only Git evidence allowlist is enforced in code and by AST tests) and never cleans or reverts violating changes — evidence is preserved for adjudication.
- Provider separation fails closed: implementer and reviewer must resolve to different providers, and read-only roles cannot map to write-capable profiles.
- Read-only mutation and forbidden-path changes are detected through independent pre/post Git evidence, never through provider self-reporting alone.
- Dangerous provider bypass flags are excluded by static tests; automated tests use fake `codex`/`claude` executables only.
- A separately authorized real-CLI smoke test is still pending and required before production-Gate use: real network isolation, real output-schema/stream compatibility, and real quota/timeout behavior are not yet verified.
- This release adapts the development orchestration plugin only; it does not implement the future Xinghui Runtime Claude/Codex adapter.

## [0.5.0] - 2026-07-21

### Added

- `python-runtime-contract-audit` Skill for high-risk Python contract surfaces: dataclasses, `frozen=True`, Protocols/callbacks, exact booleans, enum discriminators, immutable containers, nested payloads, persistence/evidence/identity boundaries, and defect-family closure.
- Explicit **Invariant owner** and **Defect-class closure** sections in dispatch orders.
- Four-layer acceptance evidence for high-risk work: inventory coverage, defect-class closure, adversarial/mutation probes, and valid-path/full-suite regression.
- Review-loop stop rule: a repeated same-family finding reopens the whole family inventory; after fresh-context repetition, stop line-item repair loops and escalate method or ownership.

### Changed

- `/orchestration:dispatch` now generalizes findings before delegation, prevents parallel workers from sharing one invariant, and treats a green test count as only one evidence layer.
- `worker` and `executor` now distinguish product-scope expansion from required same-class closure, invoke the Python contract Skill when applicable, and stop when a defect family repeats.
- `/orchestration:wrapup` now requires closure records and adversarial plus valid-path spot checks for high-risk boundaries.
- `docs/playbook/orchestration.md` expanded from role routing into a complete finding-generalization, invariant-ownership, evidence, and review-loop methodology, while retaining the v0.3.0–v0.4.0 hard rules (go-gate "small and reversible is not an exception" clause, effort pinning details, review-model risk tiers, lens-doubling fallback, language-law drift warning).
- `/orchestration:init-playbook` embedded `orchestration.md` / `README.md` templates synchronized with the new methodology, so newly initialized projects get the same rules.
- Update-safe agent override examples synchronized with the new execution discipline.

## [0.4.0] - 2026-07-21

### Changed

- `executor` tier default bumped to **Opus 4.8** (`claude-opus-4-8`) — was Opus 4.6. Updated everywhere the tier is labeled or fingerprint-probed: `agents/executor.md` (frontmatter `model:` + the self-report halt check), all four READMEs, `docs/playbook/orchestration.md`, and the embedded playbook in `commands/init-playbook.md`. `scout` (Haiku 4.5) and `worker` (Sonnet 5) defaults unchanged.
- Re-synced the `orchestration.md` embedded in `commands/init-playbook.md` (File 2/10) to the current root `docs/playbook/orchestration.md` — it had drifted behind on three prior releases: the 0.3.0 `go` gate in the boot ritual (kickoff now stops at the plan), the 0.3.1 risk-tiered external-review/lens wording, and the effort note (`scout` unset because Haiku 4.5 has no effort parameter, not "low"). The embed is what actually ships to target projects, so the stale copy meant new projects got the old methodology.
- `universal-lessons.md` seed trimmed from 26 to 21 entries — removed the five that read as single-stack war-stories (Python sqlite3 `with`/close, mobile PWA layout, frontend multi-layer cache, flex/inline-block baseline, reference-code pixel-porting) to keep the seed genuinely cross-technology. Synced symmetrically across all three copies (root `universal-lessons.md`, the embed in `commands/init-playbook.md`, and this repo's own `docs/playbook/known-failures.md`).

### Added

- **Update-safe per-tier model customization.** The tiers still ship pinned defaults, but users can now override the model a tier runs on without a plugin update clobbering it, via same-name agent shadowing in `~/.claude/agents/` (user scope) or `.claude/agents/` (project scope). Ships ready-to-copy full overrides under `examples/agents/` (`scout.md` / `worker.md` / `executor.md`) and a "Customizing the model per tier (update-safe)" section in all four READMEs. (Claude Code has no per-agent `model:` switch in `settings.json`; the all-tiers-at-once `CLAUDE_CODE_SUBAGENT_MODEL` env var is documented as the coarse alternative.)

## [0.3.1] - 2026-07-09

### Changed

- `orchestration.md`: external-model reviews and verification lenses are now explicitly risk-tiered — a balanced model handles routine reviews, the flagship is reserved for critical gates; mid-risk lenses may run on the worker tier (findings still return to the orchestrator for adversarial verification).

## [0.3.0] - 2026-07-09

### Added

- `/orchestration:go` — explicit execution order. `kickoff` now stops at the plan; nothing is executed until the user fires `go` (or gives an unambiguous instruction to start). The authorization is injected fresh at the moment of use instead of relying on rules buried in long context.
- `worker` / `executor` agents pin `effort: medium` in frontmatter (`scout` stays unset — Haiku 4.5 does not support the effort parameter).

### Changed

- `kickoff` hard stop: removed the "clearly small and reversible → may proceed directly" exemption — it was the loophole for premature starts.

## [0.2.0] - 2026-07-05

First public release: open-source packaging and multi-language documentation.

### Added

- MIT `LICENSE`.
- `.gitignore` covering common OS, editor, and dependency artifacts.
- `CHANGELOG.md` (this file).
- `license`, `repository`, and `homepage` metadata in `.claude-plugin/plugin.json`.

### Changed

- Englishified the operational surface: `commands/`, `agents/`, and the plugin/marketplace manifests are now written in English.
- Added a language-mirroring directive to every command and agent so the assistant always responds in the user's own language, independent of the instruction language.
- `README.md` is now available in four languages: English (`README.md`), Traditional Chinese (`README.zh-TW.md`), Simplified Chinese (`README.zh-CN.md`), and Japanese (`README.ja.md`).
- Documented language-mirroring as an explicit orchestrator discipline (語言律) in the playbook methodology — `docs/playbook/orchestration.md`, the wrap-up reporting step in `docs/playbook/README.md`, and their templates embedded in `commands/init-playbook.md` — so the guarantee ships beyond the 7 command/agent files.

Deferred — multilingual translation of docs/playbook/ skeletons, universal-lessons.md, and init-playbook's embedded templates (currently Traditional Chinese).

## [0.1.0] - 2026-07-05

- Initial internal version: the Traditional-Chinese orchestration plugin (scout / worker / executor tiers plus the four slash commands), before open-source packaging.
