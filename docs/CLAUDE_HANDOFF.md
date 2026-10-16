# Claude implementation and independent review handoff

Prepared: 2026-10-16. Status on this branch (`fix/merge-member-state-quadratic`):
the overlap-sweep issue below is still open here. A separate quadratic
member-state issue is patched in `1dade92`; see the last section.

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

## Fixed on this branch: quadratic P2 member-state evidence (CWE-400)

Branch `fix/merge-member-state-quadratic`, from `main` at `acb8996`.
It is independent of the overlap-sweep branch `fix/merge-membership-budget`.
Fix commit: `1dade92`. Nothing has been pushed, merged or released.

Defect: in `_snapshot`'s coverage pass (entry line 4747; line 4751 after the fix), every invalid
non-top-left member of a complete merge appended `MERGE_MEMBER_STATE_INVALID`
with refs for all n members and then `continue`d. That gave n-1 candidates of
n refs each, all of which `_select_candidate` keyed: O(n^2) CPU. A 1xn merge
whose cells all declare the same range and top-left and all hold `"x"` passes
every count, area and width budget. Reported timings: n=1000 took 4.16 s and
n=4000 about 66 s.

Why stopping at the first invalid member keeps the evidence: every candidate in
the group has the same phase, rank, code and field, and the same `cell` scope
(the anchor is the group's smallest coordinate). They differ only in their
`SORTED_BASE` descriptor id, which is allocated in creation order. A later
candidate contains this group's newly replaced atoms, so it can never reuse an
earlier base. The first candidate therefore always has the smallest key, and
candidates from other groups or codes are ordered by scope or rank. Fix:
`continue` becomes `break`, plus a four-line comment. The edit was made with a
byte-level script that keeps the file's mixed CRLF/LF line endings: there are
147 LF-only lines before and after. The CRLF count went from 6917 to 6921
because the four new comment lines use CRLF, like the lines around them.

Accepted semantic difference, approved by the owner on 2026-10-16: in mixed
valid/invalid groups the old code registered about n/2 distinct n-ref bases. Once
they passed 20*200000 memberships, `_private_descriptor_from_ids` raised and
the entry returned `INTERNAL_P2_CONTRACT_VIOLATION` with empty evidence. A 1x3000
alternating group took 118 s to reach that result. The same input now returns
`MERGE_MEMBER_STATE_INVALID` with rule-derived evidence.

Evidence in `tests/test_merge_member_state.py` (6 tests, all through
`translate_shipment_workbook`):

- Expected evidence comes from the rule, not from output: the anchor and the
  earlier valid members are `MERGED_TOP_LEFT_DIRECT` with anchor authority, and
  the first invalid member and everything after it are `DIRECT_CELL`. Cases:
  all invalid, alternating both ways, valid then invalid, invalid then valid,
  only the last member invalid, a 2x3 row-major merge, two sheets, three groups,
  and reversed or shuffled input.
- Work counter: it wraps the internal `_candidate` (not the public entry) and
  records the evidence size of each member-state candidate. A 1x64 group must
  produce exactly `[64]`. Positive control: two failing groups give `[5, 7]`, and
  a valid merge gives `[]`. The 1x3000 alternating case must be typed and give
  `[3000]`.
- RED before the fix (test file: CRLF working copy `c13b8ac7…`, committed LF blob
  `4ee05f14…`; translator `c6a6f8e5…`):
  4 failures. The counter saw 63 and 31 candidates of 64 refs; the positive
  control saw `[5, 7, 7]`; the 1x3000 case returned
  `INTERNAL_P2_CONTRACT_VIOLATION`. 15 tests ran, 104 s, exit 1.
- Anti-door check: the fixed source (`4056554d6b5a7e1d095b0e97c169d94281562f32c97b510df2423a453ebaefd2`)
  was reverted byte for byte to `c6a6f8e5…` (`git diff --quiet` clean), which
  gave the same 4 failures. It was then restored to `4056554d…` and passed again.
- Differential check: 6000 random small multi-sheet merge inputs, shuffled, with
  holes, bad top-lefts and overlaps. Results from `acb8996` and from the fix were
  identical in `repr` in 6000/6000 cases, 3411 of them member-state failures.
- After the fix, 1xn all-invalid and alternating groups take 0.06 s at n=1000,
  0.26 s at n=4000 and 1.04 s at n=16384.

Commands on Windows, Python 3.14.3, at `1dade92`:
`python -B -m unittest discover -s tests -v` exited 0 (15 tests: 9 existing and
6 new, about 0.44 s). `python -B -m examples.basic` exited 0 (1 row, 2 cartons,
`sha256:c04f0cdc…`). CI for this branch has not run because it has not been pushed.

Remaining limits:

- The overlap-sweep amplification above is not fixed on this branch.
- Each failing group still costs O(n log n) for one candidate's sort, and the
  coverage pass is O(total members). The work is linear-ish, but the code still
  runs inside the caller's process.
- Merging this branch with `fix/merge-membership-budget` is expected to conflict
  in this file and in `SECURITY.md`; the `translator.py` hunks do not overlap.
- Codex Security has still not completed, so no audit pass is claimed. Review
  of this fix: 子代理审查 (sub-agent review, not a Claude Review sign-off).
  The result is recorded below.

子代理审查 result (2026-10-16, clean-context general-purpose agent, of `1dade92`
and `ca9a878`): no blocking issues. It independently traced the selection
argument: the scope is the same within a group and differs between groups,
group members are disjoint, base ids only increase, and a member-state candidate
always returns a P2 failure. It re-ran the new tests against `acb8996`
(4 failures, 89 s) and ran its own differential check: 4012 cases with 0
differences, 717 of them member-state failures, with groups of up to 800 cells.
The full suite (15 tests) and the example both exited 0, and the line endings
were confirmed. Its four documentation findings (CRLF count wording, a dangling
"below" reference, the test-blob hash, the line number) are fixed in this text.
Not verified by the reviewer: the quoted timings, the 6000-case differential, the
owner's approval, and CI.

### Sync with upstream main (2026-10-16)

`origin/main` advanced to `b3abc81` (PR #1, dead-code removal in
`translator.py` only). This branch merged it in `caf2d14` without conflicts.
After the merge, `translator.py` SHA-256 is
`93c971c89351482e0817a6d78c7648c46291847fe767a3069395ab256b6dba87`; hashes
quoted above refer to the pre-merge `acb8996` base.
`python -B -m unittest discover -s tests -v` exited 0 (15 tests OK, CPython
3.14.3) and `python -B -m examples.basic` exited 0 with the unchanged digest
`sha256:c04f0cdc…6df2a78`. Re-mutating `break` back to `continue` on the
merged source gave 4 failures, and restoring it gave the same hash again.
