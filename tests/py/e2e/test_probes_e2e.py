#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The probe tools on the real binding. The values are placeholders: the tools hold no case."""

from __future__ import annotations

from dataclasses import dataclass

import calc_native
import pytest
from probes.__main__ import main
from probes.rows import exact_text, operand_input, value_text
from pytest import param

from tcalc.core.utils import CalcValue

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
