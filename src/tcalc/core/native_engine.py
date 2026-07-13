#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#


from __future__ import annotations

from typing import Any, Callable

import calc_native
from calc_native import CalculatorError as NativeCalculatorError

from tcalc.errors import ErrorKind, raise_error

_KIND_MAP: dict[calc_native.ErrorKind, ErrorKind] = {
    calc_native.ErrorKind.Invalid: ErrorKind.INVALID,
    calc_native.ErrorKind.Malformed: ErrorKind.MALFORMED,
    calc_native.ErrorKind.MathErr: ErrorKind.MATH_ERR,
}

# name -> OpId, built once at import. Exactly ops.py:107's rule: a UI-only op has no
# native OpSpec and never reaches this table.
_OP_IDS: dict[str, calc_native.OpId] = {
    (spec.method or spec.id.name.lower()): spec.id for spec in calc_native.op_table()
}


def _make_call(native: calc_native.Calculator, op_id: calc_native.OpId) -> Callable[..., Any]:
    def call(*args: Any) -> Any:
        # Angle-taking ops receive the unit as a trailing argument; the rest fall back
        # to the app state.
        if args and isinstance(args[-1], calc_native.AngleUnit):
            *values, unit = args
        else:
            values = list(args)
            from tcalc.app_state import get_app_state

            unit = get_app_state().angle_unit
        try:
            return calc_native.apply(native, op_id, values, unit)
        except NativeCalculatorError as exc:
            # `kind` is set by the native exception translator; stubgen cannot see a
            # dynamically attached attribute.
            kind = getattr(exc, "kind", calc_native.ErrorKind.MathErr)
            raise_error(_KIND_MAP[kind], exc)

    return call


class Calculator:
    """Same surface as tcalc.core.engine.Calculator, routed through calc_native.apply.

    The bound callable is built once per operation name and cached on the instance, so a
    repeat call is a plain attribute lookup rather than a freshly built closure.

    Transitional: Python still walks the RPN and applies one operation at a time. Once
    the RPN walk is native, this surface goes away.
    """

    def __init__(self) -> None:
        self._native = calc_native.Calculator()

    def __getattr__(self, name: str) -> Callable[..., object]:
        op_id = _OP_IDS.get(name)
        if op_id is None:
            raise AttributeError(name)
        call = _make_call(self._native, op_id)
        object.__setattr__(self, name, call)
        return call
