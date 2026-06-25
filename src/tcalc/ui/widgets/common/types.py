from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

import calc_native

from tcalc.core.ops import Operation


@dataclass
class ShiftedDef:
    label: str = ""
    operation: Operation | None = None
    tooltip: str = ""


class KeySettings(TypedDict, total=False):
    operation: str
    bg_color: str
    text_color: str


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
        data: KeySettings = {}
        if isinstance(self.operation, (Operation, calc_native.ConstId)):
            data["operation"] = self.operation.name
        if self.bg_color:
            data["bg_color"] = self.bg_color
        if self.text_color:
            data["text_color"] = self.text_color
        return data
