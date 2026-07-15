#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import calc_native
from calc_native import CalculatorError as NativeCalculatorError

from tcalc.core.utils import CalcValue
from tcalc.errors import ErrorKind, raise_error

_KIND_MAP: dict[calc_native.ErrorKind, ErrorKind] = {
    calc_native.ErrorKind.Invalid: ErrorKind.INVALID,
    calc_native.ErrorKind.Malformed: ErrorKind.MALFORMED,
    calc_native.ErrorKind.MathErr: ErrorKind.MATH_ERR,
}


def evaluate_branch(
    branch: calc_native.TokensBranch,
    calculator: calc_native.Calculator,
    unit: calc_native.AngleUnit,
) -> CalcValue:
    """Evaluate one row natively: shunt, walk, assign. One boundary crossing."""
    try:
        return calc_native.evaluate(branch, calculator, unit)
    except NativeCalculatorError as exc:
        # `kind` is attached by the native exception translator; stubgen cannot see a
        # dynamically attached attribute.
        kind = getattr(exc, "kind", calc_native.ErrorKind.MathErr)
        raise_error(_KIND_MAP[kind], exc)
