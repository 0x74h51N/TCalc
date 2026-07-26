#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Iterated-op (sum) benchmark: closed Faulhaber vs forced brute, same cases."""

from __future__ import annotations

import calc_native
import pytest

from tests.benchmark.expressions import (
    ITERATED_BRUTE_ROUNDS,
    ITERATED_CLOSED_THRESHOLDS_MS,
    ITERATED_SUM_BRUTE_EXPRESSIONS,
    ITERATED_SUM_CLOSED_EXPRESSIONS,
    make_pipeline_func,
)

from .conftest import run_benchmark


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(ITERATED_SUM_CLOSED_EXPRESSIONS))
def test_iterated_closed_benchmark(benchmark, name: str):
    calc_native.set_closed_forms_enabled(True)
    run_benchmark(
        benchmark,
        make_pipeline_func(ITERATED_SUM_CLOSED_EXPRESSIONS[name]),
        group="Iterated Sum Closed",
        name=name,
        threshold_ms=ITERATED_CLOSED_THRESHOLDS_MS[name],
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(ITERATED_SUM_BRUTE_EXPRESSIONS))
def test_iterated_brute_benchmark(benchmark, name: str):
    assert calc_native.eval_time_budget_ms() == 0
    calc_native.set_closed_forms_enabled(False)
    try:
        rounds, warmup = ITERATED_BRUTE_ROUNDS[name]
        run_benchmark(
            benchmark,
            make_pipeline_func(ITERATED_SUM_BRUTE_EXPRESSIONS[name]),
            group="Iterated Sum Brute",
            name=name,
            rounds=rounds,
            warmup_rounds=warmup,
        )
    finally:
        calc_native.set_closed_forms_enabled(True)
