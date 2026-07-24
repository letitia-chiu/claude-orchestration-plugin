# Go authorization gate

`go` is a fail-closed validation step. It validates authorization; it does not
create or broaden it.

## Exact identity checks

Before work, verify and record:

```bash
git -C "<worktree>" status --short -uall
git -C "<worktree>" branch --show-current
git -C "<worktree>" rev-parse HEAD
```

The worktree must be clean unless the packet explicitly names and accepts the
existing delta. Verify three independent identities without substitution:

1. authoritative plan SHA;
2. plugin/release implementation candidate SHA;
3. target repository HEAD plus exact status/dirty-state evidence (`CLEAN`, or
   the controller-produced `sha256:<digest>` of exact
   `git status --short --untracked-files=all` UTF-8 bytes).

The plan or plugin candidate SHA must never stand in for the target HEAD.

Verify:

- host mode is exactly `codex_hosted`;
- active execution host is exactly `codex_desktop`;
- invocation path is `host_local_cli` for scout and `active_host` for
  worker/executor;
- scout resolves exactly to
  `codex_cli / codex_read_only / gpt-5.6-luna / reasoning_effort=low`;
- scout packet, routing, and runner CLI all explicitly agree on `low`; missing
  effort, `medium`, `high`, or the UI label `Light` fails before spawn;
- worker/executor resolve to their native Desktop agents;
- model matches the selected agent definition or an explicit packet-authorized
  project-local override;
- tier responsibility matches task risk;
- allowed and forbidden files are explicit and non-conflicting;
- acceptance commands and stop conditions are executable and unambiguous;
- current authorization covers this exact Gate and no later Gate.

## Separate authorities

Execution authorization and Git authorization are independent. Implementation
permission does not imply permission to commit, push, open a pull request,
merge, amend, rebase, tag, or switch branches. Apply only the exact Git action
named in `Git authorization`; `NONE` means no Git writes.

Host-local scout execution and external provider review are independent.
Scout requires `Host-local execution authorization =
ALLOW_HOST_LOCAL_CLI_INVOCATION` in packet and runner CLI while
`External-side-effect authorization = NONE`. A reviewer instead needs a new
packet and `ALLOW_PROVIDER_INVOCATION` in both packet and external runner CLI.
Neither token authorizes the other path.

Conversation memory, a previous packet, a previous session, model capability,
or inferred user intent is never authorization.

Any mismatch, missing field, forbidden-file need, unauthorized Git action, or
scope ambiguity is a hard stop.
