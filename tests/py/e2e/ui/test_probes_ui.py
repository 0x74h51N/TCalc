#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The probe commands that open the editor, on the real editor and binding. Placeholder values."""

from __future__ import annotations

import calc_native
from probes.eval_cmd import eval_rows
from probes.rows import Layer

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
