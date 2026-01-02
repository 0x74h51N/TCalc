from __future__ import annotations

import pytest

from tcalc.core import errors

from tests.py.unit.core.conftest import FakeBigComplex, FakeBigReal


def test_to_big_and_big_complex(fake_engine):
    calc = fake_engine.Calculator()
    big = FakeBigReal(1)

    assert isinstance(calc._to_big(2.1), FakeBigReal)

    assert isinstance(calc._to_big_complex(3), FakeBigComplex)
    assert isinstance(calc._to_big_complex(1 + 2j), FakeBigComplex)


def test_to_complex(fake_engine):
    calc = fake_engine.Calculator()
    assert calc._to_complex(3) == complex(3.0, 0.0)
    assert calc._to_complex(2.5) == complex(2.5, 0.0)
    assert calc._to_complex(1 + 2j) == 1 + 2j
    assert calc._to_complex("x") == "x"


def test_coerce_args_big_supported(fake_engine):
    calc = fake_engine.Calculator()
    args = (FakeBigReal("1"), 2)
    out = calc._coerce_args("add", args)

    assert isinstance(out[0], FakeBigReal)
    assert isinstance(out[1], FakeBigReal)


def test_coerce_args_big_unsupported(fake_engine):
    calc = fake_engine.Calculator()
    args = (FakeBigReal("1"), 2)
    out = calc._coerce_args("log", args)

    assert isinstance(out[0], FakeBigReal)
    assert isinstance(out[1], int)


def test_coerce_args_bigcomplex(fake_engine):
    calc = fake_engine.Calculator()
    args = (FakeBigReal("1"), 2 + 0j)
    out = calc._coerce_args("add", args)

    assert isinstance(out[0], FakeBigComplex)
    assert isinstance(out[1], FakeBigComplex)


def test_coerce_args_complex(fake_engine):
    calc = fake_engine.Calculator()
    args = (1, 2 + 0j)
    out = calc._coerce_args("add", args)

    assert isinstance(out[0], complex)
    assert isinstance(out[1], complex)


def test_pow_big_promote(fake_engine):
    calc = fake_engine.Calculator()
    out = calc._coerce_args("pow", (2, 309))

    assert isinstance(out[0], FakeBigReal)
    assert isinstance(out[1], FakeBigReal)

    out = calc._coerce_args("pow", (1 + 2j, 400))
    assert isinstance(out[0], FakeBigComplex)
    assert isinstance(out[1], FakeBigComplex)


def test_promote_complex_rule(fake_engine):
    calc = fake_engine.Calculator()
    out = calc._promote_complex("sqrt", (-1,))

    assert isinstance(out[0], complex)

    big = FakeBigReal(1)
    out = calc._promote_complex("sqrt", (big,))
    assert out[0] is big


def test_getattr_unknown_raises(fake_engine):
    calc = fake_engine.Calculator()

    with pytest.raises(errors.Error):
        _ = calc.no_such


def test_getattr_type_error(fake_engine):
    calc = fake_engine.Calculator()

    with pytest.raises(errors.Error):
        calc.bad_type(1, 2)


def test_getattr_native_error(fake_engine):
    calc = fake_engine.Calculator()

    with pytest.raises(errors.Error):
        calc.bad_native(1, 2)


def test_getattr_promotes_complex(fake_engine):
    calc = fake_engine.Calculator()

    calc.sqrt(-1)
    name, args = calc._native.calls[-1]

    assert name == "sqrt"
    assert isinstance(args[0], complex)
