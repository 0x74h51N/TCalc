"""E2E pipeline benchmark tests."""

from __future__ import annotations

import calc_native
import pytest

from tcalc.core.engine import Calculator
from tcalc.core.parser import evaluate_tokens, tokenize_string

from .conftest import run_benchmark

EXPRESSIONS = {
    "simple": "2 + 3",
    "medium": "2 + 3 * 4 - 5",
    "complex": "sin(45) + cos(30) * tan(60)",
    "heavy": (
        "((1+2)*(3+4))/((5-6)/(7*1e16!))"
        "+ sqrt(16) * log(100)"
        "- floor(3.7) + ceil(2.3)"
        "+ sin(30)^2 + cos(30)^2"
        "- sqrt(144!) * (7 + 8) / (9 - 1)"
    ),
    "sick": (
        "sin(cos(tan(45))) + sqrt(16)*1e16!"
        "* (2^3^2) / (1 + 2 * 3 - 4 / 5)"
        "+ floor(ceil(3.14159)) * log(exp(2))"
        "+ sin(30)^2 + cos(30)^2"
        "- sqrt(144!) * (7 + 8) / (9 - 1)"
        "- ((1+2)*(3+4))/((5-6)/(7*1e16!))"
        "+ sqrt(16) * log(100)"
    ),
}

THRESHOLDS_MS = {"simple": 1, "medium": 2, "complex": 5, "heavy": 10, "sick": 50}


def _make_pipeline_func(expr: str):
    calc = Calculator()

    def evaluate():
        tokens = tokenize_string(expr)
        return evaluate_tokens(tokens, calc)

    return evaluate


def _make_tokenize_func(expr: str):
    return lambda: tokenize_string(expr)


def _make_shunting_func(expr: str):
    tokens = tokenize_string(expr)
    return lambda: calc_native.shunting_yard(tokens)


@pytest.mark.benchmark
@pytest.mark.parametrize("name", ["simple", "medium", "complex", "heavy", "sick"])
def test_calc_pipeline_benchmark(benchmark, name: str):
    run_benchmark(
        benchmark,
        _make_pipeline_func(EXPRESSIONS[name]),
        group="Calc Pipeline",
        name=name,
        threshold_ms=THRESHOLDS_MS[name],
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", ["simple", "medium", "complex", "heavy", "sick"])
def test_tokenize_benchmark(benchmark, name: str):
    run_benchmark(
        benchmark,
        _make_tokenize_func(EXPRESSIONS[name]),
        group="Tokenize",
        name=name,
    )


@pytest.mark.benchmark
@pytest.mark.parametrize("name", ["simple", "medium", "complex", "heavy", "sick"])
def test_shunting_yard_benchmark(benchmark, name: str):
    run_benchmark(
        benchmark,
        _make_shunting_func(EXPRESSIONS[name]),
        group="Shunting Yard",
        name=name,
    )
