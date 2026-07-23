# Codex-host adapter

This is the formal contract for `host_mode = codex_hosted`. Codex Desktop is the
active execution host. Its host-local tiers are Codex-native agents; Claude CLI
is available only as a fresh, separately authorized read-only adversarial
reviewer.

The adapter does not assign governance:

```text
governance authority
!= Codex Desktop active host
!= Codex-native scout / worker / executor
!= Claude CLI external reviewer
```

Every task packet names the governance authority, authoritative plan,
authorization issuer, acceptance owner, finding adjudicator, and final ratifier.
The current explicit packet and authorization are the only authority sources.
Host selection, model capability, conversation memory, prior success, and
reviewer opinion do not grant authority.

## Formal surfaces

- Root binding: `AGENTS.md`
- Workflow entry: `.agents/skills/orchestration-codex-host/SKILL.md`
- Native agents:
  - `.codex/agents/scout.toml`
  - `.codex/agents/worker.toml`
  - `.codex/agents/executor.toml`
- Shared routing: `docs/playbook/agent-routing.json`
- Gate packet: `examples/task-packets/codex-host-gate.md`
- External transport: `scripts/orchestration_agent.py`

No project-local `.codex/config.toml` is needed for this adapter. Agent
discovery uses the repository-local `.codex/agents` surface established by
feasibility. The adapter does not install or modify global configuration, a
daemon, or a hook, and it never automatically allows external provider
invocation.

## Target-project installation

The adapter files in the plugin checkout are not automatically installed in
another repository. From the plugin root, materialize the fixed 21-file
inventory into an explicit target Git root:

```bash
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository
python3 scripts/init_codex_host.py \
  --target /absolute/path/to/target-repository \
  --check
```

The target must exist, be an absolute path, and resolve to a Git repository.
Installation is transactional and no-overwrite: missing files are copied,
identical files are not rewritten, and any different file aborts the entire run
before writes. A different `AGENTS.md` requires a repository-owner manual
merge. Updates preserve project-local customization by reporting a conflict
instead of overwriting it. The materializer does not write global
configuration, invoke a provider, or perform Git writes. It is not a native
Codex Plugin Directory package.

## Risk-to-tier matrix

| Risk / task shape | Tier | Default model | Reasoning | Sandbox | Ownership |
|---|---|---|---|---|---|
| inventory, location, narrow feasibility | scout | `gpt-5.6-luna` | low | read-only | evidence only; no implementation |
| specified implementation with one invariant or defect family | worker | `gpt-5.6-terra` | medium | workspace-write | bounded implementation and authorized tests |
| cross-module, contractual, security, persistence, or otherwise high-risk work | executor | `gpt-5.6-sol` | high | workspace-write | complete authorized invariant and defect-class closure |

The task packet must select the tier and exact model. A model override must be
explicit and project-local. Missing or unavailable models fail closed: there is
no automatic fallback, retry, model switching, or role chaining. A higher tier
never receives extra file, Git, governance, acceptance, adjudication, or
ratification authority.

Codex Desktop should create a distinct child thread/task for the selected native
agent and record its UUID and actual model. The PATH Codex CLI is not the active
host and must not be used to emulate one.

`sandbox_mode` establishes the agent-level filesystem mode. Allowed and
forbidden file lists remain packet contracts verified by instructions, tests,
and pre/post Git evidence; native per-file sandbox enforcement is not available.

## Gate flow

1. `kickoff` reads the exact authoritative plan identity, collects the five
   governance identities plus host/tier/model/worktree identities, and
   materializes the common 27-field packet. It stops as unauthorized.
2. `go` validates exact worktree, branch, HEAD, plan/base identities, current
   authorization, tier/model, allowed and forbidden files, tests, and stop
   conditions. Execution authorization and Git authorization remain separate.
3. `dispatch` sends feasibility/implementation only to the selected
   Codex-native tier. Active-host work never starts the external runner.
4. `wrapup` records active-host evidence independently and defaults every next
   authorization to NO.

The implementer cannot dispatch a reviewer. There is no automatic fallback,
retry, provider switching, session resume, or role chaining.

## Claude reviewer handoff

An external review requires a new control-window authorization and a new
`adversarial_reviewer` packet:

```text
host_mode = codex_hosted
active_host = codex_desktop
invocation_path = external_cli
provider = claude_cli
profile = claude_read_only
host_tier = null
```

The packet and runner command must independently carry the same explicit token:

```text
External-side-effect authorization = ALLOW_PROVIDER_INVOCATION
--external-authorization ALLOW_PROVIDER_INVOCATION
```

The runner starts at most one fresh Claude CLI process. The reviewer cannot
modify the repository, repair findings, dispatch a host or another role, or
claim governance, acceptance, adjudication, or ratification authority. It
returns candidate findings, observations, suggestions, and evidence gaps.
Only the packet-named finding adjudicator may adjudicate candidates.

Active-host evidence and external-review evidence remain separate. A Codex
Desktop implementation report has no external runner manifest; record
`not applicable`, not a fabricated receipt.

## Pending real evidence

Static adapter implementation is not runtime smoke evidence. The following
remain pending a later, independently authorized smoke batch:

- real Luna, Terra, and Sol native agent spawning;
- three distinct child thread UUIDs and actual model identities;
- scout read-only sandbox precedence;
- embedded Codex Desktop and standalone CLI runtime parity;
- a real fresh Claude CLI read-only reviewer result;
- runtime proof for allowed/forbidden-file behavior beyond the available
  agent-level sandbox.

Do not claim these capabilities have passed until the later smoke artifacts
exist.
