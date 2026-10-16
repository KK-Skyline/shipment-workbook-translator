# Security

## Overlapping merge resource amplification (CWE-400): patched, review pending

Through release snapshot `acb8996`, the P2 overlap sweep retained a rectangle
index in each covered column. Its distinct-area guard did not bound this
repeated storage for overlapping rectangles, so attacker-controlled cell
snapshots could exhaust the caller process.

Commit `fdfb238` adds a workbook-wide budget of 200,000 rectangle-column
memberships (the summed widths of syntactically computable merge rectangles).
Inputs above it fail with `RAW_MERGE_BUDGET_EXCEEDED` in the P2 resource
preflight before the sweep allocates anything. Non-overlapping declarations
within the existing union-area limit are unaffected. A sub-agent review found
no defect in this patch; independent Claude Review is still pending. See
[the handoff](docs/CLAUDE_HANDOFF.md).

## Open: quadratic merge member-state validation (CWE-400)

This issue exists in the code before and after `fdfb238`, and the membership
budget does not cover it. In one fully covered merge, every non-top-left member
holding a value emits its own `MERGE_MEMBER_STATE_INVALID` candidate. Each
candidate carries the whole member list as evidence, so candidate construction
and selection are O(n²) in the member count. About 1,000 members already cost
several seconds of CPU, and the input stays within all count and area limits.
Overlong merge range strings can also make A1 parsing slow. Do not expose this
version to untrusted workloads in a shared process. No completed security audit
is claimed, and process-level limits remain recommended.

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
