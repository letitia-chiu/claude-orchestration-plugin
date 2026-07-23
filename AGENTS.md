# Codex-host orchestration

For Codex Desktop orchestration in this repository, use
`.agents/skills/orchestration-codex-host/SKILL.md` as the formal entry point.

Governance authority comes only from the current explicit task packet and
authorization; it is never inferred from the active host, model, or conversation
memory. An implementer must not dispatch a reviewer. Do not automatically retry,
fall back, switch models, or chain roles. External review requires a fresh,
independently authorized Claude CLI read-only packet.
