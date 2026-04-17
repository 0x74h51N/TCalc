#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Shared expression data and factory functions for benchmark & flamegraph tests."""

from __future__ import annotations

import calc_native
import shiboken6
from PySide6.QtCore import QEventLoop

from tcalc.app_state import CalculatorMode, RenderMode, get_app_state
from tcalc.core.engine import Calculator
from tcalc.core.parser import evaluate_tokens, tokenize_string
from tcalc.ui.widgets.calc.display.expression.expression import Expression
from tcalc.ui.widgets.history.history import History

_DRAIN_MAX_MS = 1000


def drain_events(qapp) -> None:
    qapp.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, _DRAIN_MAX_MS)


# //// Calc pipeline expressions \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

PIPELINE_EXPRESSIONS = {
    "simple": "2 + 3",
    "medium": "2 + 3 * 4 - 5",
    "complex": "sin(45) + cos(30) * tan(60)",
    "heavy": (
        "((1+2)*(3+4))/((5-6)/(7*1e16!))"
        "+ sqrt(16) * log(100)"
        "- floor(3.7) + ceil(2.3)"
        "+ sin(30)^2 + cos(30)^2"
        "- sqrt(144!) * (7 + 8) / (9 - 1)"
    ),
    "sick": (
        "sin(cos(tan(45))) + sqrt(16)*1e16!"
        "* (2^3^2) / (1 + 2 * 3 - 4 / 5)"
        "+ floor(ceil(3.14159)) * log(exp(2))"
        "+ sin(30)^2 + cos(30)^2"
        "- sqrt(144!) * (7 + 8) / (9 - 1)"
        "- ((1+2)*(3+4))/((5-6)/(7*1e16!))"
        "+ sqrt(16) * log(100)"
    ),
}

PIPELINE_THRESHOLDS_MS = {"simple": 1, "medium": 2, "complex": 5, "heavy": 10, "sick": 50}

# //// Paren / LaTeX expressions \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

PAREN_EXPRESSIONS = {
    "paren_simple": "(2 + 3) * 4",
    "paren_medium": "((1+2)*(3+4)) / ((5-6)+(7*8))",
    "paren_complex": "[(34+5)*(4*{3+5})+4] - [{2+1}*(7-3)]",
    "paren_heavy": (
        "[(34+5)*(4*{\\frac{4}{3*5}})+4]"
        " + ((1+2)*(3+4))/((5-6)/(7*8))"
        " - [\\frac{100}{\\sqrt{25}} + {3*\\frac{7}{2}}]"
        " + sin(cos(45)) * (2^3)"
    ),
    "paren_sick": (
        "[(34+5)*(4*{\\frac{4}{{3*5}}})+4]"
        " + {\\frac{\\frac{1}{2}}{\\frac{3}{4}}}"
        " * [((1+2)*(3+4))/((5-6)/(7*8))]"
        " - \\sqrt{\\frac{144}{\\frac{12}{1}}}"
        " + [{\\frac{sin(30)}{cos(60)}} * (tan(45) + 1)]"
        " / ((2^3^2) - {\\frac{100}{\\sqrt{25}}})"
        " - \\sqrt{\\frac{144}{\\frac{12}{1}}}"
        " + [{\\frac{sin(30)}{cos(60)}} * (tan(45) + 1)]"
        " / ((2^3^2) - {\\frac{100}{\\sqrt{25}}})"
    ),
}

# //// Expression render expressions \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

