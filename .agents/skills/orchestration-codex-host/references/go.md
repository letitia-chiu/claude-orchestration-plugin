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
existing delta. The branch, HEAD, worktree, authoritative plan SHA, canonical
base, and batch base must exactly match the packet.

Verify:

- host mode is exactly `codex_hosted`;
- active execution host is exactly `codex_desktop`;
- invocation path is exactly `active_host`;
- tier is one of `scout`, `worker`, or `executor`;
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

External provider authorization is also independent. Active-host work must carry
`External-side-effect authorization = NONE`. A reviewer needs a new packet and
new authorization, and both that packet and the external runner command must
carry the exact token `ALLOW_PROVIDER_INVOCATION`.

Conversation memory, a previous packet, a previous session, model capability,
or inferred user intent is never authorization.

Any mismatch, missing field, forbidden-file need, unauthorized Git action, or
scope ambiguity is a hard stop.
