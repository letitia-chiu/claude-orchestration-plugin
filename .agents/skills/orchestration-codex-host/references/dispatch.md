# Dispatch

Dispatch has two non-interchangeable paths.

## `active_host`

Repository feasibility and implementation remain inside Codex Desktop:

| Tier | Native agent | Default model | Use |
|---|---|---|---|
| scout | `.codex/agents/scout.toml` | `gpt-5.6-luna` | read-only inventory and narrow feasibility |
| worker | `.codex/agents/worker.toml` | `gpt-5.6-terra` | one specified invariant or defect family |
| executor | `.codex/agents/executor.toml` | `gpt-5.6-sol` | cross-module, high-risk, or contractual closure |

Create a distinct Codex Desktop child thread/task for the selected tier and
preserve its thread UUID and actual model identity. The active-host path never
uses the external runner. The PATH `codex` CLI is not the active host.

Do not spawn these agents merely to validate this adapter. Their first real
spawn requires separate smoke authorization.

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

## Prohibited routing

- feasibility or implementation through the external runner;
- an implementer starting its reviewer;
- automatic fallback, retry, model switching, role chaining, or session resume;
- treating a missing model as permission to substitute another model;
- treating host/tier selection as governance or Git authority.

If the selected native tier is unavailable, stop with capability unavailable.
Do not substitute another tier or provider.
