#!/usr/bin/env python3
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pickle
from pathlib import Path

import calc_native

from tcalc.app_state import CalculatorMode
from tcalc.core.parser import tokenize
from tcalc.ui.widgets.history.storage import HistoryEntry
from tests.benchmark.expressions import PAREN_EXPRESSIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "benchmark" / ".fixtures"
DAT_PATH = FIXTURES_DIR / f"history_{CalculatorMode.SCIENCE.value}.dat"
ITEM_COUNT = 150


def main() -> int:
    exprs = list(PAREN_EXPRESSIONS.values())
    cache: dict[str, tuple[calc_native.TokensBranch, str]] = {}
    entries: list[HistoryEntry] = []
    for i in range(ITEM_COUNT):
        expr = exprs[i % len(exprs)]
        if expr not in cache:
            tok = tokenize(expr)
            cache[expr] = (tok, calc_native.tokens_to_flat_text(tok.tokens))
        tok, flat = cache[expr]
        entries.append(HistoryEntry(expression=expr, result="42", tokenized=tok, flat_text=flat))

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    with open(DAT_PATH, "wb") as f:
        pickle.dump(entries, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"wrote {len(entries)} -> {DAT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
