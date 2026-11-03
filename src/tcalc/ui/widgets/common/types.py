from __future__ import annotations

from dataclasses import dataclass

import calc_native

from tcalc.core.ops import Operation


@dataclass
class ShiftedDef:
    label: str = ""
    operation: Operation | None = None
    tooltip: str = ""


@dataclass(frozen=True, slots=True)
class KeySettings:
    """A custom pad key as saved: an Operation or ConstId name, and its colors."""

    operation: str = ""
    bg_color: str = ""
    text_color: str = ""


@dataclass(frozen=True, slots=True)
class GridLayout:
    max_rows: int
    keys: tuple[KeySettings, ...]


@dataclass(frozen=True, slots=True)
class PadLayout:
    """A custom pad's saved layout."""

    label: str
    cols: int
    rows: int
    grids: tuple[GridLayout, ...]


@dataclass
class KeyDef:
    label: str = ""
    operation: Operation | str | calc_native.ConstId | None = None
    row: int = 0
    col: int = 0
    rowspan: int = 1
    colspan: int = 1
    tooltip: str = ""
    checkable: bool = False
    enabled: bool = True
    shifted: ShiftedDef | None = None
    bg_color: str = ""
    text_color: str = ""

    @staticmethod
    def from_op(op: Operation, row: int, col: int) -> "KeyDef":
        return KeyDef(
            label=op.symbol,
            operation=op,
            row=row,
            col=col,
            tooltip=op.name.lower().replace("_", " "),
        )

    def to_settings(self) -> KeySettings:
        operation = self.operation
        name = operation.name if isinstance(operation, (Operation, calc_native.ConstId)) else ""
        return KeySettings(name, self.bg_color, self.text_color)
