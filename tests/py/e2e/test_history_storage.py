#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from pathlib import Path

import calc_native

from tcalc.ui.widgets.history.storage import load_history

# Written by master 9ac31a9's save_history; a later build must still read it. To write it again,
# build 9ac31a9 in a detached worktree and save a HistoryEntry per expression, in this order.
SAVED = Path(__file__).with_name("saved_history.dat")
EXPRESSIONS = ["2+\\pi", "\\frac{1}{2}", "[1,2]", "mean(1,2)", "A=2", "A+1"]


def test_loads_history_an_earlier_build_saved(monkeypatch):
    monkeypatch.setattr("tcalc.ui.widgets.history.storage._history_path", lambda: SAVED)
    entries = load_history()
    assert [e.expression for e in entries] == EXPRESSIONS
    assert [calc_native.tokens_to_flat_text(e.tokenized.tokens) for e in entries] == [
        calc_native.tokens_to_flat_text(calc_native.tokenize_string(x).tokens) for x in EXPRESSIONS
    ]
