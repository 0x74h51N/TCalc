#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import calc_native
import pytest
from PySide6.QtWidgets import QWidget

from tcalc.core.native_eval import evaluate_branch
from tcalc.core.parser import tokenize
from tcalc.ui.config import calc_config
from tcalc.ui.widgets.calc.display.result.result import Result


def _coll(expr: str):
    return evaluate_branch(tokenize(expr), calc_native.Calculator(), calc_native.AngleUnit.RAD)


@pytest.fixture
def result_widget(qapp):
    parent = QWidget()
    w = Result(parent, calc_config["display"]["result"])
    parent.show()
    qapp.processEvents()
    yield w
    parent.close()
    parent.deleteLater()
    qapp.processEvents()


def test_status_label_hidden_by_default(result_widget):
    assert not result_widget.status_label.isVisible()


def test_status_label_info_shows_text(result_widget):
    result_widget.show()
    result_widget.update_res(
        "[1, 2, 3]",
        _coll("[1,2,3]"),
        status_text="three element list",
        status_kind="info",
    )
    assert result_widget.status_label.text() == "three element list"
    assert result_widget.status_label.isVisible()


def test_status_label_empty_hides(result_widget):
    result_widget.show()
    result_widget.update_res("5", 5, status_text="", status_kind="")
    assert not result_widget.status_label.isVisible()


def test_status_label_error_kind_marks_property(result_widget):
    result_widget.show()
    result_widget.update_res(
        "",
        None,
        status_text="List of List not allowed",
        status_kind="error",
    )
    assert result_widget.status_label.text() == "List of List not allowed"
    assert result_widget.status_label.property("statusKind") == "error"


def test_format_result_collection_in_result_label(result_widget):
    result_widget.show()
    result_widget.resize(600, 100)
    result_widget.result_label.setFixedWidth(500)
    coll = _coll("[1,2,3]")
    result_widget.update_res(repr(coll), coll, status_text="", status_kind="")
    # Wrap may still insert newlines if the font/metrics disagree; compare on
    # the joined form.
    assert result_widget.result_label.text().replace("\n", "") == "[1, 2, 3]"
