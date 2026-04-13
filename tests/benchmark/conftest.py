#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "*.warning=false")

FIXTURES_DIR = Path(__file__).resolve().parent / ".fixtures"
HISTORY_DAT = FIXTURES_DIR / "history_science.dat"

HISTORY_SCENARIO_COUNTS: dict[str, int] = {
    "render_exprs": 5,
    "50_items": 50,
    "150_items": 150,
}


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def history_seed(request, tmp_path):
    if not HISTORY_DAT.exists():
        pytest.fail(
            f"missing benchmark fixture: {HISTORY_DAT} — run scripts/seed_history.py",
            pytrace=False,
        )
    name = request.param
    count = HISTORY_SCENARIO_COUNTS[name]
    with open(HISTORY_DAT, "rb") as f:
        entries = pickle.load(f)
    with open(tmp_path / "history_science.dat", "wb") as f:
        pickle.dump(entries[:count], f, protocol=pickle.HIGHEST_PROTOCOL)

    from tcalc.ui.widgets.history import storage

    mp = pytest.MonkeyPatch()
    mp.setattr(storage, "_get_data_dir", lambda: tmp_path)
    yield name
    mp.undo()
