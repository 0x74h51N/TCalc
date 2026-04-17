#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import gc

import pytest

from tests.benchmark.conftest import HISTORY_SCENARIO_COUNTS
from tests.benchmark.expressions import make_history_init_func

from .conftest import run_benchmark


@pytest.mark.benchmark
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_history_init_benchmark(qapp, benchmark, history_seed):
    run_benchmark(
        benchmark,
        make_history_init_func(qapp),
        group="History Init - Full Load",
        name=history_seed,
        rounds=5,
        warmup_rounds=2,
    )
    gc.collect()


@pytest.mark.benchmark
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_history_init_math_mode_benchmark(qapp, benchmark, history_seed):
    run_benchmark(
        benchmark,
        make_history_init_func(qapp, math_mode=True),
        group="History Init - Full Load (math)",
        name=history_seed,
        rounds=5,
        warmup_rounds=2,
    )
    gc.collect()


@pytest.mark.benchmark
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_history_first_paint_benchmark(qapp, benchmark, history_seed):
    run_benchmark(
        benchmark,
        make_history_init_func(qapp, first_paint_only=True),
        group="History First Paint",
        name=history_seed,
        rounds=5,
        warmup_rounds=2,
    )
    gc.collect()


@pytest.mark.benchmark
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_history_first_paint_math_mode_benchmark(qapp, benchmark, history_seed):
    run_benchmark(
        benchmark,
        make_history_init_func(qapp, math_mode=True, first_paint_only=True),
        group="History First Paint (math)",
        name=history_seed,
        rounds=5,
        warmup_rounds=2,
    )
    gc.collect()
