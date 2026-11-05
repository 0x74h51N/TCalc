#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

import pytest
from pytest import param

from tcalc.ui.props import KeypadRole, OptionRole, Prop, StatusKind, UiRole
from tcalc.ui.widgets.common.toaster import ToastLevel
from tcalc.ui.widgets.math.renderer.expression_node import InputKind

UI = Path(__file__).parents[4] / "src" / "tcalc" / "ui"
# A property that takes no value list is a flag, set to True
VALUES: dict[Prop, type[Enum] | type[bool]] = {
    Prop.UI_ROLE: UiRole,
    Prop.KEYPAD_ROLE: KeypadRole,
    Prop.OPTION_ROLE: OptionRole,
    Prop.STATUS_KIND: StatusKind,
    Prop.TOAST_LEVEL: ToastLevel,
    Prop.EXPR_SLOT_KIND: InputKind,
    Prop.LATEX_KIND: InputKind,
    Prop.PRESSED: bool,
    Prop.ADD_BUTTON: bool,
    Prop.PAD_KEY: bool,
    Prop.EXPR_SLOT: bool,
    Prop.EXPR_INPUT: bool,
    Prop.CUSTOM_PAD_MENU: bool,
    Prop.RAISED: bool,
}
_QSS_SELECTOR = re.compile(r'[\w#\]]\[(\w+)(?:="([^"]*)")?\]')
# In Python only a stylesheet string names a Qt class before the bracket
_INLINE_SELECTOR = re.compile(r'Q\w+\[(\w+)(?:="([^"]*)")?\]')


def _selectors() -> list[tuple[str, str, str | None]]:
    found = [
        (path.name, name, value or None)
        for path in UI.rglob("*.qss")
        for name, value in _QSS_SELECTOR.findall(path.read_text(encoding="utf-8"))
    ]
    for path in (UI / "widgets" / "keypad" / "custom_pad.py", UI / "widgets" / "utils.py"):
        text = path.read_text(encoding="utf-8")
        found += [(path.name, n, v or None) for n, v in _INLINE_SELECTOR.findall(text)]
    return found


def test_every_property_has_its_values():
    assert set(VALUES) == set(Prop)


@pytest.mark.parametrize(
    "where, name, value", [param(*s, id=f"{s[0]} {s[1]}={s[2]}") for s in _selectors()]
)
def test_selector_names_a_python_property(where, name, value):
    prop = Prop(name)
    if value is None:
        return
    kind = VALUES[prop]
    if kind is bool:
        assert value == "true"
    else:
        assert value in {m.value for m in kind}
