import hashlib
import json
import unittest
from dataclasses import replace
from decimal import Decimal

from examples.basic import sample_cells
from shipment_translator import RawCell, translate_shipment_workbook


class PublicApiTests(unittest.TestCase):
    def test_synthetic_canonical_facts(self):
        result = translate_shipment_workbook(sample_cells())
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.profile_id, "canonical_split.v1")
        self.assertEqual(len(result.ir.rows), 1)
        row = result.ir.rows[0]
        self.assertEqual((row.model_label, row.qty_pcs, row.pcs_per_carton, row.packing),
                         ("SYNTHETIC-MODEL", 20, 10, "loose"))
        carton = result.ir.carton_groups[0]
        self.assertEqual(carton.declared_carton_count, 2)
        self.assertEqual((carton.outer_carton_length_mm, carton.outer_carton_width_mm,
                          carton.outer_carton_height_mm), (Decimal(400), Decimal(300), Decimal(200)))
        self.assertEqual((carton.carton_net_weight_kg, carton.carton_gross_weight_kg),
                         (Decimal(8), Decimal(9)))

    def test_packing_has_exact_source_coordinates(self):
        result = translate_shipment_workbook(sample_cells())
        self.assertTrue(result.ok, result.error)
        provenance = next(p for p in result.ir.rows[0].provenance if p.field == "packing")
        self.assertEqual(tuple(r.cell_ref for r in provenance.source_cells), ("I1", "I2"))

    def test_canonical_bytes_match_digest(self):
        result = translate_shipment_workbook(sample_cells())
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.ir_sha256, "sha256:" + hashlib.sha256(result.canonical_json_utf8).hexdigest())
        self.assertIsInstance(json.loads(result.canonical_json_utf8), dict)

    def test_input_order_is_stable(self):
        cells = sample_cells()
        a, b = translate_shipment_workbook(cells), translate_shipment_workbook(list(reversed(cells)))
        self.assertTrue(a.ok, a.error)
        self.assertTrue(b.ok, b.error)
        self.assertEqual(a.canonical_json_utf8, b.canonical_json_utf8)

    def test_empty_input_is_typed_failure_without_ir(self):
        result = translate_shipment_workbook([])
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "RAW_CELLS_EMPTY")
        self.assertIsNone(result.ir)
        self.assertIsNone(result.canonical_json_utf8)

    def test_bad_coordinate_is_rejected(self):
        cells = sample_cells()
        cells[0] = replace(cells[0], cell_ref="Z99")
        result = translate_shipment_workbook(cells)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "RAW_CELL_REF_INVALID")

    def test_missing_packing_value_is_rejected(self):
        cells = [replace(c, raw_value=None, displayed_value="", is_empty=True, data_type="n")
                 if c.cell_ref == "I2" else c for c in sample_cells()]
        result = translate_shipment_workbook(cells)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "PACKING_REQUIRED")

    def test_invalid_packing_value_is_rejected(self):
        cells = [replace(c, raw_value="unknown", displayed_value="unknown")
                 if c.cell_ref == "I2" else c for c in sample_cells()]
        result = translate_shipment_workbook(cells)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "PACKING_TYPE_INVALID")

    def test_repeated_calls_are_isolated(self):
        a = translate_shipment_workbook(sample_cells())
        self.assertFalse(translate_shipment_workbook([]).ok)
        b = translate_shipment_workbook(sample_cells())
        self.assertTrue(a.ok, a.error)
        self.assertEqual(a.canonical_json_utf8, b.canonical_json_utf8)


if __name__ == "__main__":
    unittest.main()
