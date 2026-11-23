#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The probe tools on the real binding. The values are placeholders: the tools hold no case."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import calc_native
import pytest
from flint import acb, arb, ctx, fmpq
from probes.__main__ import main
from probes.grade import (
    NOT_FINITE,
    NOT_GRADED,
    REF_DIGITS,
    bigreal_residual,
    double_of,
    expected_of_expression,
    grade_of,
)
from probes.layers import layer_rows
from probes.options import READS_CASES, Options, add_arguments, options_from, read_inputs
from probes.rows import (
    UNIT_COLUMN,
    Layer,
    ProbeError,
    Row,
    exact_text,
    format_rows,
    operand_input,
    parse_rows,
    value_text,
)
from probes.testcase import collect
from pytest import param

from tcalc.core.utils import CalcValue

RAD = calc_native.AngleUnit.RAD
# the grader reads the unit a row was computed in from its own column
IN_RAD = ((UNIT_COLUMN, RAD.name),)
BIG = calc_native.BigReal("0.5")
BIG_CX = calc_native.BigComplex(calc_native.BigReal("0.5"), calc_native.BigReal("2"))


@dataclass(frozen=True)
class TextCase:
    value: CalcValue
    value_text: str
    exact_text: str
    id: str


# one row per scalar arm of tcalc::Value
TEXT_CASES = [
    TextCase(3, "3", "3", "int"),
    TextCase(0.5, "0.5", (0.5).hex(), "float"),
    TextCase(1.5 - 0.5j, "(1.5-0.5j)", f"{(1.5).hex()},{(-0.5).hex()}", "complex"),
    TextCase(calc_native.Rational(-1, 2), "-1/2", "-1/2", "Rational"),
    TextCase(BIG, calc_native.decimal_text(BIG, 0), calc_native.decimal_text(BIG, 0), "BigReal"),
    TextCase(
        BIG_CX,
        calc_native.decimal_text(BIG_CX, 0),
        calc_native.decimal_text(BIG_CX, 0),
        "BigComplex",
    ),
]


@pytest.mark.parametrize("case", [param(c, id=c.id) for c in TEXT_CASES])
def test_value_text(case: TextCase) -> None:
    assert value_text(case.value) == case.value_text


@pytest.mark.parametrize("case", [param(c, id=c.id) for c in TEXT_CASES])
def test_exact_text(case: TextCase) -> None:
    assert exact_text(case.value) == case.exact_text


def test_value_text_collection() -> None:
    items = calc_native.evaluate(
        calc_native.tokenize_string("[0.1, 1]"), calc_native.Calculator(), calc_native.AngleUnit.RAD
    )
    assert value_text(items) == "[0.1, 1.0]"


def test_operand_input() -> None:
    operands: list[CalcValue] = [2.0, 3, calc_native.Rational(1, 2), BIG]
    expected = f"+ dbl:{(2.0).hex()} int:3 rat:1/2 big:{calc_native.decimal_text(BIG, 0)}"
    assert operand_input("+", operands) == expected


def test_scalar_rejects_bool() -> None:
    with pytest.raises(Exception, match="bool"):
        exact_text(True)


def test_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    assert "ASCII aliases" in capsys.readouterr().out


@dataclass(frozen=True)
class ExactCase:
    text: str
    expected: fmpq
    id: str


