#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The native evaluator against the Python one it replaces.

`core/engine.py` stays in tree, working and independent, precisely so it can serve as
the oracle here: every case runs through both and must agree on the value *and* the
type. A Rational where the old path gave a float is a failure, not a rounding detail.

The divergences at the bottom are deliberate and are the reason for the port.
"""

from __future__ import annotations

import calc_native
import pytest

from tcalc.core.engine import Calculator as PyCalculator
from tcalc.core.native_engine import Calculator as NativeCalculator

R = calc_native.Rational

CASES = [
    # exact rationals
    ("add", (2, 3)),
    ("sub", (2, 3)),
    ("mul", (R(1, 2), R(2, 3))),
    ("div", (1, 3)),
    ("pow", (R(2), R(-2))),
    ("sqr", (R(1, 2),)),
    # mixed arms: Python leant on pybind to widen the int; native has to homogenise
    ("add", (2, 3.5)),
    ("mul", (2, 0.5)),
    # exact rational roots (the logic that was stranded in the pybind layer)
    ("sqrt", (R(4, 9),)),
    ("cbrt", (R(-8, 27),)),
    # irrational -> the float fallback takes over
    ("sqrt", (R(2),)),
    # complex-domain promotion
    ("sqrt", (-1,)),
    ("asin", (2, calc_native.AngleUnit.RAD)),  # parser.py:275 always passes the unit
    # BigReal escalation
    ("pow", (10, 400)),
    ("mul", (1e200, 1e200)),
    # narrowing: an op with no Rational arm
    ("fact", (5,)),
    ("fact", (R(5),)),
    # derived ops (engine.py:141-165 defines these in Python; native has kernels)
    ("percent", (50,)),
    ("negate", (3,)),
    ("recip", (4,)),
]


def _exact(v: object) -> str:
    """Rational and BigReal have no __eq__ in the binding, so two equal values compare as
    distinct objects. Their textual form is lossless, so compare that.
    """
    return repr(v)


@pytest.mark.parametrize("method,args", CASES, ids=[f"{m}{args}" for m, args in CASES])
def test_native_matches_the_python_oracle(method, args):
    got = getattr(NativeCalculator(), method)(*args)
    want = getattr(PyCalculator(), method)(*args)

    assert type(got) is type(want), f"{method}{args}: {type(got)} vs {type(want)}"
    assert _exact(got) == _exact(want)


ERROR_CASES = [
    ("ln", (0,)),  # promoted into the complex domain, then log(0) is still an error
    ("fact", (1 + 2j,)),  # no Complex arm
    ("cbrt", (calc_native.BigReal("8"),)),  # no BigReal arm: never demote a BigReal
]


@pytest.mark.parametrize("method,args", ERROR_CASES)
def test_both_paths_reject_the_same_arguments(method, args):
    from tcalc import errors

    with pytest.raises(errors.CalculatorError):
        getattr(NativeCalculator(), method)(*args)
    with pytest.raises(errors.CalculatorError):
        getattr(PyCalculator(), method)(*args)


# --------------------------------------------------------------------------------
# Deliberate divergences. The old binding promotes a double result into BigReal only
# when it is `inf` (promote_inf_to_big, bindings.hpp:51), so multiplication escalates
# on overflow but silently collapses on underflow. pow's predictive gate has the same
# hole: its threshold is -324, but a double goes subnormal below 1e-308, leaving a
# ~16-decade band it calls "safe". The native rule is symmetric and lives in one place.
# --------------------------------------------------------------------------------

DIVERGENCES = [
    ("mul", (1e-200, 1e-200), 0.0),
    ("div", (1e-200, 1e200), 0.0),
    ("pow", (2.0, -1075.0), 0.0),
]


@pytest.mark.parametrize("method,args,old_value", DIVERGENCES)
def test_underflow_promotes_where_the_old_path_collapsed(method, args, old_value):
    old = getattr(PyCalculator(), method)(*args)
    assert old == old_value, "the old path is supposed to lose this value"

    new = getattr(NativeCalculator(), method)(*args)
    assert isinstance(new, calc_native.BigReal)
    assert repr(new) != "0"


def test_pow_subnormal_band_promotes():
    """2^-1030 lands in the band pow_to_big reports as safe but a double cannot hold."""
    old = getattr(PyCalculator(), "pow")(2.0, -1030.0)
    assert isinstance(old, float)
    assert 0 < old < 2.2250738585072014e-308  # subnormal: digits already gone

    new = getattr(NativeCalculator(), "pow")(2.0, -1030.0)
    assert isinstance(new, calc_native.BigReal)
