#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from dataclasses import dataclass

import calc_native
import pytest

from tcalc.core.native_eval import evaluate_branch
from tcalc.core.parser import tokenize
from tcalc.ui.controller.utils import format_result


def _eval(expr: str):
    return evaluate_branch(tokenize(expr), calc_native.Calculator(), calc_native.AngleUnit.RAD)


def _frag(x) -> str:
    # A Collection's repr is valid expression syntax ("(1, 2)" / "[1, 2]").
    return repr(x) if isinstance(x, calc_native.Collection) else str(x)


def _list(items):
    return _eval("[" + ",".join(_frag(x) for x in items) + "]")


def _point(items):
    return _eval("(" + ",".join(_frag(x) for x in items) + ")")


# -- value -> string -------------------------------------------------------
#
# group=False is the tokenizer-safe default (no thousands separators) so the
# output can be fed back into the editor; group=True is for display widgets.


@dataclass(frozen=True, slots=True)
class FormatCase:
    value: object
    group: bool
    expected: str


FORMAT_CASES = [
    pytest.param(FormatCase(_list([1, 2, 3]), False, "[1, 2, 3]"), id="list-of-ints"),
    pytest.param(FormatCase(_point([1, 2]), False, "(1, 2)"), id="point"),
    pytest.param(
        FormatCase(_list([_point([1, 2]), _point([3, 4])]), False, "[(1, 2), (3, 4)]"),
        id="list-of-points",
    ),
    pytest.param(FormatCase(_list([]), False, "[]"), id="empty-list"),
    pytest.param(
        FormatCase(_list([1000000, 2, 3]), False, "[1000000, 2, 3]"), id="collection-keeps-commas"
    ),
    pytest.param(FormatCase(_eval("[2, 9e400]"), False, "[2, 9e+400]"), id="list-of-bigreal"),
    pytest.param(FormatCase(_eval("(2.5, 1e400)"), False, "(2.5, 1e+400)"), id="point-of-bigreal"),
    pytest.param(FormatCase(_eval("[sqrt(-1), 2]"), False, "[i, 2]"), id="list-of-complex"),
    pytest.param(
        FormatCase(
            _eval("[" + ",".join(["9e400"] * 101) + "]"),
            False,
            "[9e+400, 9e+400, 9e+400, 9e+400, ..., 9e+400, 9e+400]",
        ),
        id="list-past-preview-cap",
    ),
    pytest.param(FormatCase(1234567.89, False, "1234567.89"), id="float-plain"),
    pytest.param(FormatCase(1234567.0, False, "1234567"), id="float-integral-plain"),
    pytest.param(FormatCase(1234567.89, True, "1,234,567.89"), id="float-grouped"),
    pytest.param(FormatCase(1234567.0, True, "1,234,567"), id="float-integral-grouped"),
    pytest.param(FormatCase(3 + 4j, False, "3+4i"), id="complex"),
    pytest.param(
        FormatCase(_eval("10^{16}+1"), False, "10000000000000001"), id="exact-int-past-double"
    ),
    pytest.param(
        FormatCase(_eval("9223372036854775807"), False, "9223372036854775807"),
        id="int64-max-literal",
    ),
    pytest.param(FormatCase(_eval("2+3"), False, "5"), id="exact-int-small"),
    pytest.param(FormatCase(_eval("10^{6}+1"), True, "1,000,001"), id="exact-int-grouped"),
    pytest.param(FormatCase(_eval("\\frac{1}{4}"), False, "0.25"), id="exact-fraction-decimal"),
    pytest.param(FormatCase(_eval("10000000000"), False, "10000000000"), id="int-written-in-full"),
    pytest.param(FormatCase(_eval("1/3"), True, "0.33333333333333333333"), id="third"),
    pytest.param(FormatCase(_eval("2/3"), True, "0.66666666666666666667"), id="two-thirds-rounds"),
    pytest.param(
        FormatCase(_eval("-2/7"), True, "-0.28571428571428571429"), id="negative-fraction"
    ),
    pytest.param(
        FormatCase(_eval("9007199254740993/2"), True, "4,503,599,627,370,496.5"),
        id="half-past-2^53",
    ),
    pytest.param(
        FormatCase(_eval("0.30000000000000004"), True, "0.30000000000000004"), id="seventeen-digits"
    ),
    pytest.param(FormatCase(_eval("1/10000"), True, "0.0001"), id="ten-thousandth"),
    pytest.param(
        FormatCase(_eval("1/30000"), True, "3.3333333333333333333e-05"), id="small-repeating"
    ),
    pytest.param(FormatCase(_eval("1/10000000"), True, "1e-07"), id="small-exact"),
    pytest.param(
        FormatCase(_eval("9223372036854775807/3"), True, "3,074,457,345,618,258,602.3"),
        id="int64-max-third",
    ),
    pytest.param(
        FormatCase(_eval("100000000000.5"), True, "100,000,000,000.5"), id="past-1e10-with-fraction"
    ),
    pytest.param(FormatCase(_eval("10000000000"), True, "1e+10"), id="int-zeros-abbreviate"),
    pytest.param(FormatCase(_eval("-10000000000"), True, "-1e+10"), id="negative-zeros-abbreviate"),
    pytest.param(
        FormatCase(_eval("12345678900"), True, "1.23456789e+10"), id="trailing-zeros-drop"
    ),
    pytest.param(
        FormatCase(_eval("12345678901"), True, "12,345,678,901"), id="no-trailing-zero-full"
    ),
    pytest.param(FormatCase(_eval("2^{40}"), True, "1,099,511,627,776"), id="power-full"),
    pytest.param(FormatCase(_eval("9999999999"), True, "9,999,999,999"), id="under-1e10-boundary"),
    pytest.param(
        FormatCase(_eval("2^{63}"), True, "9,223,372,036,854,775,808"), id="bigreal-exact"
    ),
    pytest.param(
        FormatCase(_eval("1e400/3"), True, "3.3333333333333333333e+399"), id="bigreal-past-double"
    ),
    pytest.param(FormatCase(_eval("1e10"), True, "1e+10"), id="double-zeros-abbreviate"),
    pytest.param(
        FormatCase(_eval("2^{0.5}*1e12"), True, "1.414213562373095e+12"), id="double-sixteen-digits"
    ),
    pytest.param(FormatCase(_eval("1e-7"), True, "1e-07"), id="double-small"),
    pytest.param(FormatCase(_eval("1e400i"), True, "1e+400i"), id="bigcomplex-imaginary-alone"),
    pytest.param(FormatCase(_eval("1e-400i"), True, "1e-400i"), id="bigcomplex-tiny-imaginary"),
    pytest.param(FormatCase(_eval("1e400i-1e400i"), True, "0"), id="bigcomplex-zero"),
    pytest.param(FormatCase(_eval("(1e400i)^{2}"), True, "-1e+800"), id="bigcomplex-real-alone"),
    pytest.param(
        FormatCase(_eval("(-4e400)⌄(-2)"), True, "-5e-201i"), id="bigcomplex-negative-imaginary"
    ),
    pytest.param(
        FormatCase(_eval("sqrt(-1e400)/3+1234"), True, "1,234+3.3333333333333333333e+199i"),
        id="bigcomplex-both",
    ),
    pytest.param(FormatCase(_eval("10^{10}-1/10^{12}"), True, "1e+10"), id="rounds-up-to-1e10"),
    pytest.param(FormatCase(_eval("cosh(1000)"), True, "inf"), id="double-inf"),
    pytest.param(FormatCase(_eval("1e308*10"), True, "1e+309"), id="double-overflow-mul"),
    pytest.param(FormatCase(_eval("1e308+1e308"), True, "2e+308"), id="double-overflow-add"),
    pytest.param(
        FormatCase(_eval("1.5e308*1.5"), True, "2.25e+308"), id="double-overflow-fraction"
    ),
    pytest.param(FormatCase(_eval("1e200*1e200"), True, "1e+400"), id="double-overflow-square"),
    pytest.param(FormatCase(_eval("1e200i*1e200i"), True, "-1e+400"), id="complex-overflow"),
    pytest.param(FormatCase(_eval("1e308*10/10"), True, "1e+308"), id="overflow-and-back"),
    pytest.param(FormatCase(_eval("1e308*10-10^{309}"), True, "0"), id="overflow-equals-exact"),
    pytest.param(
        FormatCase(_eval("sqrt(2)*1e308*10"), True, "1.4142135623730951e+309"),
        id="computed-double-keeps-its-digits",
    ),
]


