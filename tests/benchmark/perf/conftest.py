#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import Callable

ROUNDS_DEFAULT = 100
ROUNDS_RENDER = 40
WARMUP_ROUNDS = 15


def run_benchmark(
    benchmark,
    func: Callable,
    group: str,
    name: str = "",
    threshold_ms: float | None = None,
    rounds: int = ROUNDS_DEFAULT,
    warmup_rounds: int = WARMUP_ROUNDS,
):
    """Run a pedantic benchmark with optional threshold assertion."""
    benchmark.group = group

    def safe_func():
        try:
            return func()
        except Exception as e:
            raise RuntimeError(f"Benchmark '{name}' crashed: {e}") from e

    benchmark.pedantic(safe_func, rounds=rounds, warmup_rounds=warmup_rounds)

    if benchmark.stats is None:
        return

    max_ms = benchmark.stats["max"] * 1000
    if threshold_ms is not None:
        assert max_ms < threshold_ms, f"{name}: {max_ms:.4f}ms exceeds {threshold_ms}ms"
