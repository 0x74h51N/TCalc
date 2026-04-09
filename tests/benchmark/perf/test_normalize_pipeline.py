#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Normalize benchmark tests.

Tests the REAL normalize pipeline through Expression widget.
Text input -> controller -> Expression -> Calc_native::tokenize -> apply_normalized_text flow.
"""

from __future__ import annotations

import pytest

from tests.benchmark.expressions import (
    EXPR_NO_ALIAS,
    EXPR_WITH_ALIAS,
    NORMALIZE_THRESHOLDS_MS,
    make_normalize_func,
)

from .conftest import run_benchmark


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(EXPR_NO_ALIAS))
def test_normalize_no_alias(qapp, benchmark, name: str):
    """Normalize expression without aliases (baseline - no alias conversion)."""
    run_benchmark(
        benchmark,
        make_normalize_func(qapp, EXPR_NO_ALIAS[name]),
        group="Normalize",
        name=f"no_alias_{name}",
        threshold_ms=NORMALIZE_THRESHOLDS_MS[name],
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(EXPR_WITH_ALIAS))
def test_normalize_with_alias(qapp, benchmark, name: str):
    """Normalize expression with aliases (measures alias->symbol conversion cost)."""
    run_benchmark(
        benchmark,
        make_normalize_func(qapp, EXPR_WITH_ALIAS[name]),
        group="Normalize",
        name=f"with_alias_{name}",
        threshold_ms=NORMALIZE_THRESHOLDS_MS[name],
    )
