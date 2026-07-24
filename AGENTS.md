# Codex-host orchestration

For Codex Desktop orchestration in this repository, use
`.agents/skills/orchestration-codex-host/SKILL.md` as the formal entry point.

Governance authority comes only from the current explicit task packet and
authorization; it is never inferred from the active host, model, or conversation
memory. An implementer must not dispatch a reviewer. Do not automatically retry,
fall back, switch models, or chain roles. External review requires a fresh,
independently authorized Claude CLI read-only packet.

For `codex_hosted`, scout is the separately authorized Desktop-controlled
`host_local_cli` path (`codex_cli / codex_read_only / gpt-5.6-luna`); worker and
executor remain native Desktop tiers. Do not use a native scout agent as a
read-only security boundary.
