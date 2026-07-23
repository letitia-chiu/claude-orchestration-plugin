# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.7.0] - 2026-07-24

### Added

- Governance-neutral routing schema v2 with two active hosts, one packet-defined
  governance identity, and explicit separation between governance authority,
  active execution host, host-local tier, and external reviewer.
- Host-native `scout` / `worker` / `executor` tiers for both Claude-hosted and
  Codex-hosted operation, with reciprocal read-only CLI review: Codex CLI
  reviews Claude-hosted work and Claude CLI reviews Codex-hosted work.
- Repository-local Codex custom agents, the
  `.agents/skills/orchestration-codex-host` workflow entry, shared 27-field task
  packets, and a strict schema v2 result envelope.
- `scripts/init_codex_host.py`, a deterministic target-project materializer for
  the 21 files required by Codex Desktop, with read-only `--check` mode.
- Fake Codex/Claude transport coverage for authorization preflight, timeout,
  process-group cleanup, partial transcripts, Git evidence, changed-path
  allowlists, structured results, and artifact manifests.

### Changed

- The active host now performs repository feasibility and implementation using
  its own native tier. External CLIs are reserved for fresh adversarial review;
  headless Codex implementation remains a separately authorized, non-default
  opt-in.
- Kickoff, go, dispatch, and wrapup now preserve authoritative-plan identity,
  five governance identities, host/tier/model identity, allowed/forbidden
  files, separate execution/Git/provider authorization, and distinct
  active-host versus external-review evidence.
- Public documentation and plugin metadata now describe the dual-host 0.7.0
  surface. This release supersedes the unreleased 0.6.0 candidate; 0.6.0 was
  never published and is not part of the released-version history.

### Security

- Governance, execution, Git writes, and provider invocation are independent
  grants. A packet and external-runner command must both carry
  `ALLOW_PROVIDER_INVOCATION` before a CLI process can start.
- Implementers cannot dispatch reviewers; reviewers are fresh and read-only;
  automatic retry, fallback, provider switching, and role chaining remain
  forbidden.
- Codex target installation is transactional and no-overwrite: any conflict,
  including a different `AGENTS.md`, aborts before all writes. Identical files
  are not rewritten, and global configuration is never changed.
- The runner performs no Git writes and validates repository mutations through
  independent pre/post evidence rather than provider self-report.

### Known limitations

- Real rechecks remain pending for Claude-hosted → Codex CLI review and
  Codex-hosted → Claude CLI review.
- Real Luna/Terra/Sol native-agent spawning, distinct child-thread/model
  evidence, scout sandbox precedence, and embedded/standalone Codex runtime
  parity remain unverified.
- Native per-file sandbox enforcement is unavailable. Codex distribution is a
  repository-local materializer, not a native Plugin Directory package.
- Two defects found by earlier real Codex CLI probes were fixed in C1, but those
  corrected paths have not yet received a real-CLI recheck.

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
