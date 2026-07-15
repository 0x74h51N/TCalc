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
    make_tokenize_func,
)

from .conftest import run_benchmark

SCALAR_TIERS = list(COLLECTION_SCALAR_SIZES)
CALC_TIERS = list(COLLECTION_CALC_SIZES)
# HOT reduces an inline `op[...]` (build + reduce every call); the small tiers keep the
# per-call build affordable. ASSIGN builds the collection once into a variable and reduces
# `op(A)` each call: a zero-copy reduce of a native, shared collection, so the big tiers
# isolate the reducer. complex sits in both to compare build+reduce against reduce-only.
AGG_HOT_TIERS = ("simple", "medium", "complex")
AGG_ASSIGN_TIERS = ("complex", "heavy", "sick")


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
@pytest.mark.parametrize("name", AGG_HOT_TIERS)
def test_collection_aggregation_hot(benchmark, name: str, op: str):
    import calc_native

    from tcalc.core.native_eval import evaluate_branch
    from tcalc.core.parser import tokenize

    calc = calc_native.Calculator()
    unit = calc_native.AngleUnit.RAD
    # Inline: evaluate rebuilds the collection from tokens and reduces it each call.
    branch = tokenize(f"{op}{make_scalar_collection_expr(COLLECTION_AGG_SIZES[name])}")
    rounds, warmup = COLLECTION_ROUNDS[name]

    run_benchmark(
        benchmark,
        lambda: evaluate_branch(branch, calc, unit),
        group="Collection Aggregation HOT",
        name=f"{op}-{name}",
        rounds=rounds,
        warmup_rounds=warmup,
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("op", AGG_OPS)
@pytest.mark.parametrize("name", AGG_ASSIGN_TIERS)
def test_collection_aggregation_assign(benchmark, name: str, op: str):
    import calc_native

    from tcalc.core.native_eval import evaluate_branch
    from tcalc.core.parser import tokenize

    calc = calc_native.Calculator()
    unit = calc_native.AngleUnit.RAD
    # Build the collection once into a variable (setup, outside the timed loop); the loop
    # reduces `op(A)`, which resolves the shared collection with no copy.
    calc_native.clear_vars()
    evaluate_branch(
        tokenize(f"A={make_scalar_collection_expr(COLLECTION_AGG_SIZES[name])}"), calc, unit
    )
    branch = tokenize(f"{op}(A)")
    rounds, warmup = COLLECTION_ROUNDS[name]

    run_benchmark(
        benchmark,
        lambda: evaluate_branch(branch, calc, unit),
        group="Collection Aggregation Assign Variable",
        name=f"{op}-{name}",
        rounds=rounds,
        warmup_rounds=warmup,
    )
