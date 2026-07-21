---
name: python-runtime-contract-audit
description: Audit and close Python runtime contract boundaries when type annotations, dataclasses, Protocols, callbacks, evidence objects, persistence gates, enums, tuples, mappings, or frozen models affect correctness, trust, authorization, or invariants. Use before implementation planning, after any type-boundary finding, and before high-risk final review.
---

# Python Runtime Contract Audit

## Purpose

Python annotations describe intent; they do not enforce runtime behavior. A frozen dataclass prevents field reassignment, not mutation through nested lists, dictionaries, sets, or aliased objects.

Use this skill whenever a Python change relies on any of the following as a correctness or trust boundary:

- dataclass fields, especially `frozen=True`
- `Protocol` methods or callbacks
- booleans used to authorize, commit, persist, deliver, or attest
- enum discriminators
- tuple or mapping immutability
- receipts, evidence, claims, traces, intents, identities, capabilities, or persistence probes
- invariant or gate claims
- a review finding involving wrong runtime types, truthiness, aliasing, or mutable containers

This skill is an audit workflow, not a general demand to add runtime validation everywhere. Apply it to contract-bearing surfaces where malformed values can change behavior or invalidate an invariant.

## Non-negotiable rules

1. **Annotations are not enforcement.** Never treat `x: bool`, `kind: SomeEnum`, `items: tuple[...]`, or `payload: Mapping[...]` as proof that wrong runtime values are impossible.
2. **Frozen is shallow.** Never treat `@dataclass(frozen=True)` as proof of deep immutability.
3. **External booleans require exact validation.** Any value returned across a `Protocol`, callback, adapter, deserializer, fixture boundary, or plug-in seam must satisfy `type(value) is bool` before it controls a gate. Do not use truthiness first.
4. **A finding is a defect class, not a line item.** When one wrong-type, truthiness, enum, tuple, mapping, or aliasing bug is found, inventory every same-class boundary in the authorized scope before editing.
5. **Fail closed at trust boundaries.** Invalid external values must not authorize, attest, commit, deliver, or claim success.
6. **Construction-time validity for contract objects.** A successfully constructed contract object should already satisfy its field invariants. Do not rely on a later verifier to guess what malformed fields meant.
7. **No silent coercion at identity-bearing boundaries.** Do not repair identifiers with `.strip()`, convert arbitrary iterables with `tuple()`, convert arbitrary values with `bool()`, or accept enum value strings unless the contract explicitly defines a parser outside the core object.
8. **Tests must cover the surface, not only reported examples.** A regression test for the exact reviewer payload is necessary but insufficient.

## Step 1 — Classify the risk

Treat the audit as mandatory when malformed values can affect:

- authorization or capability checks
- honesty, evidence, receipts, completion claims, or future commitments
- persistence or durable-state claims
- message delivery or tool execution
- identity selection
- security, privacy, or isolation boundaries
- records that are expected to remain immutable after creation

For ordinary internal data holders with no trust or invariant role, record that runtime enforcement is intentionally out of scope rather than mechanically validating everything.

## Step 2 — Build the contract surface inventory before editing

Enumerate the authorized production scope and list:

- every dataclass and every field
- every enum-bearing field
- every bool-bearing field
- every tuple, mapping, list, set, or nested payload field
- every `Protocol` method and callback return value
- every external value used in `if value`, `if not value`, `bool(value)`, enum dispatch, delivery, persistence, or verdict construction

Produce a compact matrix with these columns:

```text
owner
field or method
semantic category
exact accepted runtime type
None allowed?
canonical-value rule
immutability / snapshot strategy
invalid-input behavior
covering test
```

For high-risk contract modules, add a meta-test that compares `dataclasses.fields()` against the inventory so new fields cannot bypass review silently.

## Step 3 — Generalize every finding

Before applying a fix, write the defect family:

```text
Observed instance:
General defect class:
Same-class search scope:
All matches found:
Chosen shared rule:
Tests proving class closure:
```

Examples:

- `Receipt.success="false"` is not only a Receipt bug. The class is **external bool values accepted through truthiness**. Search every callback and Protocol bool boundary.
- `required_tool_names` accepts a list. The class is **mutable or wrong-type containers accepted by frozen contract objects**. Search every sequence and mapping field.
- `kind="final_message"` is accepted. The class is **string values impersonating enum discriminators**. Search every enum field and dispatch branch.
- mutating the source payload changes later delivery. The class is **mutable alias retained across a contract boundary**. Search every nested container and store snapshot path.