# one row per OP_MEANINGS entry that stays exact, plus the token kinds the walk descends into
EXACT_CASES = [
    ExactCase("(1)+(2)", fmpq(3), "add"),
    ExactCase("1-3", fmpq(-2), "sub"),
    ExactCase("2·3", fmpq(6), "mul"),
    ExactCase("(-7)÷(2)", fmpq(-7, 2), "div"),
    ExactCase("mod(-7,2)", fmpq(-1), "mod truncates"),
    ExactCase("intdiv(-7,2)", fmpq(-3), "intdiv truncates"),
    ExactCase("2^{-2}", fmpq(1, 4), "pow"),
    ExactCase("(8)⌄(3)", fmpq(2), "root"),
    ExactCase("(-8)⌄(3)", fmpq(-2), "real first odd root"),
    ExactCase("(-8)^{1/sqrt(9)}", fmpq(-2), "real first through an exact root"),
    ExactCase("(-8)^{1/log(1000)}", fmpq(-2), "real first through an exact log"),
    ExactCase("sqrt(4)", fmpq(2), "sqrt"),
    ExactCase("cbrt(-27)", fmpq(-3), "cbrt"),
    ExactCase("2²", fmpq(4), "sqr"),
    ExactCase("2³", fmpq(8), "cube"),
    ExactCase("(2)⁻¹", fmpq(1, 2), "recip"),
    ExactCase("-2", fmpq(-2), "negate"),
    ExactCase("+2", fmpq(2), "unary plus"),
    ExactCase("50%", fmpq(1, 2), "percent"),
    ExactCase("log(0.01)", fmpq(-2), "log of a power of ten"),
    ExactCase("⏨2", fmpq(100), "pow10"),
    ExactCase("4!", fmpq(24), "fact"),
    ExactCase("nCr(5,2)", fmpq(10), "choose"),
    ExactCase("nPr(5,2)", fmpq(20), "permute"),
    ExactCase("gcd(4,6)", fmpq(2), "gcd"),
    ExactCase("lcm(4,6)", fmpq(12), "lcm"),
    ExactCase("floor(-2.5)", fmpq(-3), "floor"),
    ExactCase("ceil(-2.5)", fmpq(-2), "ceil"),
    ExactCase("trunc(-2.5)", fmpq(-2), "trunc"),
    ExactCase("sum(1,2,3)", fmpq(6), "sum"),
    ExactCase("mean(1,2,4)", fmpq(7, 3), "mean"),
    ExactCase("mean[1,2,4]", fmpq(7, 3), "mean of a collection"),
    ExactCase("min(3,1,2)", fmpq(1), "min"),
    ExactCase("max(3,1,2)", fmpq(3), "max"),
    ExactCase("median(3,1,2,4)", fmpq(5, 2), "median"),
    ExactCase("\\frac{1}{4}", fmpq(1, 4), "latex fraction"),
    ExactCase("0.1+0.2", fmpq(3, 10), "typed decimals are exact"),
]


@pytest.mark.parametrize("case", [param(c, id=c.id) for c in EXACT_CASES])
def test_expected_of_expression_exact(case: ExactCase) -> None:
    value = expected_of_expression(case.text, RAD)
    assert isinstance(value, fmpq)
    assert value == case.expected


@dataclass(frozen=True)
class BallCase:
    text: str
    real: str
    imag: str
    id: str


# one row per OP_MEANINGS entry that leaves the exact arm, against python-flint called directly
BALL_CASES = [
    BallCase("exp(2)", "7.389056098930650227230427", "0", "exp"),
    BallCase("ln(2)", "0.6931471805599453094172321", "0", "ln"),
    BallCase("log(2)", "0.3010299956639811952137389", "0", "log"),
    BallCase("sin(2)", "0.9092974268256816953960199", "0", "sin"),
    BallCase("cos(2)", "-0.4161468365471423869975682", "0", "cos"),
    BallCase("tan(2)", "-2.185039863261518991643306", "0", "tan"),
    BallCase("sinh(2)", "3.626860407847018767668214", "0", "sinh"),
    BallCase("cosh(2)", "3.762195691083631459562213", "0", "cosh"),
    BallCase("tanh(2)", "0.9640275800758168839464137", "0", "tanh"),
    BallCase("asin(0.5)", "0.5235987755982988730771072", "0", "asin"),
    BallCase("acos(0.5)", "1.047197551196597746154214", "0", "acos"),
    BallCase("atan(2)", "1.107148717794090503017065", "0", "atan"),
    BallCase("asinh(2)", "1.443635475178810342493277", "0", "asinh"),
    BallCase("acosh(2)", "1.316957896924816708625046", "0", "acosh"),
    BallCase("atanh(0.5)", "0.5493061443340548456976226", "0", "atanh"),
    BallCase("gamma(0.5)", "1.772453850905516027298167", "0", "gamma"),
    BallCase("(0.5)!", "0.8862269254527580136490837", "0", "fact of a fraction"),
    BallCase("polar(2)", "-0.4161468365471423869975682", "0.9092974268256816953960199", "polar"),
    BallCase("(2)⌄(3)", "1.259921049894873164767211", "0", "root"),
    BallCase("(-2)^{0.5}", "0", "1.414213562373095048801689", "principal even root"),
    BallCase("mod(-7,π)", "-0.716814692820413523074713", "0", "mod truncates a ball"),
    BallCase("intdiv(-7,π)", "-2", "0", "intdiv truncates a ball"),
    BallCase("var(1,2,4)", "2.333333333333333333333333", "0", "var"),
    BallCase("varp(1,2,4)", "1.555555555555555555555556", "0", "varp"),
    BallCase("std(1,2,4)", "1.527525231651946668862682", "0", "std"),
    BallCase("stdp(1,2,4)", "1.247219128924647128527916", "0", "stdp"),
    BallCase("3+2i", "3", "2", "imaginary literal"),
    # on the cut above 1 TCalc takes C99's side (cmath), which python-flint does not
    BallCase("acos(2)", "0", "-1.316957896924816708625046", "acos on the cut above 1"),
    BallCase(
        "asin(2)",
        "1.570796326794896619231322",
        "1.316957896924816708625046",
        "asin on the cut above 1",
    ),
    BallCase(
        "atanh(2)",
        "0.5493061443340548456976226",
        "1.570796326794896619231322",
        "atanh on the cut above 1",
    ),
    # where python-flint and cmath already agree, the reference stays python-flint's
    BallCase(
        "acos(-2)",
        "3.141592653589793238462643",
        "-1.316957896924816708625046",
        "acos on the cut below -1",
    ),
    BallCase(
        "asin(-2)",
        "-1.570796326794896619231322",
        "1.316957896924816708625046",
        "asin on the cut below -1",
    ),
    BallCase(
        "atanh(-2)",
        "-0.5493061443340548456976226",
        "1.570796326794896619231322",
        "atanh on the cut below -1",
    ),
    BallCase(
        "acos(2+i)",
        "0.5073563032171445630418297",
        "-1.469351744368185273255844",
        "acos off the cut",
    ),
    BallCase(
        "asin(2+i)", "1.063440023577752056189492", "1.469351744368185273255844", "asin off the cut"
    ),
    BallCase(
        "atanh(2+i)",
        "0.4023594781085250936501898",
        "1.338972522294493561124194",
        "atanh off the cut",
    ),
]

