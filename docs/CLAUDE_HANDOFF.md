# Claude implementation and independent review handoff

Prepared: 2026-10-16. Status: core patched in `fdfb238` (see "Repair record"
below); independent Claude Review pending; not released.

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

## Repair record (2026-10-16, implementing agent: Claude Code)

Baseline: Git `acb89969be078636eb5eb213b3c07ede188d1c67`, `translator.py`
SHA-256 `c6a6f8e5…ddde5` (matches the entry hash above). Fix commit:
`fdfb238e5983150a1d9675b22143268438c02881` on branch
`fix/merge-membership-budget` (not merged, not pushed, not released).
Patched `translator.py` SHA-256:
`b0708b1dca5c959c67bed04557a37c75b58fb807bccb6d24b8707782744d6616`.
`translator.py` keeps its mixed CRLF/LF line endings; the patch touches no other lines.

### Change

`_snapshot` adds one condition to the existing count/per-rectangle-area gate:
the sum of `end_column - start_column + 1` over the deduplicated, syntactically
computable `budget_rectangles` must not exceed 200,000.

- Units: rectangle-column memberships, workbook-wide across all sheets.
- Consumer invariant: the overlap sweep is the only P2 consumer whose work
  depends on rectangle width (its join walk, `active_by_column` insertion and
  expiry each visit every column of every swept rectangle). Swept rectangles
  are a subset of `budget_rectangles`, so stored memberships and column visits
  are each at most 200,000. Coverage expansion is bounded separately by the
  member cells, which come from the at most 200,000 input cells.
- Value: for pairwise-disjoint rectangles, summed width <= summed area ==
  union area <= 200,000 (the existing union-area gate). No non-overlapping
  declaration set that previously passed the area gates is newly rejected; a
  test covers the extreme valid case (25,000 complete 1x8 merges, union and
  memberships both exactly 200,000, P2 accepted).
- Failure: existing `RAW_MERGE_BUDGET_EXCEEDED` (P2, rank 4, scope `workbook`,
  field `RESOURCE_MERGE_AREA`, no source cells). Phase: P2 resource preflight,
  before `merge_groups`, the overlap sweep and coverage.

### Precedence change

Affected inputs are only declaration sets whose summed width exceeds 200,000
while passing the earlier gates; such sets necessarily overlap, or contain
locally invalid rectangles that already fail P2. They previously returned a P2
semantic code (normally `MERGE_RANGE_OVERLAP`, rank 7) after the costly sweep,
or exhausted memory. They now return `RAW_MERGE_BUDGET_EXCEEDED`. Against the
P2 rank order this matches ranks 5–11. For ranks 1–3 (`CELL_ERROR`,
`MERGE_SCHEMA_INVALID`, `MERGE_RANGE_INVALID`) it follows the precedent of the
existing area gates, which already return before those collected candidates. A
regression test confirms the pre-fix area gate behaves this way. Inputs at or
below the budget keep their previous result and evidence.

### Tests (`tests/test_merge_budget.py`, 10 new; the 9 original tests unchanged)

Public-entry witnesses with expectations derived from input geometry. The test
counts sweep work with `sys.setprofile` (heap pushes from `_snapshot`,
`component_root` calls) and measures peak allocations with `tracemalloc`.
Coverage: scaled handoff family (2x13 cells, 213,148 memberships, union
16,408); thresholds 199,999 / 200,000 / 200,001, with a positive control showing
that the instrument sees the sweep at 200,000; workbook-wide two-sheet total;
four input permutations for the budget failure and for overlap evidence;
precedence against the existing area gate; incomplete in-budget declarations
keep `MERGE_COVERAGE_INCOMPLETE`; valid vertical/horizontal merges keep the
canonical bytes; vertical-merge members carry top-left authority; and the
maximal valid P2 load.

Observed counters on CPython 3.14.3 (Windows):

| Witness | Before (`acb8996`) | After (`fdfb238`) |
| --- | --- | --- |
| handoff 2x13 | `MERGE_RANGE_OVERLAP`, 26 pushes, 205,020 lookups, peak 18.8 MB | budget error, 0, 0, peak 82 KB |
| 200,001 | `MERGE_RANGE_OVERLAP`, 25, 191,859, 18.8 MB | budget error, 0, 0, 66 KB |
| 200,000 | `MERGE_RANGE_OVERLAP`, 25, 191,858, 18.8 MB | unchanged |

The full-scale handoff input (about 409.6 million memberships) was not run.

### RED/GREEN evidence

- New tests against unpatched `acb8996` source: 10 run, 5 failed (all
  over-budget cases), 5 passed (compatibility/control cases).
- Mutations, each run on the full suite and then restored from a saved copy:
  remove the new condition → 5 failures; `>= 200000` → 4 failures (at-threshold
  overlap, valid maximal load); `> 200001` → 2 failures; same check moved after
  the sweep (correct error code, late rejection) → 3 failures from the
  work counters (`26 != 0`, `25 != 0`). Restored hash re-verified as `b0708b1d…`.
- `python -B -m unittest discover -s tests -v`: exit 0, 19 tests OK
  (CPython 3.14.3). In a clean CPython 3.12.13 venv after `pip install .`: exit 0,
  19 tests OK.
- `python -B -m examples.basic`: exit 0 on 3.14.3 and 3.12.13; digest
  `sha256:c04f0cdc…6df2a78`, identical to the unpatched source.
- GitHub Actions (3.11–3.14): not run for this branch, because it has not been pushed.
  Python 3.11 and 3.13 were not tested locally.

### Remaining limits

- Independent Claude Review has not been performed; this record contains only
  the implementer's claims.
- The Codex Security scan remains incomplete (report-storage permission
  failure above); no security scan has passed.
- `merged_cell_info` range/top-left strings are not length-bounded before
  `_coordinate` parsing. This was not analysed as part of this fix.
- The budget bounds this sweep only; the module's other phases have not had
  a complete resource audit.
