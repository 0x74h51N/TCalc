from __future__ import annotations

from dataclasses import dataclass

from tcalc.core.ops import Operation


@dataclass
class ShiftedDef:
    label: str = ""
    operation: Operation | None = None
    tooltip: str = ""


@dataclass
class KeyDef:
    label: str = ""
    operation: Operation | str | None = None
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
