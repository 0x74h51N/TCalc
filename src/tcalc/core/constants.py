from __future__ import annotations

from typing import TYPE_CHECKING

import calc_native

if TYPE_CHECKING:
    from .utils import CalcValue

CONST_BY_ID: dict[calc_native.ConstId, calc_native.ConstSpec] = {}
CONST_VALUES: dict[calc_native.ConstId, "CalcValue"] = {}

for _spec in calc_native.const_table():
    CONST_BY_ID[_spec.id] = _spec
    CONST_VALUES[_spec.id] = _spec.value

E = CONST_VALUES[calc_native.ConstId.EulerNumber]

_imag = CONST_BY_ID[calc_native.ConstId.Imaginary]
I_UNIT_CHARS: frozenset[str] = frozenset({_imag.symbol, *_imag.aliases})