CLOSE = arb("1e-24")


@pytest.mark.parametrize("case", [param(c, id=c.id) for c in BALL_CASES])
def test_expected_of_expression_ball(case: BallCase) -> None:
    value = expected_of_expression(case.text, RAD)
    assert value is not None
    # the table's 25 digits are read at more than the default 15
    with ctx.workdps(REF_DIGITS):
        assert abs(acb(value) - acb(arb(case.real), arb(case.imag))) < CLOSE


@pytest.mark.parametrize(
    "text",
    [
        param("x+1", id="variable"),
        param("log_{2}(8)", id="subscript"),
        param("[1,2]", id="collection"),
    ],
)
def test_expected_of_expression_not_graded(text: str) -> None:
    assert expected_of_expression(text, RAD) is None


def test_expected_of_expression_constant() -> None:
    value = expected_of_expression("2π", RAD)
    assert isinstance(value, acb)
    assert double_of(value) == 2 * math.pi


def test_bigreal_residual_of_exact_value() -> None:
    third = calc_native.apply(
        calc_native.Calculator(),
        calc_native.OpId.Div,
        [calc_native.BigReal("1"), calc_native.BigReal("3")],
        calc_native.AngleUnit.RAD,
    )
    assert isinstance(third, calc_native.BigReal)
    _, relative = bigreal_residual(third, fmpq(1, 3))
    # a BigReal holds about 72 digits: the residual is its own rounding, far under 1e-70
    assert abs(float(relative)) < 1e-70


@dataclass(frozen=True)
class DoubleCase:
    ball: acb
    expected: float | complex | None
    id: str


DOUBLE_CASES = [
    DoubleCase(acb(fmpq(1, 2)), 0.5, "exact half"),
    DoubleCase(acb(arb(1, 1e-10)), None, "too wide for one double"),
    DoubleCase(acb(fmpq(1, 2), fmpq(-1, 4)), 0.5 - 0.25j, "complex"),
    DoubleCase(acb(0, fmpq(1, 2)), 0.5j, "imaginary"),
]


@pytest.mark.parametrize("case", [param(c, id=c.id) for c in DOUBLE_CASES])
def test_double_of(case: DoubleCase) -> None:
    assert double_of(case.ball) == case.expected


@dataclass(frozen=True)
class GradeCase:
    row: Row
    error: str
    id: str


# rows TCalc writes that the grader cannot measure: each is graded with a word, never a traceback
GRADE_CASES = [
    GradeCase(
        Row("1÷0", Layer.EVAL, "CalculatorError", "Math error", IN_RAD), NOT_GRADED, "error row"
    ),
    GradeCase(
        Row("sin dbl:inf", Layer.APPLY, "float", "nan", IN_RAD), NOT_GRADED, "infinite operand"
    ),
    GradeCase(Row("1e400", Layer.EVAL, "float", "1.0", IN_RAD), NOT_FINITE, "infinite expected"),
    GradeCase(
        Row("(-8)⌄(3)", Layer.EVAL, "float", "-2.0", IN_RAD),
        "0 ulp",
        "double against an exact value",
    ),
    GradeCase(
        Row("sqrt(4)", Layer.EVAL, "Rational", "2", IN_RAD), "exact", "exact against an exact value"
    ),
    GradeCase(
        Row("log(2)·0+2", Layer.EVAL, "Rational", "2", IN_RAD), "exact", "exact against a ball"
    ),
]


@pytest.mark.parametrize("case", [param(c, id=c.id) for c in GRADE_CASES])
def test_grade_of(case: GradeCase) -> None:
    assert grade_of(case.row).error == case.error


