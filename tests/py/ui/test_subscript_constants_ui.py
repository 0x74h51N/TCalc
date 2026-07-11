#
# TCalc - Copyright (C) 2026 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations


def test_keybutton_subscript_uses_icon(qapp) -> None:
    import calc_native

    from tcalc.ui.widgets.common.button import KeyButton
    from tcalc.ui.widgets.common.types import KeyDef

    kd = KeyDef(label="σ_{SB}", operation=calc_native.ConstId.StefanBoltzmann)
    btn = KeyButton(kd, "const")
    assert btn.text() == ""
    assert not btn.icon().isNull()


def test_keybutton_plain_keeps_text(qapp) -> None:
    from tcalc.ui.widgets.common.button import KeyButton
    from tcalc.ui.widgets.common.types import KeyDef

    btn = KeyButton(KeyDef(label="π"), "const")
    assert btn.text() == "π"
    assert btn.icon().isNull()


def _iter_actions(menu):
    for act in menu.actions():
        sub = act.menu()
        if sub is not None:
            yield from _iter_actions(sub)
        else:
            yield act


def test_constant_menu_subscript_action_has_icon(qapp) -> None:
    from PySide6.QtWidgets import QMenu

    from tcalc.ui.widgets.common.constants_menu import build_constant_menu

    menu = QMenu()
    build_constant_menu(menu, lambda entry: None)

    sb = [a for a in _iter_actions(menu) if a.text() == "Stefan Boltzmann"]
    assert sb, "Stefan Boltzmann action not found"
    assert not sb[0].icon().isNull()

    actions = list(_iter_actions(menu))
    assert actions
    assert all(not a.icon().isNull() for a in actions)

    # Every icon is rendered into the same shared box, so pixmap sizes match uniformly
    pixmap_sizes = {a.icon().availableSizes()[0] for a in actions}
    assert len(pixmap_sizes) == 1
