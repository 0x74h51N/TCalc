#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The probe commands that open the editor or render widgets, on the real app and binding."""

from __future__ import annotations

from pathlib import Path

import calc_native
import pytest
from probes.__main__ import main
from probes.eval_cmd import eval_rows
from probes.rows import PLAIN_COLUMN, Layer, Row, parse_rows
from PySide6.QtGui import QImage

from tcalc.ui.widgets.calc.display.expression.expression import Expression


def test_eval_rows(expression_widget: Expression) -> None:
    rows = {
        row.layer: row for row in eval_rows(expression_widget, "1/3", calc_native.AngleUnit.RAD)
    }
    assert (rows[Layer.EVAL].type, rows[Layer.EVAL].value) == ("Rational", "1/3")
    # = writes the decimal, which a typed decimal reads back as BigReal
    assert rows[Layer.ROUND_TRIP].value.startswith("BigReal")


def test_eval_rows_error(expression_widget: Expression) -> None:
    rows = {
        row.layer: row for row in eval_rows(expression_widget, "1/0", calc_native.AngleUnit.RAD)
    }
    assert rows[Layer.EVAL].type == "Error"


def _table(capsys: pytest.CaptureFixture[str], argv: list[str]) -> list[Row]:
    assert main(argv) == 0
    return parse_rows(capsys.readouterr().out)


@pytest.mark.usefixtures("isolated_app")
def test_editor_steps(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    picture = tmp_path / "e.png"
    rows = _table(
        capsys,
        ["editor", "\\frac{1}{2}", "--step", "left", "--step", "text:7", "--png", str(picture)],
    )
    assert [row.input for row in rows] == ["\\frac{1}{2}", "left", "text:7"]
    assert all(row.value.count("|") == 1 for row in rows)
    assert dict(rows[-1].extra)[PLAIN_COLUMN] == "\\frac{1}{72}"
    assert QImage(str(picture)).width() > 0


@pytest.mark.usefixtures("isolated_app")
def test_render_tree(capsys: pytest.CaptureFixture[str]) -> None:
    rows = _table(capsys, ["render", "\\root{8}{3}"])
    assert rows[-1].layer == Layer.TREE
    assert rows[-1].value == "'' Root<'8' ; '3'> ''"
