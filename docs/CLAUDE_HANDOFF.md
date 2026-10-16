# Claude implementation and independent review handoff

Prepared: 2026-10-16. Status: known issue open; core source not patched.

## Purpose and ownership

The owner authorized publishing this MIT alpha snapshot with its known issue
disclosed, handing code remediation to Claude and independent verification to
Claude Review. Do not confuse publication, passing smoke tests, or this document
with a completed security review. The implementing agent must supply a patch;
the reviewing agent must independently assess it and its regression evidence.

## Exact scope

This repository is a standalone extraction of a shipment translator. Its public
entry accepts in-memory `RawCell` snapshots; no XLSX adapter, cloud API, desktop
UI, container solver, customer workbook or private runtime material is included.

- Core: `shipment_translator/translator.py`.
- Input model: `shipment_translator/models.py`.
- Public exports: `shipment_translator/__init__.py`.
- Synthetic public example: `examples/basic.py`.
- Standalone tests: `tests/test_public_api.py`.
- Interface and limits: `README.md`, `docs/INTERFACE.md`, `SECURITY.md`.

Entry core SHA-256:
`c6a6f8e569b5f848ec1a42161af2c86fe33975eb2453c4fc5045d62cff3ddde5`.
Only the input-model import changed during extraction (line endings were normalized
by patching). The original private application was not modified for this release.
Freeze current file hashes and the Git revision before implementation.

## Verified issue: P2 merge-overlap resource amplification

Classification: CWE-400; medium severity; high confidence in the static trace.
Attack surface: caller-controlled `RawCell.merged_cell_info`.
Impact: excessive CPU/memory in the integrating Python process, potentially
`MemoryError`. No remote service or actual production exploitation is established.

Relevant entry-snapshot locations in `shipment_translator/translator.py`:

- `_snapshot`, around line 4360: public input validation.
- Around 4580–4601: rectangle count, individual area and distinct union-area gates.
- Around 4643–4693: overlap sweep and `active_by_column` sets.
- Around 4698 onward: overlap candidates, then coverage checks.
- Around 7054: resource exceptions including `MemoryError` propagate.

Root cause: the guards bound geometric union area, but the sweep retains each
rectangle's index in every column it covers. Many overlapping rectangles can
have a small union while their total column-membership count is enormous.
Disjoint-set component tracking reduces some comparisons but does not eliminate
the repeated storage or the width loops. Missing coverage is detected too late.

Static stress family, not executed at dangerous scale:

1. One sheet, 50,000 ordinary string cells at rows 1..4, columns 1..12500.
2. For cell `(r,c)`, declare a rectangle with start
   `(1, max(1,c-8192))`, end `(r, min(16384,c+8191))`; top-left equals start.
3. All 50,000 spans are distinct, non-singleton, within coordinate bounds,
   and contain their declaring cell. Input cell count is below 200,000.
4. Each rectangle and the union have area at most 65,536, passing the area
   guards; the rectangle-count guard permits exactly 50,000.
5. All rectangles start on row 1, so none expire during insertion. Each has
   width at least 8,192, giving at least 409,600,000 retained set memberships.
6. Declarations are intentionally inconsistent as a workbook; the parser must
   reject them safely before that inconsistency causes disproportionate work.

Do not run this full input without a separately constrained disposable process.
Use small synthetic witnesses and deterministic operation/allocation counters.

## Implementation task

Repair the shared merge resource boundary before expensive column-membership
allocation. Prefer the smallest correct change, for example a cumulative work
budget covering repeated rectangle-column memberships, or a bounded overlap
algorithm. Establish the budget's invariant from its actual downstream consumers.
Counting only union area or only rectangle count is insufficient.

If choosing an additional budget, explicitly document its value, units, failure
code, phase and precedence. Distinct valid non-overlapping inputs within the
existing limits must remain accepted. For malformed inputs, preserve exact error
ordering/evidence where possible; explain any intentional resource-precedence
change instead of silently modifying a test expectation. Do not invent an
absent historical contract to justify semantics.

Keep the repair within the core, regression tests and related documentation.
Do not redesign profile handling, change accepted business values, relax provenance
checks, add unrelated dependencies, or patch the original private product.

## Tests and anti-false-green requirements

1. Add an independent synthetic witness through `translate_shipment_workbook`.
   Show the current failure of the intended work bound before applying the fix.
   Bound test time/memory; a test must not exhaust the developer machine.
2. Establish that the new rejection happens before the expensive sweep. Check
   observed work or allocations, not just an eventual typed error or elapsed time.
3. Cover just-below/at/above the selected work threshold; if threshold tests need
   an internal seam, pair them with a real public-entry case.
4. Keep valid disjoint merges, ordinary vertical merges, top-left provenance and
   simple non-merged translation correct. Add input-permutation checks for
   deterministic failure/evidence.
5. Freeze tests, temporarily remove the new guard or restore the expensive path,
   demonstrate RED, restore exact GREEN source hash, then rerun binding tests.
6. Preserve all nine current tests; no skip/xfail, weakened assertions, mocked
   public translator, or expectations generated from production lookup tables.
7. Run `python -B -m unittest discover -s tests -v` and
   `python -B -m examples.basic`. Report actual exits/counts, test additions,
   mutation evidence and final hashes. CI covers Python 3.11–3.14; report its
   actual state rather than assuming it passed.

Claude Review must trace the fix independently from public input to allocation,
verify the work bound under overlapping/incomplete declarations and confirm that
the test would detect a regression. Distinguish a bounded rejection from a later
failure after costly allocation. Do not sign off from green test counts alone.

## Security-plugin and privacy state

Codex Security was invoked, preflight passed with a worker-capacity warning, and
an independent static auditor confirmed the resource issue above. Its canonical
report checkpoint failed with:

`Scan output parent must not be group- or world-writable without the sticky bit.`

This is a local report-storage permissions problem, separate from the code bug.
No completed/sealed audit report exists. Do not claim the plugin passed or report
zero vulnerabilities. Repair scan storage using its supported configuration or
owner-controlled directory; do not loosen filesystem protections just to finish.

Publication privacy checks covered the 14 initial release files with source
inspection and all-file patterns for provider keys, private keys, emails, private
paths and known customer markers: none were found. Examples are synthetic. This
handoff adds no customer input or credentials. The large module's intermediate
business/provenance sections have not received a complete manual security audit.
Never read or upload the original private repository as part of this bounded task.

## What is already verified

- Nine standalone public-API tests passed on the current local Linux Python.
- The synthetic canonical example translated one row into two cartons.
- An isolated Windows Python 3.14 build/install/import check succeeded.
- No dependency on the original application's package directories is required.
- Historical private-project test totals and contract bundles are not part of
  this release and must not be presented as its conformance evidence.

After a verified repair, update the known-issue sections to reference the fixing
commit and review evidence. Retain the historical finding accurately. Broader
conformance, a general XLSX adapter and solver integration are separate work.
