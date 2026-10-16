# Public boundary

`translate_shipment_workbook(raw_cells, *, selected_sheet_ref=None)` accepts a
list or tuple of `RawCell` records. The optional sheet reference is the translator's
sheet token, not necessarily a visible worksheet title; pass it only after obtaining
the correct token from your integration. Leave it unset for the basic single-sheet case.

Each `RawCell` has fourteen fields:

| Field | Meaning |
| --- | --- |
| `sheet_name` | Original worksheet name |
| `row_index`, `column_index` | One-based source coordinates |
| `cell_ref` | A1 address matching those coordinates |
| `raw_value`, `displayed_value` | Scalar value and its display representation |
| `data_type`, `is_empty` | Source type and empty-state declaration |
| `merged_cell_info` | Optional `range` and `top_left` declaration |
| `formula` | Formula text, when present |
| `formula_cached_value` | Cached scalar; do not fabricate it |
| `formula_cache_status` | `not_applicable`, `available`, `missing`, `error`, or `external_reference` |
| `hidden_row`, `hidden_column` | Original visibility flags |

Declarations must be internally consistent. For example, a blank cell uses a
blank-compatible type as well as `raw_value=None`, an empty display and `is_empty=True`.
Merge coverage must include the physical cells required by the parser.

The canonical example binds these columns, in centimetres and kilograms:

```text
product_model_raw, qty_pcs, pcs_per_carton,
carton_length_cm, carton_width_cm, carton_height_cm,
single_carton_net_weight_kg, single_carton_gross_weight_kg, packing_type
```

Successful IR dimensions are expressed in millimetres as `Decimal`. The public
result is a frozen dataclass with `ok`, `profile_id`, `ir`, `error`,
`canonical_json_utf8` and `ir_sha256`, plus schema/contract/rule versions.
Use the returned canonical bytes directly for byte comparisons and digests; a
generic `json.dumps(dataclasses.asdict(ir))` is not its canonical serializer.

Errors include phase, code, scope, field and source-cell evidence. Reject a failed
result rather than consuming partial facts. Successful results also expose
`required_t2_block` and load-unit completeness declarations, which downstream
integrations must enforce.

This guide documents the extracted implementation, not a replacement for a
complete independently versioned business specification. Historical Base/Errata/
Vector artifacts are not distributed here and historical full-conformance claims
are deliberately not carried into this release.
