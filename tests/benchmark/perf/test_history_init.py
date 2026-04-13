#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest

from tcalc.app_state import CalculatorMode
from tcalc.ui.widgets.history.history import History
from tests.benchmark.conftest import HISTORY_SCENARIO_COUNTS

from .conftest import run_benchmark


@pytest.mark.benchmark
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_history_init_benchmark(qapp, benchmark, history_seed):
    def init_history():
        h = History(mode=CalculatorMode.SCIENCE)
        qapp.processEvents()
        h.close()
        h.deleteLater()
        qapp.processEvents()

    run_benchmark(
        benchmark,
        init_history,
        group="History Init",
        name=history_seed,
        rounds=5,
        warmup_rounds=2,
    )