@pytest.mark.parametrize("case", FORMAT_CASES)
def test_format_result(case):
    assert format_result(case.value, group=case.group) == case.expected


# -- output parses back to one token ---------------------------------------

ROUND_TRIP_CASES = [
    pytest.param(1234567.89, calc_native.TokenKind.Number, id="float"),
    pytest.param(_eval("10^{16}+1"), calc_native.TokenKind.Number, id="exact-int-past-double"),
    pytest.param(_list([1000000, 2, 3]), calc_native.TokenKind.Paren, id="collection"),
    pytest.param(_eval("[2, 9e400]"), calc_native.TokenKind.Paren, id="collection-of-bigreal"),
]


@pytest.mark.parametrize("value,expected_kind", ROUND_TRIP_CASES)
def test_default_output_round_trips(value, expected_kind):
    # The grouped form "1,234,567.89" would split into 5 tokens; the default form
    # must come back as one.
    text = format_result(value)
    toks = list(tokenize(text).tokens)
    assert len(toks) == 1, f"{text!r} -> {[t.kind for t in toks]}"
    assert toks[0].kind == expected_kind


# The default text is written into the expression (=, collection items): it evaluates back to the same
# value. The native number types have no ==, so the difference is read as text.
@pytest.mark.parametrize(
    "expr",
    [
        pytest.param("10000000000", id="int-zeros"),
        pytest.param("2^{40}", id="whole-rational"),
        pytest.param("10^{16}+1", id="int-past-double"),
        pytest.param("100000000001234567890", id="bigreal-twenty-digits"),
        pytest.param("1e400i", id="bigcomplex"),
    ],
)
def test_default_output_reads_back(expr):
    diff = _eval(f"{format_result(_eval(expr))}-({expr})")
    assert str(diff) in ("0", "0+0i")


# MR writes a fraction as \frac (keep_rational): it evaluates back to the same Rational.
@pytest.mark.parametrize(
    "expr",
    [
        pytest.param("1/3", id="third"),
        pytest.param("-2/7", id="negative-fraction"),
        pytest.param("9007199254740993/2", id="half-past-2^53"),
    ],
)
def test_fraction_text_reads_back(expr):
    from tcalc.core.utils import fraction_text

    diff = _eval(f"{fraction_text(_eval(expr))}-({expr})")
    assert str(diff) == "0"
