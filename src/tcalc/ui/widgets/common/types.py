from __future__ import annotations

from typing import Union

from typing_extensions import TypedDict

from tcalc.core.ops import Operation


class ShiftedDef(TypedDict, total=False):
    label: str
    operation: Operation
    tooltip: str


class KeyDef(TypedDict, total=False):
    label: str
    operation: Union[Operation, str, None]
    row: int
    col: int
    rowspan: int
    colspan: int
    tooltip: str
    checkable: bool
    enabled: bool
    shifted: ShiftedDef
