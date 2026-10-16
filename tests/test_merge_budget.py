"""Merge-overlap resource boundary regressions (CWE-400, see SECURITY.md).

The P2 overlap sweep stores one rectangle index per covered column, so its work
is the sum of declared rectangle widths ("rectangle-column memberships"), not
the distinct union area.  These synthetic witnesses pass the older count,
per-rectangle area and union-area gates while their membership total exceeds
200,000.  Expected facts are stated from the input geometry, not from results.
"""
import heapq
import random
import sys
import tracemalloc
import unittest

import shipment_translator.translator as translator_module
from examples.basic import sample_cells
from shipment_translator import RawCell, translate_shipment_workbook

MEMBERSHIP_BUDGET = 200000


def a1(row, column):
    letters = ""
    while column:
        column, remainder = divmod(column - 1, 26)
        letters = chr(65 + remainder) + letters
    return f"{letters}{row}"


def merge(start, end):
    return {"range": f"{a1(*start)}:{a1(*end)}", "top_left": a1(*start)}


def text_cell(sheet, row, column, value, merged=None):
    return RawCell(sheet, row, column, a1(row, column), value, value, "s", False,
                   merged_cell_info=merged)


def blank_cell(sheet, row, column, merged=None):
    return RawCell(sheet, row, column, a1(row, column), None, "", "n", True,
                   merged_cell_info=merged)


def row_family(widths, sheet="Merges"):
    """Cell (1, i) declares an incomplete rectangle (1, i)..(1, i + w - 1)."""
    return [text_cell(sheet, 1, index, "x", merge((1, index), (1, index + width - 1)))
            for index, width in enumerate(widths, 1)]


def handoff_family(rows, columns, half_width=8192):
    """Scaled-down copy of the stress family in docs/CLAUDE_HANDOFF.md."""
    return [
        text_cell("Merges", row, column, "x", merge(
            (1, max(1, column - half_width)), (row, min(16384, column + half_width - 1))))
        for row in range(1, rows + 1)
        for column in range(1, columns + 1)
    ]


def widths_totalling(total, count=25, wide=8192):
    widths = [wide] * (count - 1) + [total - wide * (count - 1)]
    assert all(1 < width <= wide for width in widths) and sum(widths) == total
    return widths


def declared_rectangles(cells):
    rectangles = set()
    for cell in cells:
        info = cell.merged_cell_info
        start, end = info["range"].split(":")
        rectangles.add((cell.sheet_name, start, end))
    return rectangles


def parse(ref):
    letters = "".join(char for char in ref if char.isalpha())
    column = 0
    for letter in letters:
        column = column * 26 + ord(letter) - 64
    return int(ref[len(letters):]), column


def geometry(cells):
    """Independent count/area/union/membership totals of declared rectangles."""
    union, max_area, memberships = set(), 0, 0
    rectangles = declared_rectangles(cells)
    for sheet, start, end in rectangles:
        (top, left), (bottom, right) = parse(start), parse(end)
        max_area = max(max_area, (bottom - top + 1) * (right - left + 1))
        memberships += right - left + 1
        union.update((sheet, row, column) for row in range(top, bottom + 1)
                     for column in range(left, right + 1))
    return len(rectangles), max_area, len(union), memberships


def observe(cells):
    """Translate through the public entry while counting overlap-sweep work.

    ``sweep_insertions`` counts heap pushes made by the P2 snapshot (one per
    rectangle entering the sweep); ``component_lookups`` counts the sweep's
    union-find lookups; ``peak_bytes`` is the traced allocation peak.
    """
    counts = {"sweep_insertions": 0, "component_lookups": 0}
    snapshot_code = translator_module._snapshot.__code__

    def profiler(frame, event, arg):
        if event == "c_call" and arg is heapq.heappush and frame.f_code is snapshot_code:
            counts["sweep_insertions"] += 1
        elif (event == "call" and frame.f_code.co_name == "component_root"
              and frame.f_code.co_filename == translator_module.__file__):
            counts["component_lookups"] += 1

    tracemalloc.start()
    sys.setprofile(profiler)
    try:
        result = translate_shipment_workbook(cells)
    finally:
        sys.setprofile(None)
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    counts["peak_bytes"] = peak
    return result, counts


