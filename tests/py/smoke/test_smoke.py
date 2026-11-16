#
# TCalc - Copyright (C) 2026 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Every op and LaTeX form over edge operands, on the app's path: none may end the process."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import calc_native
import pytest

REPO = Path(__file__).resolve().parents[3]

OPERANDS = (
    "0",
    "1",
    "-1",
    "0.5",
    "1/3",
    "9223372036854775807",
    "-9223372036854775807-1",
    "1e19",
    "2^{63}",
    "1e308",
    "1e-320",
    "1e400",
    "1e-400",
    "i",
    "1e400i",
    "1+i",
    "[]",
    "[0,1e400,-1]",
    "(1,2)",
    "[[1],[2]]",
)

ONE_SLOT_LATEX = (r"\sqrt{{{a}}}", r"\sum_{{n=1}}^{{{a}}} n", r"\prod_{{n=1}}^{{{a}}} n")
TWO_SLOT_LATEX = (r"\frac{{{a}}}{{{b}}}", r"\root{{{a}}}{{{b}}}", "{a}^{{{b}}}", "log_{{{a}}}{b}")

# A case known to fail, held until its issue is fixed: case -> (issue, date).
SMOKE_PINS: dict[str, tuple[str, str]] = {
    "(-9223372036854775807-1)^(-1)": ("#249", "2026-11-16"),
    "(-9223372036854775807-1)⁻¹": ("#249", "2026-11-16"),
    "(1)⌄(-9223372036854775807-1)": ("#249", "2026-11-16"),
    "(-1)⌄(-9223372036854775807-1)": ("#249", "2026-11-16"),
    "(0.5)⌄(-9223372036854775807-1)": ("#249", "2026-11-16"),
    "(1/3)⌄(-9223372036854775807-1)": ("#249", "2026-11-16"),
    "(9223372036854775807)⌄(-9223372036854775807-1)": ("#249", "2026-11-16"),
    "(-9223372036854775807-1)⌄(-1)": ("#249", "2026-11-16"),
    "(-9223372036854775807-1)⌄(-9223372036854775807-1)": ("#249", "2026-11-16"),
    "\\root{1}{-9223372036854775807-1}": ("#249", "2026-11-16"),
    "\\root{-1}{-9223372036854775807-1}": ("#249", "2026-11-16"),
    "\\root{0.5}{-9223372036854775807-1}": ("#249", "2026-11-16"),
    "\\root{1/3}{-9223372036854775807-1}": ("#249", "2026-11-16"),
    "\\root{9223372036854775807}{-9223372036854775807-1}": ("#249", "2026-11-16"),
    "\\root{-9223372036854775807-1}{-1}": ("#249", "2026-11-16"),
    "\\root{-9223372036854775807-1}{-9223372036854775807-1}": ("#249", "2026-11-16"),
}


def _cases() -> list[str]:
    pairs = [(a, b) for a in OPERANDS for b in OPERANDS]
    cases: list[str] = []
    for row in calc_native.op_table():
        if not row.method:
            continue
        sym = row.symbol
        arity = row.arity.name
        if row.is_variadic:
            cases += [f"{sym}({a})" for a in OPERANDS] + [f"{sym}({a},{b})" for a, b in pairs]
        elif arity == "Binary":
            cases += [f"({a}){sym}({b})" for a, b in pairs]
        elif arity == "Postfix":
            cases += [f"({a}){sym}" for a in OPERANDS]
        elif row.call_arity == 2:
            cases += [f"{sym}({a},{b})" for a, b in pairs]
        else:
            cases += [f"{sym}({a})" for a in OPERANDS]
    cases += [form.format(a=a) for form in ONE_SLOT_LATEX for a in OPERANDS]
    cases += [form.format(a=a, b=b) for form in TWO_SLOT_LATEX for a, b in pairs]
    return cases


CASES = _cases()


def _run_chunk(exprs: list[str]) -> dict[str, str]:
    """Faults of *exprs* by case; a worker that ends is restarted after its last case."""
    faults: dict[str, str] = {}
    env = os.environ | {"QT_QPA_PLATFORM": "offscreen", "QT_LOGGING_RULES": "*=false"}
    first = 0
    while first < len(exprs):
        proc = subprocess.run(
            [sys.executable, "-m", "tests.py.smoke.worker"],
            input=json.dumps(exprs[first:]),
            capture_output=True,
            text=True,
            cwd=REPO,
            env=env,
            check=False,
        )
        last: int | None = None
        for line in proc.stdout.splitlines():
            msg = json.loads(line)
            if "start" in msg:
                last = first + msg["start"]
            else:
                faults[exprs[first + msg["error"]]] = f"exception {msg['exc']}"
        if proc.returncode == 0:
            break
        if last is None:
            raise RuntimeError(f"smoke worker failed before its first case:\n{proc.stderr}")
        rc = proc.returncode
        faults[exprs[last]] = "freeze" if rc == 1 else f"abort signal {-rc}"
        first = last + 1
    return faults


@pytest.fixture(scope="module")
def faults() -> dict[str, str]:
    n = os.cpu_count() or 1
    with ThreadPoolExecutor(n) as pool:
        chunks = pool.map(_run_chunk, [CASES[k::n] for k in range(n)])
    return {case: fault for chunk in chunks for case, fault in chunk.items()}


def _param(case: str) -> object:
    pin = SMOKE_PINS.get(case)
    marks = [pytest.mark.xfail(strict=True, reason=f"{pin[0]} {pin[1]}")] if pin else []
    return pytest.param(case, id=case, marks=marks)


@pytest.mark.parametrize("case", [_param(c) for c in CASES])
def test_case(case: str, faults: dict[str, str]) -> None:
    assert case not in faults, faults.get(case)


def test_pins_name_cases() -> None:
    assert set(SMOKE_PINS) <= set(CASES), set(SMOKE_PINS) - set(CASES)
