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
within the existing union-area limit are unaffected. Independent review of the
patch is still pending; see [the handoff](docs/CLAUDE_HANDOFF.md). No completed
security audit is claimed, and process-level limits remain recommended.

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
