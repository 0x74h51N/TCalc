#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import dataclasses
import json
import logging

import pytest
from PySide6.QtCore import QPoint, QSettings
from pytest import param

from tcalc.core.ops import Operation
from tcalc.theme import load_theme
from tcalc.ui.config import CONFIG
from tcalc.ui.styles import apply_theme
from tcalc.ui.widgets.common.button import KSSpinBox
from tcalc.ui.widgets.common.constants_menu import CONSTANTS_BY_CATEGORY
from tcalc.ui.widgets.common.types import GridLayout, KeySettings, PadLayout
from tcalc.ui.widgets.keypad.custom_pad import CustomPad

DEFAULTS = CONFIG.keypad.custom
CONSTANT = next(iter(CONSTANTS_BY_CATEGORY.values()))[0]


@pytest.fixture
def settings(qapp, monkeypatch, tmp_path):
    ini = str(tmp_path / "t.ini")

    def factory(*_):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr("tcalc.ui.widgets.keypad.custom_pad.QSettings", factory)
    return factory()


def _layout(pad: CustomPad):
    return (
        pad._label,
        pad._cols,
        pad._rows,
        [
            (g.max_rows, [(k.operation, k.row, k.col, k.bg_color, k.text_color) for k in g.keys])
            for g in pad._grids
        ],
    )


def _add(pad: CustomPad, *ops: Operation) -> None:
    for op in ops:
        pad._open_op_picker(QPoint(0, 0), 0)
        pad._on_operation_picked(op)


def _pick_color(pad: CustomPad, target: str, value: str) -> None:
    pad._open_color_picker((0, 0), target, QPoint(0, 0))
    pad._color_picker.item_selected.emit(value)


def _replace(pad: CustomPad) -> None:
    pad._open_op_picker(QPoint(0, 0), 0, edit=(0, 0))
    pad._on_operation_picked(Operation.SUB)


# (the edit, made through the pad's own handlers on a pad holding ADD and MUL)
@pytest.mark.parametrize(
    "edit",
    [
        param(lambda pad: _add(pad, Operation.SIN), id="operation added"),
        param(lambda pad: pad._on_constant_picked(CONSTANT, 0), id="constant added"),
        param(_replace, id="operation replaced"),
        param(lambda pad: _pick_color(pad, "bg", "$accent"), id="theme color"),
        param(lambda pad: _pick_color(pad, "text", "#123456"), id="custom color"),
        param(lambda pad: pad._remove_key(0, 0), id="key removed"),
        param(lambda pad: pad._on_cols_changed(2), id="cols changed"),
        param(lambda pad: pad._on_rows_changed(2), id="rows changed"),
        param(lambda pad: pad._grids[0]._on_max_rows_changed(1), id="grid rows changed"),
        param(lambda pad: pad._rename_pad(), id="renamed"),
    ],
)
def test_edited_layout_round_trips(settings, monkeypatch, edit):
    monkeypatch.setattr(
        "tcalc.ui.widgets.keypad.custom_pad.QInputDialog.getText", lambda *a, **k: ("Mine", True)
    )
    pad = CustomPad(3)
    pad._toggle_edit(True)
    _add(pad, Operation.ADD, Operation.MUL)
    edit(pad)
    pad._toggle_edit(False)
    assert _layout(CustomPad(3)) == _layout(pad)


def test_new_pad_starts_from_defaults_silently(settings, caplog):
    with caplog.at_level(logging.WARNING):
        pad = CustomPad(3)
    assert (pad._cols, pad._rows) == (DEFAULTS.default_cols, DEFAULTS.default_rows)
    assert [(g.max_rows, g.keys) for g in pad._grids] == [(DEFAULTS.default_max_rows, [])]
    assert caplog.records == []


def _saved(settings: QSettings, layout: object) -> None:
    settings.setValue("custom_pad/3/layout", json.dumps(layout))
    settings.sync()


def _pad(cols: int, *grids: GridLayout) -> dict:
    return dataclasses.asdict(PadLayout("Mine", cols, 1, grids))


def test_unknown_operation_is_skipped_and_keeps_positions(settings):
    keys = (KeySettings("SIN"), KeySettings("NO_SUCH_OP"), KeySettings("COS"))
    _saved(settings, _pad(1, GridLayout(2, keys)))
    keys = CustomPad(3)._grids[0].keys
    assert [(k.operation, k.row, k.col) for k in keys] == [
        (Operation.SIN, 0, 0),
        (Operation.COS, 0, 1),
    ]


# (saved grids of a 1x2 pad, the max_rows of the loaded grids)
@pytest.mark.parametrize(
    "saved, max_rows",
    [
        param([2, 3, 4], [2, 3], id="extra dropped"),
        param([2], [2, DEFAULTS.default_max_rows], id="missing added"),
    ],
)
def test_extra_grids_are_dropped_and_missing_ones_added(settings, saved, max_rows):
    _saved(settings, _pad(2, *(GridLayout(n, ()) for n in saved)))
    assert [g.max_rows for g in CustomPad(3)._grids] == max_rows


# (saved layout, the logged line)
@pytest.mark.parametrize(
    "layout, logged",
    [
        param(
            {**_pad(1), "grids": {}},
            "custom pad 3.grids: expected a list, got dict",
            id="grids a table",
        ),
        param(
            {**_pad(1), "cols": "2"},
            "custom pad 3.cols: expected int, got str",
            id="cols text",
        ),
    ],
)
def test_layout_of_the_wrong_shape_starts_from_defaults(settings, caplog, layout, logged):
    _saved(settings, layout)
    with caplog.at_level(logging.WARNING):
        pad = CustomPad(3)
    assert (pad._label, pad._cols, pad._rows) == (
        "CustomPad 3",
        DEFAULTS.default_cols,
        DEFAULTS.default_rows,
    )
    assert [r.getMessage() for r in caplog.records] == [logged]


@pytest.fixture
def themed(qapp):
    old_palette, old_sheet = qapp.palette(), qapp.styleSheet()
    apply_theme(qapp, "dark")
    yield qapp
    load_theme("dark")
    qapp.setPalette(old_palette)
    qapp.setStyleSheet(old_sheet)


def _spins(pad: CustomPad) -> list[KSSpinBox]:
    pad._toggle_edit(True)
    return pad.findChildren(KSSpinBox)


@pytest.mark.parametrize("variant", ["kitty", "sponge", "retro"])
def test_toolbar_spin_boxes_keep_their_font_and_fit_in_every_theme(settings, themed, variant):
    built_before = _spins(CustomPad(3))
    font = built_before[0].font()
    apply_theme(themed, variant)
    for spin in built_before + _spins(CustomPad(4)):
        assert (spin.font().family(), spin.font().pointSize()) == (font.family(), font.pointSize())
        assert spin.width() >= spin.sizeHint().width(), spin.prefix()