Do not mark the finding closed until all authorized same-class matches are either fixed or explicitly documented as intentionally out of scope with rationale.

## Step 4 — Apply runtime rules consistently

Prefer small centralized validators with field-aware errors, for example:

```python
def require_exact_bool(value: object, field_name: str) -> bool: ...
def require_exact_enum(value: object, enum_type: type, field_name: str): ...
def require_canonical_text(value: object, field_name: str) -> str: ...
def require_canonical_ref(value: object, field_name: str) -> str: ...
def require_exact_datetime(value: object, field_name: str): ...
def require_tuple_of(value: object, item_validator, field_name: str) -> tuple: ...
def freeze_json_mapping(value: object, field_name: str): ...
```

Rules:

- use `type(value) is bool` for strict booleans
- validate external boolean results before branching; invalid values fail closed
- require actual enum members where the contract says enum; parsing strings belongs at an adapter boundary
- distinguish `TypeError` for wrong runtime type from `ValueError` for invalid value
- reject leading or trailing whitespace in opaque identifiers rather than silently normalizing it
- require exact tuple when tuple is the public contract, unless conversion is explicitly documented and safely copies ordered input
- never accept unordered containers where order is meaningful
- recursively freeze or snapshot nested payloads when post-construction immutability is part of the contract
- verify both source-alias mutation and mutation through the exposed object

## Step 5 — Test by invalid family

For every applicable field category, cover families rather than one reviewer example.

### Boolean

```text
True, False
"true", "false"
0, 1, 0.0, 1.0
[], [False], {}, (), None, object()
```

Only exact `True` and `False` are valid booleans.

### Enum

```text
enum member (valid)
enum.value string
enum.name string
member of another Enum
None, 0, object()
```

### Tuple / immutable sequence

```text
tuple (valid)
list, set, generator, dict, str, None
source-container mutation after construction
```

### Canonical text or reference

```text
valid ASCII and non-ASCII text
None, non-string
"", " ", "\t", "\n"
" value", "value "
```

### Datetime

```text
valid datetime
None, string timestamp, int, float, dict, object()
```

### Mapping / nested payload

```text
valid allowed scalar and nested values
list or string in place of mapping
non-string keys where prohibited
nested mutable list and dict
set, generator, bytes, custom object where prohibited
source alias mutation
mutation through exposed value
```

Also prove valid end-to-end flows still work. Rejection-only tests are not sufficient.

## Step 6 — Separate implementation ownership from adversarial review

For one invariant or contract family, keep the production change, inventory, validators, and boundary tests under one implementation owner and one context. Do not split those across parallel workers.

Parallelize only work that is genuinely independent, such as unrelated modules or mechanical documentation after the contract is settled.

The adversarial reviewer must remain read-only and independent. The model that fixes a finding must not be the sole final reviewer of that same finding.

## Step 7 — Acceptance evidence hierarchy

A green test count is supporting evidence, not closure by itself. Require all four layers:

1. **Inventory evidence** — every contract field and external return boundary is accounted for.
2. **Class-closure evidence** — the reported defect was generalized and all same-class matches were resolved or explicitly excluded.
3. **Mutation / adversarial evidence** — wrong types, truthiness, aliasing, and nested mutation probes were run.
4. **Regression evidence** — full project gate passes and valid end-to-end behavior remains intact.

A report that supplies only layer 4 is incomplete for a high-risk runtime contract change.

## Step 8 — Review-loop stop rule

After any external NO-GO:

1. classify each finding by defect family
2. check whether it is a new family or a missed member of a previously known family
3. if it is a missed member, do not issue another narrow patch order; reopen the family inventory
4. run one internal adversarial pass before spending another external-review call
5. allow one fresh-context external review after local class closure
6. if the same defect family returns again, stop the loop and escalate the methodology or ownership rather than issuing another line-item patch

## Required report

Return:

```text
Conclusion
Contract inventory summary
Defect families found
Same-class matches and disposition
Files changed
Boundary tests added
Valid-path regression checks
Remaining exclusions / assumptions
Commands run with actual results
```

Never claim a gate or invariant is complete merely because the existing test suite is green.