GOLDEN = "tests/py/e2e/test_eval_e2e.py::test_native_eval_golden[precedence-mul-over-add]"
ROOTS = "tests/py/e2e/test_eval_e2e.py::test_root_correctly_rounded"


def test_collect_one_row() -> None:
    (row,) = collect(GOLDEN, None)
    assert row.params["expr"] == "1+2*3"
    assert row.params["expected_value"] == 7.0


def test_collect_keyword_rows_of_dataclass_cases() -> None:
    rows = collect(ROOTS, "root-cube")
    assert rows
    assert all(type(row.params["case"]).__name__ == "RootCase" for row in rows)


def test_collect_nothing() -> None:
    with pytest.raises(ProbeError, match="no parametrized case"):
        collect("tests/py/e2e/test_eval_e2e.py::nope", None)


def _options(*argv: str) -> Options:
    """Options as the command line gives them."""
    parser = argparse.ArgumentParser()
    add_arguments(parser, READS_CASES)
    return options_from(parser.parse_args(argv))


def test_read_inputs_from_a_test() -> None:
    options = _options("--test", GOLDEN, "--field", "expr")
    (one,) = read_inputs(options)
    assert one.text == "1+2*3"
    assert ("test.expected_value", "7.0") in one.beside


def test_test_without_field_lists_rows(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["eval", "--test", GOLDEN]) == 0
    assert "expr=" in capsys.readouterr().out


# the checks the removed unit tests made, through the real command and the real binding


def test_definitions_reach_the_inputs() -> None:
    options = _options("@A+@AB", "--def", "A=1", "--def", "AB=2")
    assert [one.text for one in read_inputs(options)] == ["(1)+(2)"]


@pytest.mark.parametrize("text", [param("@B", id="undefined"), param("@+1", id="no name")])
def test_definitions_reject(text: str) -> None:
    options = _options("--", text)
    with pytest.raises(ProbeError):
        read_inputs(options)


def test_rows_read_back() -> None:
    rows = [
        Row("1/2", Layer.EVAL, "Rational", "1/2", (("note", "a"),)),
        Row("2+2", Layer.APPLY, "int", "4"),
    ]
    assert parse_rows(format_rows(rows)) == [
        rows[0],
        Row("2+2", Layer.APPLY, "int", "4", (("note", ""),)),
    ]


def _table(path: Path, value: str) -> str:
    path.write_text(format_rows([Row("sqrt(2)", Layer.EVAL, "float", value, IN_RAD)]))
    return str(path)


def test_grade_compares_two_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    worse = repr(math.nextafter(math.sqrt(2), 2.0))
    old, new = _table(tmp_path / "old", worse), _table(tmp_path / "new", repr(math.sqrt(2)))
    assert main(["grade", old, new]) == 0
    assert "better 1 worse 0" in capsys.readouterr().out


def test_grade_rejects_a_repeated_input(tmp_path: Path) -> None:
    path = tmp_path / "twice"
    row = Row("sqrt(2)", Layer.EVAL, "float", "1.0", IN_RAD)
    path.write_text(format_rows([row, row]))
    assert main(["grade", str(path), str(path)]) == 2


def test_field_names_a_missing_path() -> None:
    options = _options("--test", GOLDEN, "--field", "nope")
    with pytest.raises(ProbeError, match="nope.*expr"):
        read_inputs(options)


@dataclass(frozen=True)
class OpAloneCase:
    text: str
    input: str
    value: str
    id: str


# the last op alone, read from each token kind that carries one
OP_ALONE_CASES = [
    OpAloneCase("(2)⁻¹", "⁻¹ int:2", "1/2", "op"),
    OpAloneCase("\\root{8}{3}", "⌄ int:8 int:3", "2/1", "latex"),
    OpAloneCase("sqrt(4)", "√ int:4", "2/1", "call"),
    OpAloneCase("max(1,2,3)", "max list:[1,2,3]", "3", "variadic call"),
    OpAloneCase("-sin(π)", "u- rat:0/1", "0/1", "exact inner op"),
    OpAloneCase("A=2+1", "+ int:2 int:1", "3/1", "assignment"),
    OpAloneCase("log_{2}8", "log int:8 int:2", "3/1", "log with its base"),
    OpAloneCase("\\root{2}", "⌄ int:2 rat:2/1", "1.4142135623730951", "empty slot"),
]


@pytest.mark.parametrize("case", [param(c, id=c.id) for c in OP_ALONE_CASES])
def test_layer_rows_op_alone(case: OpAloneCase) -> None:
    rows = {row.layer: row for row in layer_rows(case.text, calc_native.AngleUnit.RAD)}
    assert (rows[Layer.APPLY].input, rows[Layer.APPLY].value) == (case.input, case.value)
