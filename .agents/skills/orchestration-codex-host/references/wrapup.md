# Wrap-up

Keep active-host evidence and external-review evidence in separate sections.
Never manufacture one from the other.

## Active-host evidence

Record:

- authority identity and authoritative plan identity;
- current control-window authorization;
- Codex Desktop host thread UUID;
- native child thread/task UUID, or host-local CLI session ID for scout;
- selected tier, configured model, and actual model evidence;
- exact worktree, pre/post branch, HEAD, status, and ancestry;
- changed files and diff scope;
- every acceptance command and actual result;
- Git authorization and every Git action taken;
- deviations, unsupported capabilities, and evidence gaps;
- host-local scout transcript/Git evidence/manifest, or `not applicable` for
  native worker/executor.

Record requested and CLI-reported model separately. The native scout sandbox is
not an accepted safety boundary; mark the corrected Luna CLI recheck `pending`
until independently authorized and executed.

## External-review evidence

Only after independent review authorization, record separately:

- reviewer authorization identity and packet identity;
- Claude CLI session identity, exact model, transcript, and manifest;
- pre/post read-only Git evidence;
- candidate findings, observations, suggestions, and evidence gaps;
- the packet-named finding adjudicator;
- adjudication status for each candidate finding.

The canonical final artifact records controller-owned immutable provenance
separately from the provider's substantive result. Never ask the reviewer to
confirm or endorse provenance.

The reviewer does not close findings by assertion and cannot become the
acceptance owner or final ratifier.

## Authorization footer

Every wrap-up defaults all continuation to NO:

```text
NEXT IMPLEMENTATION AUTHORIZED: NO
EXTERNAL REVIEW AUTHORIZED: NO
REAL SMOKE AUTHORIZED: NO
COMMIT AUTHORIZED: NO
PUSH / PR / MERGE AUTHORIZED: NO
```

Change a value only when the current control window explicitly authorizes that
exact next action. Stop after reporting.
