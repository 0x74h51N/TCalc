#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""E2E pipeline benchmark tests."""

from __future__ import annotations

import pytest

from tests.benchmark.expressions import (
    PAREN_EXPRESSIONS,
    PIPELINE_EXPRESSIONS,
    PIPELINE_THRESHOLDS_MS,
    make_pipeline_func,
    make_shunting_func,
    make_tokenize_func,
)

from .conftest import run_benchmark


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(PIPELINE_EXPRESSIONS))
def test_calc_pipeline_benchmark(benchmark, name: str):
    run_benchmark(
        benchmark,
        make_pipeline_func(PIPELINE_EXPRESSIONS[name]),
        group="Calc Pipeline",
        name=name,
        threshold_ms=PIPELINE_THRESHOLDS_MS[name],
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(PIPELINE_EXPRESSIONS))
def test_tokenize_benchmark(benchmark, name: str):
    run_benchmark(
        benchmark,
        make_tokenize_func(PIPELINE_EXPRESSIONS[name]),
        group="Tokenize",
        name=name,
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(PIPELINE_EXPRESSIONS))
def test_shunting_yard_benchmark(benchmark, name: str):
    run_benchmark(
        benchmark,
        make_shunting_func(PIPELINE_EXPRESSIONS[name]),
        group="Shunting Yard",
        name=name,
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", list(PAREN_EXPRESSIONS))
def test_tokenize_paren_benchmark(benchmark, name: str):
    run_benchmark(
        benchmark,
        make_tokenize_func(PAREN_EXPRESSIONS[name]),
        group="Tokenize Paren-LaTeX",
        name=name,
    )
