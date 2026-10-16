# Security

## Known issue: overlapping merge resource amplification

The current P2 overlap sweep retains a rectangle index in each covered column.
Its distinct-area guard does not bound this repeated storage for overlapping
rectangles. Attacker-controlled cell snapshots can exhaust the caller process
(CWE-400). A repair and independent review are pending; see
[the handoff](docs/CLAUDE_HANDOFF.md). Do not expose this version to untrusted
workloads within a shared process. No completed security audit is claimed.

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
