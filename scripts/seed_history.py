#!/usr/bin/env python3
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import calc_native

from tcalc.core.parser import tokenize
from tcalc.ui.controller.utils import format_result
from tcalc.ui.widgets.history.storage import HistoryEntry
from tests.benchmark.expressions import PAREN_EXPRESSIONS, RENDER_EXPRESSIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "benchmark" / ".fixtures"
DAT_NAME = "history.dat"
DAT_PATH = FIXTURES_DIR / DAT_NAME
ITEM_COUNT = 150


def _local_path() -> Path:
    from PySide6.QtCore import QCoreApplication, QStandardPaths

    if QCoreApplication.instance() is None:
        QCoreApplication([])
    QCoreApplication.setApplicationName("TCalc")
    base = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    return base / DAT_NAME


def _evalator(calculator, toks):
    res = "42"
    if calculator is not None:
        res = format_result(calc_native.evaluate(toks, calculator, calc_native.AngleUnit.DEG))
    return res


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed TCalc history")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Enable local seed mode",
    )
    args = parser.parse_args()
    calculator = calc_native.Calculator() if args.local else None
    exprs = list(PAREN_EXPRESSIONS.values())
    if args.local:
        exprs += list(RENDER_EXPRESSIONS.values())[:-1]
    cache: dict[str, tuple[calc_native.TokensBranch, str]] = {}
    entries: list[HistoryEntry] = []
    for i in range(ITEM_COUNT):
        expr = exprs[i % len(exprs)]
        if expr not in cache:
            tok = tokenize(expr)
            cache[expr] = (tok, calc_native.tokens_to_flat_text(tok.tokens))
        tok, flat = cache[expr]
        res = _evalator(calculator, tok)
        entries.append(HistoryEntry(expression=expr, result=res, tokenized=tok, flat_text=flat))

    out_path = _local_path() if args.local else DAT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump(entries, f, protocol=pickle.HIGHEST_PROTOCOL)

    try:
        display = out_path.relative_to(REPO_ROOT)
    except ValueError:
        display = out_path
    print(f"wrote {len(entries)} -> {display}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
