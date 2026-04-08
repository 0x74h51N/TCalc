#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Expression widget rendering benchmark tests.

Tests the performance of Expression widget's node creation and rendering.
"""

from __future__ import annotations

import pytest

from tests.benchmark.expressions import (
    RENDER_EXPRESSIONS,
    RENDER_THRESHOLDS_MS,
    make_render_func,
)

from .conftest import ROUNDS_RENDER, run_benchmark


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(RENDER_EXPRESSIONS))
def test_expression_render_benchmark(qapp, benchmark, name: str):
    """Test that Expression widget rendering stays under threshold."""
    run_benchmark(
        benchmark,
        make_render_func(qapp, RENDER_EXPRESSIONS[name]),
        group="Expression Node Widgets' Render",
        name=name,
        threshold_ms=RENDER_THRESHOLDS_MS[name],
        rounds=ROUNDS_RENDER,
    )
