"""P2 merge member-state evidence and its per-group work bound (CWE-400).

Expected evidence is derived from the merge rule, not from translator output:
members of a complete merge are visited in row-major order after the top-left
anchor is resolved; each valid blank member then reads the anchor's value.  The
first member whose snapshot state is not blank fails the group, and its evidence
is the group at that moment: the anchor and the earlier valid members carry the
anchor's authority, while that member and every later member are still direct.
Sheets are identified by S000001.. in sorted sheet-name order, and the smallest
(sheet, anchor row, anchor column) failure wins regardless of input order.
"""
import random
import unittest
from contextlib import contextmanager

from shipment_translator import RawCell, translate_shipment_workbook
from shipment_translator import translator as core


def _col(index):
    text = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        text = chr(65 + remainder) + text
    return text


def _ref(row, column):
    return f"{_col(column)}{row}"


def _merge(sheet, top, left, rows, columns, invalid):
    """One complete merge; ``invalid`` holds (row, column) offsets with value "x"."""
    span = f"{_ref(top, left)}:{_ref(top + rows - 1, left + columns - 1)}"
    info = {"range": span, "top_left": _ref(top, left)}
    cells = []
    for dr in range(rows):
        for dc in range(columns):
            row, column = top + dr, left + dc
            if (dr, dc) == (0, 0) or (dr, dc) in invalid:
                cells.append(RawCell(sheet, row, column, _ref(row, column), "x", "x", "s", False, info))
            else:
                cells.append(RawCell(sheet, row, column, _ref(row, column), None, "", "n", True, info))
    return cells


def _expected(sheet_ref, top, left, rows, columns, invalid):
    members = [(dr, dc) for dr in range(rows) for dc in range(columns)]
    first = next(offset for offset in members if offset != (0, 0) and offset in invalid)
    anchor = _ref(top, left)
    evidence = []
    for offset in members:
        cell = _ref(top + offset[0], left + offset[1])
        if offset < first:
            evidence.append((sheet_ref, cell, anchor, "MERGED_TOP_LEFT_DIRECT"))
        else:
            evidence.append((sheet_ref, cell, cell, "DIRECT_CELL"))
    return tuple(evidence)


def _evidence(result):
    return tuple((ref.sheet_ref, ref.cell_ref, ref.authority_cell_ref, ref.value_origin)
                 for ref in result.error.source_cells)


@contextmanager
def _member_state_work():
    """Record the evidence size of every MERGE_MEMBER_STATE_INVALID candidate built."""
    sizes = []
    original = core._candidate

    def counting(code, field, source_cells=(), *args, **kwargs):
        if code == "MERGE_MEMBER_STATE_INVALID":
            sizes.append(len(source_cells))
        return original(code, field, source_cells, *args, **kwargs)

    core._candidate = counting
    try:
        yield sizes
    finally:
        core._candidate = original


def _row_offsets(n, predicate):
    return frozenset((0, i) for i in range(1, n) if predicate(i))


class MergeMemberStateEvidenceTests(unittest.TestCase):
    def assert_member_state(self, cells, expected):
        result = translate_shipment_workbook(cells)
        self.assertFalse(result.ok)
        self.assertEqual((result.error.phase, result.error.code),
                         ("P2_EFFECTIVE_CELL_AND_MERGE", "MERGE_MEMBER_STATE_INVALID"))
        self.assertEqual(_evidence(result), expected)
        return result

    def test_first_invalid_member_snapshot_is_selected(self):
        n = 6
        cases = {
            "all_invalid": lambda i: True,
            "alternating_odd": lambda i: i % 2 == 1,
            "alternating_even": lambda i: i % 2 == 0,
            "valid_then_invalid": lambda i: i >= 3,
            "invalid_then_valid": lambda i: i < 3,
            "only_last_invalid": lambda i: i == n - 1,
        }
        for name, predicate in cases.items():
            with self.subTest(name):
                invalid = _row_offsets(n, predicate)
                self.assert_member_state(_merge("Sheet", 1, 1, 1, n, invalid),
                                         _expected("S000001", 1, 1, 1, n, invalid))

    def test_two_dimensional_merge_uses_row_major_order(self):
        invalid = frozenset({(1, 0), (1, 2)})
        self.assert_member_state(_merge("Sheet", 2, 2, 2, 3, invalid),
                                 _expected("S000001", 2, 2, 2, 3, invalid))

    def test_lowest_sheet_and_anchor_wins_for_any_input_order(self):
        b_group = _merge("B", 2, 1, 1, 4, frozenset({(0, 2), (0, 3)}))
        a_low = _merge("A", 5, 1, 1, 4, frozenset({(0, 3)}))
        a_high = _merge("A", 9, 2, 1, 3, frozenset({(0, 1)}))
        cells = b_group + a_low + a_high
        expected = _expected("S000001", 5, 1, 1, 4, frozenset({(0, 3)}))
        orders = [cells, list(reversed(cells))]
        rng = random.Random(20261016)
        for _ in range(4):
            shuffled = list(cells)
            rng.shuffle(shuffled)
            orders.append(shuffled)
        for index, order in enumerate(orders):
            with self.subTest(order=index):
                self.assert_member_state(order, expected)

    def test_member_state_work_is_one_candidate_per_group(self):
        n = 64
        for name, predicate in (("all_invalid", lambda i: True),
                                ("alternating", lambda i: i % 2 == 0)):
            with self.subTest(name), _member_state_work() as sizes:
                invalid = _row_offsets(n, predicate)
                self.assert_member_state(_merge("Sheet", 1, 1, 1, n, invalid),
                                         _expected("S000001", 1, 1, 1, n, invalid))
                self.assertEqual(sizes, [n])

    def test_work_counter_observes_every_failing_group(self):
        # Positive control: the counter is not blind.  Two failing groups give
        # exactly two observations of their own sizes; a valid merge gives none.
        with _member_state_work() as sizes:
            cells = (_merge("Sheet", 1, 1, 1, 5, frozenset({(0, 4)}))
                     + _merge("Sheet", 3, 1, 1, 7, frozenset({(0, 1), (0, 2)})))
            self.assert_member_state(cells, _expected("S000001", 1, 1, 1, 5, frozenset({(0, 4)})))
        self.assertEqual(sorted(sizes), [5, 7])
        with _member_state_work() as sizes:
            result = translate_shipment_workbook(_merge("Sheet", 1, 1, 1, 5, frozenset()))
        self.assertFalse(result.ok)
        self.assertNotEqual(result.error.code, "MERGE_MEMBER_STATE_INVALID")
        self.assertEqual(sizes, [])

    def test_large_mixed_group_is_typed_member_state_failure(self):
        # Before the per-group bound this input built ~n/2 distinct n-cell
        # descriptors, overflowed the private evidence arena and surfaced as
        # INTERNAL_P2_CONTRACT_VIOLATION without evidence.  It must now be the
        # typed member-state failure after linear work.
        n = 3000
        invalid = _row_offsets(n, lambda i: i % 2 == 0)
        with _member_state_work() as sizes:
            self.assert_member_state(_merge("Sheet", 1, 1, 1, n, invalid),
                                     _expected("S000001", 1, 1, 1, n, invalid))
        self.assertEqual(sizes, [n])


if __name__ == "__main__":
    unittest.main()
