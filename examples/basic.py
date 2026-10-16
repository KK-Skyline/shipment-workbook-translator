"""A completely synthetic canonical-split input. Run: python -m examples.basic."""
from shipment_translator import RawCell, translate_shipment_workbook


def sample_cells():
    headers = (
        "product_model_raw", "qty_pcs", "pcs_per_carton",
        "carton_length_cm", "carton_width_cm", "carton_height_cm",
        "single_carton_net_weight_kg", "single_carton_gross_weight_kg",
        "packing_type",
    )
    values = ("SYNTHETIC-MODEL", 20, 10, 40, 30, 20, 8, 9, "loose")
    return [
        RawCell(
            sheet_name="Shipment", row_index=row, column_index=column,
            cell_ref=f"{chr(64 + column)}{row}", raw_value=value,
            displayed_value=str(value), data_type="s" if type(value) is str else "n",
            is_empty=False,
        )
        for row, items in ((1, headers), (2, values))
        for column, value in enumerate(items, 1)
    ]


if __name__ == "__main__":
    result = translate_shipment_workbook(sample_cells())
    if not result.ok:
        raise SystemExit(f"{result.error.phase}: {result.error.code}")
    print(f"Profile: {result.profile_id}")
    print(f"Rows: {len(result.ir.rows)}; cartons: {result.ir.carton_groups[0].declared_carton_count}")
    print(result.ir_sha256)
