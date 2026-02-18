"""Normalize benchmark tests.

Tests the REAL normalize pipeline through Expression widget.
Text input -> controller -> Expression -> Calc_native::tokenize -> apply_normalized_text flow.
"""

from __future__ import annotations

import pytest

from tcalc.ui.widgets.calc.display.expression.expression import Expression

from .conftest import run_benchmark

# Expressions WITHOUT aliases (already using symbols) - baseline
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

# Expressions WITH aliases (need normalization)
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

THRESHOLDS_MS = {"simple": 15, "medium": 20, "complex": 25, "heavy": 30, "sick": 40}


def _make_normalize_func(qapp, expr: str):
    """Create function that tests real normalize pipeline through Expression widget."""

    def normalize():
        widget = Expression()
        widget.show()
        widget.set_plain_text(expr)
        qapp.processEvents()
        widget.close()
        widget.deleteLater()
        qapp.processEvents()

    return normalize


@pytest.mark.benchmark
@pytest.mark.parametrize("name", ["simple", "medium", "complex", "heavy", "sick"])
def test_normalize_no_alias(qapp, benchmark, name: str):
    """Normalize expression without aliases (baseline - no alias conversion)."""
    run_benchmark(
        benchmark,
        _make_normalize_func(qapp, EXPR_NO_ALIAS[name]),
        group="Normalize",
        name=f"no_alias_{name}",
        threshold_ms=THRESHOLDS_MS[name],
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", ["simple", "medium", "complex", "heavy", "sick"])
def test_normalize_with_alias(qapp, benchmark, name: str):
    """Normalize expression with aliases (measures alias→symbol conversion cost)."""
    run_benchmark(
        benchmark,
        _make_normalize_func(qapp, EXPR_WITH_ALIAS[name]),
        group="Normalize",
        name=f"with_alias_{name}",
        threshold_ms=THRESHOLDS_MS[name],
    )
