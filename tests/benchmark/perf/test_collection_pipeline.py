#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Collection tokenize / e2e / aggregation benchmarks (scalar and calc tabled separately)."""

from __future__ import annotations

import pytest

from tests.benchmark.expressions import (
    COLLECTION_AGG_SIZES,
    COLLECTION_CALC_SIZES,
    COLLECTION_E2E_CALC_THRESHOLDS_MS,
    COLLECTION_E2E_SCALAR_THRESHOLDS_MS,
    COLLECTION_ROUNDS,
    COLLECTION_SCALAR_SIZES,
    COLLECTION_TOKENIZE_CALC_THRESHOLDS_MS,
    COLLECTION_TOKENIZE_SCALAR_THRESHOLDS_MS,
    make_calc_collection_expr,
    make_pipeline_func,
    make_scalar_collection_expr,
    make_scalar_collection_value,
    make_tokenize_func,
)

from .conftest import run_benchmark

SCALAR_TIERS = list(COLLECTION_SCALAR_SIZES)
CALC_TIERS = list(COLLECTION_CALC_SIZES)
AGG_TIERS = list(COLLECTION_AGG_SIZES)


@pytest.mark.benchmark
@pytest.mark.parametrize("name", SCALAR_TIERS)
def test_tokenize_collection_scalar(benchmark, name: str):
    expr = make_scalar_collection_expr(COLLECTION_SCALAR_SIZES[name])
    rounds, warmup = COLLECTION_ROUNDS[name]
    run_benchmark(
        benchmark,
        make_tokenize_func(expr),
        group="Tokenize-W-Collection [scalar]",
        name=name,
        threshold_ms=COLLECTION_TOKENIZE_SCALAR_THRESHOLDS_MS[name],
        rounds=rounds,
        warmup_rounds=warmup,
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", CALC_TIERS)
def test_tokenize_collection_calc(benchmark, name: str):
    expr = make_calc_collection_expr(COLLECTION_CALC_SIZES[name])
    rounds, warmup = COLLECTION_ROUNDS[name]
    run_benchmark(
        benchmark,
        make_tokenize_func(expr),
        group="Tokenize-W-Collection [calc]",
        name=name,
        threshold_ms=COLLECTION_TOKENIZE_CALC_THRESHOLDS_MS[name],
        rounds=rounds,
        warmup_rounds=warmup,
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", SCALAR_TIERS)
def test_collection_e2e_scalar(benchmark, name: str):
    expr = make_scalar_collection_expr(COLLECTION_SCALAR_SIZES[name])
    rounds, warmup = COLLECTION_ROUNDS[name]
    run_benchmark(
        benchmark,
        make_pipeline_func(expr),
        group="Collection E2E [scalar]",
        name=name,
        threshold_ms=COLLECTION_E2E_SCALAR_THRESHOLDS_MS[name],
        rounds=rounds,
        warmup_rounds=warmup,
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", CALC_TIERS)
def test_collection_e2e_calc(benchmark, name: str):
    expr = make_calc_collection_expr(COLLECTION_CALC_SIZES[name])
    rounds, warmup = COLLECTION_ROUNDS[name]
    run_benchmark(
        benchmark,
        make_pipeline_func(expr),
        group="Collection E2E [calc]",
        name=name,
        threshold_ms=COLLECTION_E2E_CALC_THRESHOLDS_MS[name],
        rounds=rounds,
        warmup_rounds=warmup,
    )


AGG_OPS = ("mean", "median", "max")


@pytest.mark.benchmark
@pytest.mark.parametrize("op", AGG_OPS)
@pytest.mark.parametrize("name", AGG_TIERS)
def test_collection_aggregation_scalar(benchmark, name: str, op: str):
    from tcalc.core.engine import Calculator
    from tcalc.core.parser import (
        ValueOperand,
        evaluate_rpn,
        shunting_yard,
        tokenize_string,
    )

    calc = Calculator()
    # Pre-built runtime Collection (built once, directly, no tokenize).
    collection = make_scalar_collection_value(COLLECTION_AGG_SIZES[name])
    # The op's native OpToken, taken from a normal tokenized reduction.
    op_tok = shunting_yard(tokenize_string(f"{op}[1,2,3]"))[1]
    rpn = [ValueOperand(collection), op_tok]

    run_benchmark(
        benchmark,
        lambda: evaluate_rpn(rpn, calc),
        group="Collection Aggregation",
        name=f"{op}-{name}",
    )
