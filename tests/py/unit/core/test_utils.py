from __future__ import annotations

from types import SimpleNamespace

import pytest

from tcalc.core import utils as utils_mod

param = pytest.param


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        param("123", 123, id="int"),
        param("3.14", 3.14, id="float"),
    ],
)
def test_parse_number_token_basic(fake_calc_native, literal, expected):
    assert utils_mod.parse_number_token(literal) == expected


def test_parse_number_token_scientific_bigreal(fake_calc_native):
    out = utils_mod.parse_number_token("1e-3")

    assert out.__class__.__name__ == "FakeBigReal"
    assert str(out) == "1e-3"


def test_parse_number_token_scientific_fallback_float(monkeypatch):
    from tests.py.unit.core.conftest import FakeBigRealFail

    monkeypatch.setattr(
        utils_mod,
        "calc_native",
        SimpleNamespace(BigReal=FakeBigRealFail),
        raising=False,
    )

    assert utils_mod.parse_number_token("1e-3") == 0.001


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        param("i", 1j, id="i"),
        param("I", 1j, id="I"),
        param("j", 1j, id="j"),
        param("J", 1j, id="J"),
        param("3i", 3j, id="3i"),
        param("i3", 3j, id="i3"),
        param("3j", 3j, id="3j"),
        param("j3", 3j, id="j3"),
        param("-2i", -2j, id="-2i"),
        param("i-2", -2j, id="i-2"),
        param("-2j", -2j, id="-2j"),
        param("j-2", -2j, id="j-2"),
    ],
)
def test_parse_number_token_imaginary(literal, expected, fake_calc_native):
    assert utils_mod.parse_number_token(literal) == expected


def test_parse_number_token_imaginary_scientific(fake_calc_native):
    assert utils_mod.parse_number_token("1e-3i") == 0.001j


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        param(3.0, True, id="int"),
        param(2.0000000000001, True, id="epsilon-close"),
        param(2.1, False, id="fractional"),
    ],
)
def test_is_int_like(value, expected):
    assert utils_mod.is_int_like(value) is expected
