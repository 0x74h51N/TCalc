from __future__ import annotations

from types import SimpleNamespace

import pytest

from tcalc.core import utils as utils_mod


def test_parse_number_token_int(fake_calc_native):
    assert utils_mod.parse_number_token("123") == 123


def test_parse_number_token_float(fake_calc_native):
    assert utils_mod.parse_number_token("3.14") == 3.14


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
        ("i", 1j),
        ("I", 1j),
        ("j", 1j),
        ("J", 1j),
        ("3i", 3j),
        ("i3", 3j),
        ("3j", 3j),
        ("j3", 3j),
        ("-2i", -2j),
        ("i-2", -2j),
        ("-2j", -2j),
        ("j-2", -2j),
    ],
)
def test_parse_number_token_imaginary(literal, expected, fake_calc_native):
    assert utils_mod.parse_number_token(literal) == expected


def test_parse_number_token_imaginary_scientific(fake_calc_native):
    assert utils_mod.parse_number_token("1e-3i") == 0.001j


def test_is_int_like():
    assert utils_mod.is_int_like(3.0)
    assert utils_mod.is_int_like(2.0000000000001)
    assert not utils_mod.is_int_like(2.1)
