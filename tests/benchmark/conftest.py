from __future__ import annotations

import os
import sys
from typing import Callable

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "*.warning=false")


ROUNDS_DEFAULT = 100
ROUNDS_RENDER = 30
WARMUP_ROUNDS = 5


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def run_benchmark(
    benchmark,
    func: Callable,
    group: str,
    name: str = "",
    threshold_ms: float | None = None,
    rounds: int = ROUNDS_DEFAULT,
) -> None:
    """Run a benchmark with standard settings and threshold check.
    Threshold compares against MAX time, worst case across all rounds.
    """

    def safe_func():
        try:
            return func()
        except Exception as e:
            raise RuntimeError(f"Benchmark '{name}' crashed: {e}") from e

    benchmark.group = group
    benchmark.pedantic(safe_func, rounds=rounds, warmup_rounds=WARMUP_ROUNDS)

    if benchmark.stats is None:
        return

    max_ms = benchmark.stats["max"] * 1000
    if threshold_ms is not None:
        assert max_ms < threshold_ms, f"{name}: {max_ms:.4f}ms exceeds {threshold_ms}ms"
