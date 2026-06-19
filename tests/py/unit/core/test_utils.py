#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import math
import time

import pytest

from tcalc.core import constants as constants_mod
from tcalc.core import utils as utils_mod

param = pytest.param


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        param("e", math.e, id="constant-e"),
    ],
)
def test_constant_is_float(literal: str, expected: float) -> None:
    value = constants_mod.CONSTANTS[literal]
    assert isinstance(value, float)
    assert value == pytest.approx(expected)


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        param("123", 123, id="int"),
        param("3.14", 3.14, id="float"),
    ],
)
def test_parse_number_token_basic(fake_calc_native, literal, expected):
    assert utils_mod.parse_number_token(literal) == expected


@pytest.mark.parametrize(
    ("literal", "expected", "expected_type"),
    [
        param("10e+0", 10.0, float, id="scientific-notation-exponent-zero"),
        param("10e+1", 100.0, float, id="scientific-notation"),
        param("1e-3", 0.001, float, id="scientific-notation-small"),
        param("1e309", None, "FakeBigReal", id="scientific-notation-overflow-bigreal"),
        param("1e-400", None, "FakeBigReal", id="scientific-notation-underflow-bigreal"),
    ],
)
def test_parse_number_token_scientific_notation(
    fake_calc_native, literal: str, expected: float | None, expected_type: object
) -> None:
    out = utils_mod.parse_number_token(literal)

    if expected_type is float:
        assert out == pytest.approx(expected)
        return

    assert out.__class__.__name__ == expected_type
    assert str(out) == literal


def test_parse_number_token_huge_exponent_no_hang(fake_calc_native):
    # A BigReal result ("1.2e+410909525") fed back into the editor is re-parsed.
    # Decimal.as_integer_ratio() would materialize a ~410M-digit int and hang;
    # parse_number_token must bail to BigReal via the adjusted() guard instead.
    start = time.monotonic()
    out = utils_mod.parse_number_token("1.243693235223141e+410909525")
    elapsed = time.monotonic() - start

    assert elapsed < 1.0, f"parse_number_token hung ({elapsed:.1f}s) on a huge-exponent decimal"
    assert out.__class__.__name__ == "FakeBigReal"


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
