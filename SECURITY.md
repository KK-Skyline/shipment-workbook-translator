# Security

## Known issue: overlapping merge resource amplification

The current P2 overlap sweep retains a rectangle index in each covered column.
Its distinct-area guard does not bound this repeated storage for overlapping
rectangles. Attacker-controlled cell snapshots can exhaust the caller process
(CWE-400). A repair and independent review are pending; see
[the handoff](docs/CLAUDE_HANDOFF.md). Do not expose this version to untrusted
workloads within a shared process. No completed security audit is claimed.

## Fixed on branch: quadratic merge member-state evidence

Found during sub-agent review of the overlap repair; it predates that repair
and is outside its budget. In `_snapshot`'s P2 coverage pass, every invalid
non-top-left member of a complete n-cell merge built a separate
`MERGE_MEMBER_STATE_INVALID` candidate carrying all n refs, and all of them
were then ranked: O(n^2) CPU within every existing count/area budget
(CWE-400). Example: a 1x4000 merge whose members all hold `"x"` took about
66 s on the reporting machine.

Commit `1dade92` (branch `fix/merge-member-state-quadratic`, not merged or
released) stops each group at its first invalid member, which is already the
candidate the selector keeps. Error code, phase and `source_cells` are
unchanged, except for one intended difference: large mixed valid/invalid groups
that used to overflow the private evidence arena and return
`INTERNAL_P2_CONTRACT_VIOLATION` with no evidence now return the typed
`MERGE_MEMBER_STATE_INVALID`. Regression evidence and limits are in
[the handoff](docs/CLAUDE_HANDOFF.md). This was checked by a sub-agent review,
not a completed security audit.

This alpha library accepts in-memory cell snapshots. It has no network client,
credential store, workbook reader or service authentication layer.

Adapters must enforce archive/decompression limits, file access boundaries and
formula-cache integrity before calling the core. Services should use process-level
memory/time limits in addition to the parser's own guards. A valid translation
does not certify cargo handling, pallet capacity or physical loading safety.

Use synthetic, minimized reproductions when reporting problems. Do not include
customer data, access tokens or API keys. For sensitive reports, contact the
maintainer through a private channel before opening a public issue. There is
currently no separately staffed security response team or response-time guarantee.
