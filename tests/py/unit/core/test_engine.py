from __future__ import annotations

import pytest

from tcalc import errors
from tcalc.core.constants import E
from tests.py.unit.core.conftest import FakeBigComplex, FakeBigReal

param = pytest.param


@pytest.fixture
def calc(fake_engine):
    return fake_engine.Calculator()


def test_to_big_and_big_complex(calc):
    big = FakeBigReal(1)

    assert isinstance(calc._to_big(2.1), FakeBigReal)
    assert calc._to_big(big) is big

    assert isinstance(calc._to_big_complex(3), FakeBigComplex)
    assert isinstance(calc._to_big_complex(1 + 2j), FakeBigComplex)
    cx = FakeBigComplex("1", "2")
    assert calc._to_big_complex(cx) is cx
    assert calc._to_big_complex("x") == "x"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        param(3, complex(3.0, 0.0), id="int->complex"),
        param(2.5, complex(2.5, 0.0), id="float->complex"),
        param(1 + 2j, 1 + 2j, id="complex-passthrough"),
        param("x", "x", id="non-number-passthrough"),
    ],
)
def test_to_complex(calc, value, expected):
    assert calc._to_complex(value) == expected


@pytest.mark.parametrize(
    ("name", "args", "expected_types"),
    [
        param(
            "add",
            (FakeBigReal("1"), 2),
            (FakeBigReal, FakeBigReal),
            id="big-add-promotes",
        ),
        param("log", (FakeBigReal("1"), 2), (FakeBigReal, int), id="big-log-no-promote"),
        param(
            "add",
            (FakeBigReal("1"), 2 + 0j),
            (FakeBigComplex, FakeBigComplex),
            id="big+complex->bigcomplex",
        ),
        param("add", (1, 2 + 0j), (complex, complex), id="complex-promotes"),
        param("nope", (FakeBigReal("1"), 2), (FakeBigReal, int), id="unknown-op-no-promote"),
    ],
)
def test_coerce_args_type_promotions(calc, name, args, expected_types):
    out = calc._coerce_args(name, args)
    assert isinstance(out[0], expected_types[0])
    assert isinstance(out[1], expected_types[1])


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        param((10, 308), (int, int), id="pow-no-special-promotion"),
        param((0.1, 400), (float, int), id="pow-no-special-promotion-underflow"),
        param(
            (FakeBigReal("2"), 308),
            (FakeBigReal, FakeBigReal),
            id="pow-preserves-existing-bigreal",
        ),
        param((1 + 2j, 400), (complex, complex), id="pow-complex-promotes-complex"),
    ],
)
def test_pow_arg_coercion(calc, args, expected):
    out = calc._coerce_args("pow", args)
    assert isinstance(out[0], expected[0])
    assert isinstance(out[1], expected[1])


@pytest.mark.parametrize(
    ("name", "args", "promotes"),
    [
        param("sqrt", (-1,), True, id="sqrt-domain->complex"),
        param("sqrt", (1,), False, id="sqrt-ok"),
        param("log", (-1,), True, id="log-domain->complex"),
        param("log", (1,), False, id="log-ok"),
        param("root", (-1, 2), True, id="root-domain->complex"),
        param("nope", (-1,), False, id="unknown-op"),
    ],
)
def test_promote_complex(calc, name, args, promotes):
    out = calc._promote_complex(name, args)
    if promotes:
        assert isinstance(out[0], complex)
    else:
        assert out == args
    if len(args) >= 2:
        assert out[1] == args[1]


def test_promote_complex_big_passthrough(calc):
    big = FakeBigReal(1)
    assert calc._promote_complex("sqrt", (big,))[0] is big


def test_getattr_unknown_raises(calc):
    with pytest.raises(errors.Error):
        _ = calc.no_such


@pytest.mark.parametrize(
    "method",
    [
        param("bad_type", id="type-error-wrapped"),
        param("bad_native", id="native-error-wrapped"),
    ],
)
def test_getattr_errors_wrapped(calc, method):
    with pytest.raises(errors.Error):
        getattr(calc, method)(1, 2)


def test_getattr_promotes_complex(calc):
    calc.sqrt(-1)
    name, args = calc._native.calls[-1]

    assert name == "sqrt"
    assert isinstance(args[0], complex)


def test_getattr_non_callable_passthrough(calc):
    assert calc.calls is calc._native.calls


@pytest.mark.parametrize(
    ("method", "value", "expected_args"),
    [
        param("sqr", 3, (3, 2), id="sqr"),
        param("cube", 3, (3, 3), id="cube"),
        param("recip", 3, (3, -1), id="recip"),
        param("pow10", 3, (10, 3), id="pow10"),
        param("exp", 3, (E, 3), id="exp"),
    ],
)
def test_shortcut_methods_call_pow(calc, method, value, expected_args):
    getattr(calc, method)(value)
    name, args = calc._native.calls[-1]
    assert name == "pow"
    assert args == expected_args


@pytest.mark.parametrize(
    ("method", "value", "expected_call", "expected_args"),
    [
        param("negate", 3, "sub", (0, 3), id="negate->sub"),
        param("percent", 50, "div", (50, 100), id="percent->div"),
    ],
)
def test_shortcut_methods_call_other(calc, method, value, expected_call, expected_args):
    getattr(calc, method)(value)
    name, args = calc._native.calls[-1]
    assert name == expected_call
    assert args == expected_args


def test_getattr_forwards_kwargs(calc):
    class Native:
        def foo(self, a, *, b):
            return (a, b)

    calc._native = Native()
    assert calc.foo(1, b=2) == (1, 2)
