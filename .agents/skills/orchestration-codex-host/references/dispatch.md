# Dispatch

Dispatch has two non-interchangeable paths.

## Active-host local tiers

Codex Desktop controls both paths, but their execution mechanisms differ:

| Tier | Invocation | Provider/profile | Default model | Use |
|---|---|---|---|---|
| scout | `host_local_cli` | `codex_cli / codex_read_only` | `gpt-5.6-luna / low` | read-only inventory and narrow feasibility |
| worker | `active_host` | `.codex/agents/worker.toml` / `codex_native` | `gpt-5.6-terra` | one specified invariant or defect family |
| executor | `active_host` | `.codex/agents/executor.toml` / `codex_native` | `gpt-5.6-sol` | cross-module, high-risk, or contractual closure |

Scout requires both packet and runner CLI to carry
`ALLOW_HOST_LOCAL_CLI_INVOCATION`; its packet must keep external provider
authorization at `NONE`. It uses runner mutation detection, transcript, Git
evidence, and manifest, but remains an active-host local tier—not a reviewer,
fallback, or source of governance authority. The native scout TOML was retired
because its observed sandbox did not enforce read-only.

The controller pins scout reasoning effort to the CLI value `low`. The runner
passes `-c model_reasoning_effort=low`, ignores user config for that child, and
fails before spawn if packet, routing, or caller differs. `Light` is a UI label,
not the CLI value. No global default may silently upgrade scout effort.

Before spawning the scout, the runner validates the complete controller packet
and saves it as `task.md`. It then extracts exactly one section delimited by
`BEGIN/END PROVIDER SUBSTANTIVE TASK`, prepends the
`substantive_only` phase contract, saves that prompt as `provider-task.md`, and
sends only that file to Luna. Missing, duplicate, empty, reversed, or
controller-identity-bearing sections fail before spawn. The provider therefore
cannot be tasked with revalidating plan/candidate/governance identity while the
full packet remains available for audit.

Worker/executor use distinct Codex Desktop child tasks; preserve thread UUID and
actual model identity. The PATH Codex CLI is not the active host.

## `external_cli`

The only Codex-hosted external role is an adversarial reviewer:

```text
provider = claude_cli
profile = claude_read_only
role = adversarial_reviewer
```

It must use a fresh, independent reviewer packet and fresh session. The
implementation packet cannot authorize it. Before one external process may be
started, both locations must carry the exact token:

1. packet: `External-side-effect authorization = ALLOW_PROVIDER_INVOCATION`
2. runner CLI: `--external-authorization ALLOW_PROVIDER_INVOCATION`

The Claude CLI reviewer is read-only. It may return candidate findings,
observations, suggestions, and evidence gaps. It may not modify the repository,
start another role, adjudicate findings, accept the implementation, or ratify a
release.

Invoke the reviewer from the target repository root with the target-installed
`scripts/orchestration_agent.py` and
`docs/playbook/agent-routing.json`. The runner mechanically extracts
the role-specific reviewer transport from the target-local canonical
`examples/schemas/orchestration-result.schema.json`; the provider never
receives or echoes controller-owned provenance. Feasibility and implementation
select their own narrower definitions from that same SSOT. The runner rejects
fields outside the selected role before lossless empty-field normalization and
then creates canonical `provenance + provider_result` output. No
plugin-checkout path is part of the invocation.

## Prohibited routing

- feasibility through any path except the exact Codex-hosted scout
  `host_local_cli` tuple;
- worker/executor implementation through the external runner;
- an implementer starting its reviewer;
- automatic fallback, retry, model switching, role chaining, or session resume;
- treating a missing model as permission to substitute another model;
- treating host/tier selection as governance or Git authority.

If the selected native tier is unavailable, stop with capability unavailable.
Do not substitute another tier or provider.
