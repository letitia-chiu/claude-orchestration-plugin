# orchestration — dual-host orchestration for Claude and Codex

**English** · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

Version: **0.7.0**

This repository provides one governance-neutral orchestration contract with two
active-host adapters. Claude Desktop / Claude Code can run the workflow with
Claude-native agents. Codex Desktop uses a Desktop-controlled host-local CLI
scout and native worker/executor agents.
Either host may hand a frozen candidate to the other provider's CLI for a fresh,
read-only adversarial review.

The core separation is:

```text
governance authority
!= active execution host
!= host-local scout / worker / executor tier
!= external adversarial reviewer
```

Governance is not fixed to ChatGPT, Claude, Codex, or another product. Every
task packet explicitly names the governance authority, authorization issuer,
acceptance owner, finding adjudicator, and final ratifier. A host, model, or
reviewer cannot infer those powers from its role.

## Host modes and tier parity

| Host mode | Active host | Host-local tiers | External reviewer |
|---|---|---|---|
| `claude_hosted` | Claude Desktop / Claude Code | `scout` / `worker` / `executor` using Claude-native model tiers | Codex CLI / `codex_read_only` |
| `codex_hosted` | Codex Desktop | scout = `host_local_cli` Codex CLI / Luna; worker/executor = native Terra/Sol | Claude CLI / `claude_read_only` |

`scout` handles read-only inventory and narrow feasibility, `worker` handles a
specified implementation with one invariant or defect family, and `executor`
owns cross-module or high-risk contractual closure. Higher capability never
adds file, Git, acceptance, adjudication, ratification, or governance authority.

Codex-hosted feasibility uses the separately authorized Desktop-controlled
`host_local_cli / codex_cli / codex_read_only / gpt-5.6-luna` tier.
Worker/executor implementation stays native Desktop Terra/Sol. This scout path
is not an external reviewer or fallback. The implementer cannot start
the reviewer, and there is no automatic reviewer dispatch, retry, fallback,
model switching, or role chaining. `headless_cli` implementation is a
non-default opt-in that requires separate authorization.

## Install for a Claude-hosted project

Install from the Claude plugin marketplace:

```text
/plugin marketplace add letitia-chiu/claude-orchestration-plugin
/plugin install orchestration@orchestration-marketplace
```

For development:

```bash
claude --plugin-dir /path/to/claude-orchestration-plugin
```

The Claude-hosted surface is the namespaced command set
(`/orchestration:kickoff`, `/orchestration:go`, `/orchestration:dispatch`,
`/orchestration:wrapup`, `/orchestration:init-playbook`) plus
`agents/scout.md`, `agents/worker.md`, and `agents/executor.md`.

Claude model customization remains update-safe through same-name agent
shadowing. Project `.claude/agents/` overrides user `~/.claude/agents/`, which
overrides the plugin; ready-to-copy examples live in `examples/agents/`.
Claude-hosted adversarial review uses a separately authorized, fresh Codex CLI
read-only session.

## Install for a Codex-hosted project

Files in this plugin checkout do not automatically appear in another
repository. Materialize the Codex-host adapter into an explicit target Git
root:

```bash
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository
```

Check an installation without writing:

```bash
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository \
  --check
```

The target must be an existing absolute Git repository path. The materializer
installs exactly 20 repository-local files: `AGENTS.md`, the two native
`.codex/agents` worker/executor definitions, the Codex-host skill and references, the shared
playbook/routing/schema/task packets, and the Claude reviewer runner.

Installation is transactional and no-overwrite. Missing files are copied,
identical files are left untouched, and any different file makes the whole run
fail with zero writes. A different existing `AGENTS.md` requires a repository
owner to merge it manually. Re-running after a plugin update is safe: unchanged
files remain a no-op, while project-local customizations become conflicts
instead of being overwritten.

The materializer does not modify global Codex or Claude configuration, invoke a
provider, or perform Git writes. This is a repository-local materializer, not a
native Codex Plugin Directory package. Codex-hosted adversarial review uses the
target's own `scripts/orchestration_agent.py`,
`docs/playbook/agent-routing.json`, and
`examples/schemas/orchestration-result.schema.json`.

## Safety and evidence contract

Every authorized packet separately carries the authoritative plan SHA,
release/implementation candidate SHA, target repository HEAD and dirty-state
evidence, explicit governance identity, host/tier/model identity, allowed and forbidden
files, acceptance commands, stop conditions, and separate execution, Git, and
external-provider authorizations. A real CLI call requires
`ALLOW_PROVIDER_INVOCATION` in both the packet and runner command; reviewer
authorization is always independent and starts a fresh session.

The canonical schema v3 is one SSOT. Providers receive only its mechanically
extracted `provider_result`; the runner injects controller-owned immutable
provenance and records requested/reported model separately. Reviewer findings
remain candidates until the packet-named adjudicator decides them.

## Capability status

Source and fake-transport tests cover routing schema v2, governance neutrality,
both host contracts, static three-tier mappings, strict result validation,
authorization preflight, timeout/Git/manifest handling, and transactional
no-overwrite distribution.

Established real evidence is narrower: earlier Codex CLI probes preserved JSONL
events and exercised timeout, process-group termination, partial transcripts,
and manifests. The Luna/low Codex-host scout formal runner recheck passed in one
fresh invocation with exit 0, including schema v3, semantic, read-only/mutation,
and manifest validation.

Real smoke proved that the former native Codex scout sandbox did not enforce
read-only in the observed embedded runtime, so that default was retired. Real
rechecks remain pending for native Terra/Sol tasks, both schema-v3 reciprocal
reviewers, and embedded-versus-standalone Codex runtime version skew. Native
per-file sandbox enforcement and a native Plugin Directory package are
unavailable. This project is not a Xinghui Runtime adapter.

## License

[MIT](LICENSE) © 2026 letitia-chiu
