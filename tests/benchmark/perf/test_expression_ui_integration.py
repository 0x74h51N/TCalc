#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Expression UI integration benchmark tests.

Measures incremental edit performance: after initial render,
how fast do individual QLineEdit changes propagate through the pipeline.
"""

from __future__ import annotations

import pytest

from tests.benchmark.expressions import (
    MULTI_EDIT_THRESHOLDS_MS,
    RENDER_EXPRESSIONS,
    SINGLE_EDIT_THRESHOLDS_MS,
    make_incremental_edit_func,
    make_multi_edit_func,
    setup_widget,
)

from .conftest import ROUNDS_RENDER, run_benchmark


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(RENDER_EXPRESSIONS))
def test_single_edit_benchmark(qapp, benchmark, name: str):
    widget = setup_widget(qapp, RENDER_EXPRESSIONS[name])
    try:
        run_benchmark(
            benchmark,
            make_incremental_edit_func(qapp, widget),
            group="Expression UI Integration — Single Edit",
            name=name,
            threshold_ms=SINGLE_EDIT_THRESHOLDS_MS[name],
            rounds=ROUNDS_RENDER,
        )
    finally:
        widget.close()
        widget.deleteLater()


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(RENDER_EXPRESSIONS))
def test_multi_edit_benchmark(qapp, benchmark, name: str):
    widget = setup_widget(qapp, RENDER_EXPRESSIONS[name])
    try:
        run_benchmark(
            benchmark,
            make_multi_edit_func(qapp, widget, num_steps=5),
            group="Expression UI Integration — Multi Edit (5 steps)",
            name=name,
            threshold_ms=MULTI_EDIT_THRESHOLDS_MS[name],
            rounds=ROUNDS_RENDER,
        )
    finally:
        widget.close()
        widget.deleteLater()
