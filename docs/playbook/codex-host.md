# Codex-host adapter

This is the formal contract for `host_mode = codex_hosted`. Codex Desktop is the
active execution host. Scout is a Desktop-controlled host-local read-only Codex
CLI tier; worker/executor are native Desktop agents. Claude CLI is available
only as a fresh, separately authorized read-only adversarial reviewer.

The adapter does not assign governance:

```text
governance authority
!= Codex Desktop active host
!= Codex host-local scout / native worker / native executor
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
- Native implementation agents:
  - `.codex/agents/worker.toml`
  - `.codex/agents/executor.toml`
- Host-local scout: `scripts/orchestration_agent.py` resolving
  `host_local_cli / codex_cli / codex_read_only / gpt-5.6-luna`
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
another repository. From the plugin root, materialize the fixed 20-file
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
| inventory, location, narrow feasibility | scout | `gpt-5.6-luna` | CLI profile | runner-enforced read-only plus Git mutation evidence | evidence only; no implementation |
| specified implementation with one invariant or defect family | worker | `gpt-5.6-terra` | medium | workspace-write | bounded implementation and authorized tests |
| cross-module, contractual, security, persistence, or otherwise high-risk work | executor | `gpt-5.6-sol` | high | workspace-write | complete authorized invariant and defect-class closure |

The task packet must select the tier and exact model. A model override must be
explicit and project-local. Missing or unavailable models fail closed: there is
no automatic fallback, retry, model switching, or role chaining. A higher tier
never receives extra file, Git, governance, acceptance, adjudication, or
ratification authority.

Codex Desktop explicitly dispatches scout through the target-local runner with
independent `ALLOW_HOST_LOCAL_CLI_INVOCATION` authorization. The CLI is the
local tier execution mechanism; the PATH Codex CLI is not the active host, a
reviewer, or a fallback.
Worker/executor use distinct native Desktop child tasks.

Real smoke showed that `.codex/agents/scout.toml` with
`sandbox_mode = read-only` did not enforce a read-only boundary in the observed
embedded runtime; the file and misleading default were retired.
Native per-file sandbox enforcement remains unavailable.

## Gate flow

1. `kickoff` reads the exact authoritative plan identity, collects the five
   governance identities plus host/tier/model/worktree identities, and
   materializes the C2 packet. It stops as unauthorized.
2. `go` separately validates authoritative plan SHA, release/implementation
   candidate SHA, target repository HEAD, target dirty-state evidence, current
   authorization, tier/model, allowed and forbidden files, tests, and stop
   conditions. Execution authorization and Git authorization remain separate.
3. `dispatch` sends feasibility to the exact host-local CLI scout tuple and
   implementation to native worker/executor.
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

The controller has already supplied immutable provenance. The reviewer produces
only the substantive `provider_result`; it does not infer, modify, confirm, or
adjudicate authority metadata. The runner mechanically selects the
`adversarial_reviewer` provider definition from the canonical schema-v3 SSOT,
records requested/reported model separately, and writes
`provenance + provider_result`.

The runner starts at most one fresh Claude CLI process. The reviewer cannot
modify the repository, repair findings, dispatch a host or another role, or
claim governance, acceptance, adjudication, or ratification authority. It
returns candidate findings, observations, suggestions, and evidence gaps.
Only the packet-named finding adjudicator may adjudicate candidates.

Active-host evidence and external-review evidence remain separate. A Codex
Desktop implementation report has no external runner manifest; record
`not applicable`, not a fabricated receipt.

## Pending real evidence

The C2 targeted recheck preserved these established results: host-local Luna
read-only enforcement and zero Git delta, native Terra/Sol success, and
schema-v3 Claude/Codex reviewer success. Luna's substantive result alone failed
because the then-common transport exposed reviewer collections to a feasibility
role and the model populated them.

The canonical schema now contains separate feasibility, implementation, and
reviewer transport definitions. Feasibility inventory is expressed only through
`summary` and `evidence`; reviewer fields are rejected rather than ignored or
converted.

- real Luna CLI scout: one independently authorized confirmation remains pending.
- real Terra worker and Sol executor native tasks: preserved PASS evidence; no C3 rerun is required.
- schema-v3 Claude and Codex reviewers: preserved PASS evidence; no C3 rerun is required.
- runtime version-skew behavior: remains an explicit compatibility caveat.

Treat embedded/standalone version skew as behavioral evidence, not binary
parity, and do not claim final ratification from static tests.