RENDER_EXPRESSIONS = {
    "simple": "\\frac{1}{2}",
    "medium": "\\frac{\\frac{1}{2}}{\\frac{2}{3}}",
    "complex": "\\frac{\\frac{\\frac{1}{2}}{\\frac{2}{3}}}{\\frac{5}{6}}",
    "heavy": (
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
        "}"
        "{(1+\\frac{2}{3+(\\frac{4}{5}+6)})*(7-\\frac{8}{9+10})}"
    ),
    "sick": (
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{"
        "\\frac{\\pow{1}{\\frac{2}{\\pow{3}{\\frac{4}{\\pow{5}{6}}}}}}"
        "{\\pow{7}{\\frac{8}{\\pow{9}{\\frac{10}{11}}}}}"
        "}"
        "{"
        "\\frac{\\pow{2}{\\frac{3}{\\pow{4}{\\frac{5}{\\pow{6}{7}}}}}}"
        "{\\pow{8}{\\frac{9}{\\pow{10}{\\frac{11}{12}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{3}{\\frac{4}{\\pow{5}{\\frac{6}{\\pow{7}{8}}}}}}"
        "{\\pow{9}{\\frac{10}{\\pow{11}{\\frac{12}{13}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{4}{\\frac{5}{\\pow{6}{\\frac{7}{\\pow{8}{9}}}}}}"
        "{\\pow{10}{\\frac{11}{\\pow{12}{\\frac{13}{14}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{5}{\\frac{6}{\\pow{7}{\\frac{8}{\\pow{9}{10}}}}}}"
        "{\\pow{11}{\\frac{12}{\\pow{13}{\\frac{14}{15}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{6}{\\frac{7}{\\pow{8}{\\frac{9}{\\pow{10}{11}}}}}}"
        "{\\pow{12}{\\frac{13}{\\pow{14}{\\frac{15}{16}}}}}"
        "}"
        "}"
        "{"
        "\\frac{\\pow{7}{\\frac{8}{\\pow{9}{\\frac{10}{\\pow{11}{12}}}}}}"
        "{\\pow{13}{\\frac{14}{\\pow{15}{\\frac{16}{17}}}}}"
        "}"
        "}"
    ),
}

RENDER_THRESHOLDS_MS = {"simple": 10, "medium": 20, "complex": 50, "heavy": 150, "sick": 250}

# //// Normalize expressions \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

EXPR_NO_ALIAS = {
    "simple": "2 + 3",
    "medium": "2 + 3 * 4 - 5 * 6",
    "complex": "sin(45) + cos(30) * tan(60)",
    "heavy": "(1 + 2) * (3 - 4) + (5 + 6) - (7 * 8) + (9 - 10)",
    "sick": (
        "(1 + 2) * (3 - 4) + (5 + 6) - (7 * 8) + (9 - 10)"
        " * sin(45) + cos(30) - tan(60) * log(100)"
        " + exp(2) - (2 × 3) * 4 + sin(cos(tan(15)))"
    ),
}

EXPR_WITH_ALIAS = {
    "simple": "2 add 3",
    "medium": "2 add 3 mul 4 sub 5 mul 6",
    "complex": "sin(45) add cos(30) mul tan(60)",
    "heavy": "(1 add 2) mul (3 sub 4) add (5 add 6) sub (7 mul 8) add (9 sub 10)",
    "sick": (
        "(1 add 2) mul (3 sub 4) add (5 add 6) sub (7 mul 8) add (9 sub 10)"
        " mul sin(45) add cos(30) sub tan(60) mul log(100)"
        " add exp(2) sub (2 mul 3) mul 4 add sin(cos(tan(15)))"
    ),
}

NORMALIZE_THRESHOLDS_MS = {"simple": 15, "medium": 20, "complex": 25, "heavy": 30, "sick": 40}

# //// UI integration thresholds \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

SINGLE_EDIT_THRESHOLDS_MS = {
    "simple": 5,
    "medium": 5,
    "complex": 10,
    "heavy": 15,
    "sick": 25,
}

MULTI_EDIT_THRESHOLDS_MS = {
    "simple": 5,
    "medium": 10,
    "complex": 20,
    "heavy": 50,
    "sick": 100,
}


# //// Factory functions \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\


def make_pipeline_func(expr: str):
    calc = Calculator()

    def evaluate():
        tokens = tokenize_string(expr)
        return evaluate_tokens(tokens, calc)

    return evaluate


def make_tokenize_func(expr: str):
    return lambda: tokenize_string(expr)


def make_shunting_func(expr: str):
    tokens = tokenize_string(expr)
    return lambda: calc_native.shunting_yard(tokens)


def make_render_func(qapp, expr: str):
    def render():
        widget = Expression()
        widget.set_plain_text(expr)
        widget.show()
        drain_events(qapp)
        widget.close()
        widget.deleteLater()

    return render


def make_normalize_func(qapp, expr: str):
    def normalize():
        widget = Expression()
        widget.set_plain_text(expr)
        widget.show()
        drain_events(qapp)
        widget.close()
        widget.deleteLater()

    return normalize


def setup_widget(qapp, expr: str) -> Expression:
    widget = Expression()
    widget.set_plain_text(expr)
    widget.show()
    drain_events(qapp)
    return widget


def make_incremental_edit_func(qapp, widget: Expression):
    edits = widget.expression_inputs()
    step = [0]

    def edit_step():
        if not edits:
            return
        target = edits[step[0] % len(edits)]
        text = target.text()

        if text.endswith("1") and len(text) > 1:
            target.setText(text[:-1])
        else:
            target.setText(text + "1")
        drain_events(qapp)

    return edit_step


def make_history_init_func(qapp, math_mode: bool = False, first_paint_only: bool = False):
    app_state = get_app_state()

    def init_history():
        prev_mode = app_state._history_mode
        if math_mode:
            app_state._history_mode = RenderMode.MATH
        try:
            h = History(mode=CalculatorMode.SCIENCE)
            h.show()
            if first_paint_only:
                qapp.sendPostedEvents()
            else:
                drain_events(qapp)
            shiboken6.delete(h)
        finally:
            if math_mode:
                app_state._history_mode = prev_mode

    return init_history


def make_multi_edit_func(qapp, widget: Expression, num_steps: int = 5):
    edits = widget.expression_inputs()

    def multi_edit():
        if not edits:
            return
        for i in range(min(num_steps, len(edits))):
            target = edits[i]
            text = target.text()
            if text.endswith("1") and len(text) > 1:
                target.setText(text[:-1])
            else:
                target.setText(text + "1")
        drain_events(qapp)

    return multi_edit
