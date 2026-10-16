"""Cell snapshot accepted by the translation boundary."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RawCell:
    sheet_name: str
    row_index: int
    column_index: int
    cell_ref: str
    raw_value: Any
    displayed_value: str
    data_type: str
    is_empty: bool
    merged_cell_info: dict[str, Any] | None = None
    formula: str | None = None
    formula_cached_value: Any = None
    formula_cache_status: str = "not_applicable"
    hidden_row: bool = False
    hidden_column: bool = False
