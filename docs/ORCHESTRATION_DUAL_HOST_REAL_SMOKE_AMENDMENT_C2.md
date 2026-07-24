# Dual-Host Recovery — Real-Smoke Amendment C2

Status: architecture amendment authorized after the 2026-07-24
pre-ratification real smoke.

Authority:

- authoritative recovery plan:
  `24df2b57f01c63b0a81050e451ae1a6a5121f2b2`
- failed-smoke candidate:
  `2e2cbf0f36d70e98196f8aa9197390215a03204f`
- smoke evidence:
  `/Users/tzuhsuan/Backups/orchestration-dual-host-smoke-2026-07-24`

This document records only the adjudicated architecture changes. It does not
authorize implementation, real provider invocation, ratification, or release.

## A1. Codex-hosted scout execution

The real smoke established that `.codex/agents/scout.toml` with
`sandbox_mode = read-only` did not create an effective read-only boundary in
the observed Codex Desktop embedded runtime. The write probe succeeded.

The corrected default architecture is:

```text
Codex Desktop remains the active host.

scout:
  invocation_path = host_local_cli
  provider = codex_cli
  profile = codex_read_only
  model = gpt-5.6-luna

worker:
  invocation_path = active_host
  provider = codex_native
  model = gpt-5.6-terra

executor:
  invocation_path = active_host
  provider = codex_native
  model = gpt-5.6-sol
```

`host_local_cli` is explicitly dispatched by Codex Desktop and remains an
active-host local tier. It is not an external reviewer, fallback, or automatic
model switch. It requires independent execution authorization and uses the
runner's read-only mutation detection, transcript, Git evidence, and manifest.
It receives no reviewer, governance, acceptance, adjudication, ratification, or
Git authority.

The Codex Desktop native scout sandbox is no longer a documented safety
boundary.

## A2. Controller-owned provenance

Providers do not output, confirm, endorse, or adjudicate:

```text
governance authority
authorization issuer
acceptance owner
finding adjudicator
final ratifier
host mode
execution host
invocation path
```

The controller and runner construct immutable provenance from the validated
packet and invocation. Providers output only the substantive result:

```text
verdict
summary
evidence
stop_reason
changed_files
tests
repository_state
findings
observations
suggestions
evidence_gaps
```

After validating the provider result, the runner writes the canonical final
artifact as:

```text
provenance + provider_result
```

Provider output cannot rewrite provenance.

## A3. Repository identities

Every formal packet records these identities separately:

```text
Authoritative plan SHA
Release / implementation candidate SHA
Target repository HEAD
Target repository status / dirty-state evidence
```

The plan SHA and plugin or implementation candidate SHA never substitute for
the target repository HEAD. A disposable target may legitimately use three
different SHAs; the packet and runner must validate each in its own domain.
