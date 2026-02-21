from __future__ import annotations

import multiprocessing
import os
import pathlib
import sys
from typing import Callable

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "*.warning=false")


ROUNDS_DEFAULT = 100
ROUNDS_RENDER = 40
WARMUP_ROUNDS = 15


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def flamegraph_flag(request):
    """Return True if --flamegraph was passed to pytest"""
    return request.config.getoption("--flamegraph")


def pytest_addoption(parser):
    parser.addoption(
        "--flamegraph",
        action="store_true",
        default=False,
        help="Generate flamegraphs for benchmarks",
    )


def _generate_flamegraph(func: Callable, rounds: int, warmup: int, flame_path: pathlib.Path):
    from pyinstrument import Profiler

    profiler = Profiler()
    for _ in range(warmup):
        try:
            func()
        except Exception:
            pass
    profiler.start()
    for _ in range(rounds):
        try:
            func()
        except Exception:
            pass
    profiler.stop()

    try:
        flame_path.parent.mkdir(parents=True, exist_ok=True)
        with open(flame_path, "w") as f:
            f.write(profiler.output_html())
        print(f"[INFO] Flamegraph saved: {flame_path}")
    except Exception as e:
        print(f"[WARN] Could not save flamegraph: {e}")


def run_benchmark(
    benchmark,
    func: Callable,
    group: str,
    name: str = "",
    threshold_ms: float | None = None,
    rounds: int = ROUNDS_DEFAULT,
    flamegraph=flamegraph_flag,
):
    benchmark.group = group

    def safe_func():
        try:
            return func()
        except Exception as e:
            raise RuntimeError(f"Benchmark '{name}' crashed: {e}") from e

    if flamegraph:
        flame_dir = pathlib.Path(".flamegraphs") / group
        flame_path = flame_dir / f"{name}.html"
        p = multiprocessing.Process(
            target=_generate_flamegraph,
            args=(safe_func, rounds, WARMUP_ROUNDS, flame_path),
            daemon=True,
        )
        p.start()

    benchmark.pedantic(safe_func, rounds=rounds, warmup_rounds=WARMUP_ROUNDS)

    if benchmark.stats is None:
        return

    max_ms = benchmark.stats["max"] * 1000
    if threshold_ms is not None:
        assert max_ms < threshold_ms, f"{name}: {max_ms:.4f}ms exceeds {threshold_ms}ms"
