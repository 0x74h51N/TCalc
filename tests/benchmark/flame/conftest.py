#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import pathlib
from typing import Callable

WARMUP_ROUNDS = 10

FLAMEGRAPH_DIR = pathlib.Path(".flamegraphs")


def run_flamegraph(
    func: Callable,
    group: str,
    name: str,
    interval: float = 0.0001,
):
    """Profile *func* with pyinstrument and write an HTML flamegraph."""
    from pyinstrument import Profiler

    profiler = Profiler(interval=interval, async_mode="disabled", use_timing_thread=True)
    for _ in range(WARMUP_ROUNDS):
        try:
            func()
        except Exception:
            pass
    profiler.start()
    try:
        func()
    except Exception:
        pass
    profiler.stop()

    flame_dir = FLAMEGRAPH_DIR / group
    flame_path = flame_dir / f"{name}.html"
    flame_path.parent.mkdir(parents=True, exist_ok=True)
    with open(flame_path, "w") as f:
        f.write(profiler.output_html())
    print(f"\n  flamegraph -> {flame_path}")