class MergeMembershipBudgetTests(unittest.TestCase):
    def assert_budget_failure(self, result):
        self.assertFalse(result.ok)
        self.assertIsNone(result.ir)
        self.assertIsNone(result.canonical_json_utf8)
        self.assertEqual((result.error.phase, result.error.code, result.error.scope, result.error.field),
                         ("P2_EFFECTIVE_CELL_AND_MERGE", "RAW_MERGE_BUDGET_EXCEEDED",
                          "workbook", "RESOURCE_MERGE_AREA"))
        self.assertEqual(result.error.source_cells, ())

    def assert_overlap_of(self, result, declaring_refs):
        self.assertFalse(result.ok)
        self.assertEqual((result.error.phase, result.error.code),
                         ("P2_EFFECTIVE_CELL_AND_MERGE", "MERGE_RANGE_OVERLAP"))
        self.assertEqual(sorted(ref.cell_ref for ref in result.error.source_cells), sorted(declaring_refs))

    def test_handoff_family_rejected_before_sweep_allocation(self):
        cells = handoff_family(rows=2, columns=13)
        count, max_area, union, memberships = geometry(cells)
        # The witness passes every pre-existing gate ...
        self.assertEqual(count, 26)
        self.assertLessEqual(max_area, 200000)
        self.assertLessEqual(union, 200000)
        # ... while its repeated column memberships exceed the budget.
        self.assertGreater(memberships, MEMBERSHIP_BUDGET)
        result, counts = observe(cells)
        self.assert_budget_failure(result)
        self.assertEqual(counts["sweep_insertions"], 0)
        self.assertEqual(counts["component_lookups"], 0)
        # The unbounded sweep retains >200,000 set memberships (~18 MB on
        # CPython 3.14); the bounded rejection stays far below that.
        self.assertLess(counts["peak_bytes"], 4 * 1024 * 1024)

    def test_threshold_below_at_and_above(self):
        declaring = [a1(1, column) for column in range(1, 26)]
        below = row_family(widths_totalling(MEMBERSHIP_BUDGET - 1))
        self.assertEqual(geometry(below)[3], MEMBERSHIP_BUDGET - 1)
        self.assert_overlap_of(translate_shipment_workbook(below), declaring)

        at = row_family(widths_totalling(MEMBERSHIP_BUDGET))
        count, max_area, union, memberships = geometry(at)
        self.assertEqual((count, memberships), (25, MEMBERSHIP_BUDGET))
        self.assertLessEqual(max_area, 200000)
        self.assertLessEqual(union, 200000)
        at_result, at_counts = observe(at)
        self.assert_overlap_of(at_result, declaring)
        # Positive control: an admitted declaration set really reaches the
        # sweep, so zero counts below cannot come from a blind instrument.
        self.assertEqual(at_counts["sweep_insertions"], 25)
        self.assertGreater(at_counts["component_lookups"], 0)

        above = row_family(widths_totalling(MEMBERSHIP_BUDGET + 1))
        self.assertEqual(geometry(above)[3], MEMBERSHIP_BUDGET + 1)
        self.assertLessEqual(geometry(above)[2], 200000)
        above_result, above_counts = observe(above)
        self.assert_budget_failure(above_result)
        self.assertEqual(above_counts["sweep_insertions"], 0)
        self.assertEqual(above_counts["component_lookups"], 0)
        self.assertLess(above_counts["peak_bytes"] * 4, at_counts["peak_bytes"])

    def test_budget_is_workbook_wide(self):
        half = widths_totalling(MEMBERSHIP_BUDGET // 2 + 1, count=13)
        first, second = row_family(half, "Left"), row_family(half, "Right")
        declaring = [a1(1, column) for column in range(1, 14)]
        self.assert_overlap_of(translate_shipment_workbook(first), declaring)
        both = first + second
        self.assertEqual(geometry(both)[3], MEMBERSHIP_BUDGET + 2)
        result, counts = observe(both)
        self.assert_budget_failure(result)
        self.assertEqual(counts["sweep_insertions"], 0)

    def test_budget_failure_is_permutation_stable(self):
        cells = handoff_family(rows=2, columns=13)
        baseline = translate_shipment_workbook(cells)
        self.assert_budget_failure(baseline)
        orders = [list(reversed(cells))]
        for seed in (1, 7, 2026):
            shuffled = list(cells)
            random.Random(seed).shuffle(shuffled)
            orders.append(shuffled)
        for order in orders:
            self.assertEqual(translate_shipment_workbook(tuple(order)), baseline)

    def test_overlap_evidence_at_threshold_is_permutation_stable(self):
        cells = row_family(widths_totalling(MEMBERSHIP_BUDGET))
        baseline = translate_shipment_workbook(cells)
        self.assert_overlap_of(baseline, [a1(1, column) for column in range(1, 26)])
        shuffled = list(cells)
        random.Random(11).shuffle(shuffled)
        self.assertEqual(translate_shipment_workbook(shuffled), baseline)

    def test_resource_precedence_matches_existing_area_gate(self):
        # Documented precedence: like the pre-existing area gates, the budget
        # is a P2 resource preflight that returns before earlier P2 facts.
        schema_error = text_cell("Merges", 3, 1, "y", {"range": "A3:B3"})
        over_area = [text_cell("Merges", 1, 1, "x", merge((1, 1), (13, 16384))), schema_error]
        self.assert_budget_failure(translate_shipment_workbook(over_area))
        over_memberships = row_family(widths_totalling(MEMBERSHIP_BUDGET + 1)) + [schema_error]
        self.assert_budget_failure(translate_shipment_workbook(over_memberships))
        within = row_family(widths_totalling(MEMBERSHIP_BUDGET)) + [schema_error]
        result = translate_shipment_workbook(within)
        self.assertEqual(result.error.code, "MERGE_SCHEMA_INVALID")

    def test_incomplete_disjoint_declaration_within_budget_keeps_coverage_error(self):
        cells = [text_cell("Merges", 1, 1, "x", merge((1, 1), (1, 8192))),
                 text_cell("Merges", 2, 1, "y", merge((2, 1), (2, 8192)))]
        self.assertEqual(geometry(cells)[3], 16384)
        result, counts = observe(cells)
        self.assertEqual((result.error.phase, result.error.code),
                         ("P2_EFFECTIVE_CELL_AND_MERGE", "MERGE_COVERAGE_INCOMPLETE"))
        self.assertEqual(counts["sweep_insertions"], 2)


class ValidMergeCompatibilityTests(unittest.TestCase):
    def test_valid_vertical_and_horizontal_merges_keep_translation(self):
        vertical, horizontal = merge((1, 1), (3, 1)), merge((1, 3), (1, 5))
        notes = [
            text_cell("Zz Notes", 1, 1, "note", vertical),
            blank_cell("Zz Notes", 2, 1, vertical), blank_cell("Zz Notes", 3, 1, vertical),
            text_cell("Zz Notes", 1, 3, "x", horizontal),
            blank_cell("Zz Notes", 1, 4, horizontal), blank_cell("Zz Notes", 1, 5, horizontal),
        ]
        plain = translate_shipment_workbook(sample_cells())
        merged = translate_shipment_workbook(sample_cells() + notes)
        self.assertTrue(merged.ok, merged.error)
        row = merged.ir.rows[0]
        self.assertEqual((row.model_label, row.qty_pcs, row.packing), ("SYNTHETIC-MODEL", 20, "loose"))
        provenance = next(p for p in row.provenance if p.field == "packing")
        self.assertEqual(tuple(r.cell_ref for r in provenance.source_cells), ("I1", "I2"))
        self.assertEqual(merged.canonical_json_utf8, plain.canonical_json_utf8)

    def test_vertical_merge_members_carry_top_left_authority(self):
        # Canonical-profile rows forbid merged bound data fields (P4), so the
        # failure evidence exposes the P2 effective cells of the merge itself.
        span = merge((2, 9), (3, 9))
        cells = []
        for cell in sample_cells():
            if cell.cell_ref == "I2":
                cell = text_cell(cell.sheet_name, 2, 9, "loose", span)
            cells.append(cell)
            if cell.row_index == 2:
                cells.append(blank_cell(cell.sheet_name, 3, cell.column_index, span)
                             if cell.column_index == 9 else
                             RawCell(cell.sheet_name, 3, cell.column_index, a1(3, cell.column_index),
                                     cell.raw_value, cell.displayed_value, cell.data_type, False))
        result = translate_shipment_workbook(cells)
        self.assertFalse(result.ok)
        self.assertEqual((result.error.phase, result.error.code), ("P4_ROW", "MERGED_DATA_FIELD_FORBIDDEN"))
        facts = [(r.cell_ref, r.authority_cell_ref, r.value_origin) for r in result.error.source_cells]
        self.assertEqual(facts, [("I2", "I2", "MERGED_TOP_LEFT_DIRECT"), ("I3", "I2", "MERGED_TOP_LEFT_DIRECT")])

    def test_disjoint_merges_at_membership_budget_pass_p2(self):
        # 25,000 complete, disjoint 1x8 merges: union area and memberships are
        # both exactly 200,000, the largest valid merge load.  No header row
        # exists, so the first failure after an accepted P2 is in P3.
        cells = []
        for row in range(1, 21):
            for left in range(1, 10001, 8):
                span = merge((row, left), (row, left + 7))
                cells.append(text_cell("Grid", row, left, "x", span))
                cells.extend(blank_cell("Grid", row, column, span) for column in range(left + 1, left + 8))
        self.assertEqual(len(cells), 200000)
        result = translate_shipment_workbook(cells)
        self.assertFalse(result.ok)
        self.assertEqual((result.error.phase, result.error.code), ("P3_PROFILE_BIND", "SHIPMENT_SHEET_REQUIRED"))


if __name__ == "__main__":
    unittest.main()
