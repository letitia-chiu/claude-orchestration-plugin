# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2026-07-05

First public release.

### Added

- MIT `LICENSE`.
- `CONTRIBUTING.md` with project structure, local development, and contribution guidelines.
- `.gitignore` covering common OS, editor, and dependency artifacts.
- `CHANGELOG.md` (this file).
- `license`, `repository`, and `homepage` metadata in `.claude-plugin/plugin.json`.

### Changed

- Englishified the operational surface: `commands/`, `agents/`, and the plugin/marketplace manifests are now written in English.
- Added a language-mirroring directive to every command and agent so the assistant always responds in the user's own language, independent of the instruction language.
- `README.md` is now available in four languages: English (`README.md`), Traditional Chinese (`README.zh-TW.md`), Simplified Chinese (`README.zh-CN.md`), and Japanese (`README.ja.md`).
- Documented language-mirroring as an explicit orchestrator discipline (語言律) in the playbook methodology — `docs/playbook/orchestration.md`, the wrap-up reporting step in `docs/playbook/README.md`, and their templates embedded in `commands/init-playbook.md` — so the guarantee ships beyond the 7 command/agent files.

Deferred — multilingual translation of docs/playbook/ skeletons, universal-lessons.md, and init-playbook's embedded templates (currently Traditional Chinese).
