#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""View-menu state <-> UI sync. Dock toggles now; preset radios reuse the same
data-driven pattern once presets drive a real layout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest

import tcalc.app_state as app_state_mod
from tcalc.app_state import DockKind, get_app_state
from tcalc.ui.controller.menubar import ViewOperations

param = pytest.param


@dataclass(frozen=True, slots=True)
class ToggleSpec:
    """A View-menu dock toggle: its handler (key into the menu's action map)
    and the dock it drives."""

    id: str
    fn: Callable
    kind: DockKind


# One line per dock toggle; add a new keypad here and every test below covers it.
DOCK_TOGGLES = [
    ToggleSpec("numpad", ViewOperations.toggle_numpad, DockKind.NUMPAD),
    ToggleSpec("funcpad", ViewOperations.toggle_funcpad, DockKind.FUNCPAD),
    ToggleSpec("trigpad", ViewOperations.toggle_trigpad, DockKind.TRIGPAD),
    ToggleSpec("history", ViewOperations.toggle_history, DockKind.HISTORY),
]
SPECS = [param(s, id=s.id) for s in DOCK_TOGGLES]


@pytest.fixture
def window(qapp, monkeypatch, tmp_path):
    """A fresh MainWindow with isolated settings and stubbed history I/O."""
    from PySide6.QtCore import QSettings

    ini = str(tmp_path / "t.ini")

    def factory(*a, **k):
        return QSettings(ini, QSettings.Format.IniFormat)

    # Isolate real app config: avoid clobbering the user's saved layout/geometry
    # on close and keep a deterministic (empty) start state.
    monkeypatch.setattr("tcalc.app_state.QSettings", factory)
    monkeypatch.setattr("tcalc.ui.window.QSettings", factory)
    # Don't read/write the real history.dat.
    monkeypatch.setattr("tcalc.ui.widgets.history.history.load_history", lambda: [])
    monkeypatch.setattr("tcalc.ui.widgets.history.history.save_history", lambda _i: None)
    # Rebuild the singleton so it binds to the isolated settings, not a stale one.
    monkeypatch.setattr(app_state_mod, "_app_state", None)

    from tcalc.ui.window import MainWindow

    win = MainWindow()
    win.show()
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def _action(window, spec: ToggleSpec):
    # Retained on the menu controller -> no QMenu traversal (avoids PySide GC).
    return window.menubar.view_menu._toggle_actions[spec.fn]


def _open(window, spec: ToggleSpec) -> bool:
    # isHidden() is reliable offscreen; isVisible() depends on the parent chain.
    return not window._docks[spec.kind].isHidden()


# Channels that flip a dock to a desired state. The invariant must hold no matter
# which one drives the change (menu = forward path, dock = visibilityChanged feedback).
def _flip_via_menu(window, spec: ToggleSpec, want: bool) -> None:
    if _open(window, spec) != want:
        _action(window, spec).trigger()


def _flip_via_dock(window, spec: ToggleSpec, want: bool) -> None:
    dock = window._docks[spec.kind]
    dock.show() if want else dock.close()


CHANNELS = [param(_flip_via_menu, id="via-menu"), param(_flip_via_dock, id="via-dock")]


@pytest.mark.parametrize("spec", SPECS)
@pytest.mark.parametrize("flip", CHANNELS)
def test_dock_state_stays_synced(window, qapp, spec, flip):
    """Dock visibility, app-state, and the menu check stay in lockstep through
    any channel, both directions."""
    for want in (True, False, True):
        flip(window, spec, want)
        qapp.processEvents()
        assert (
            _open(window, spec)
            == get_app_state().is_dock_open(spec.kind)
            == _action(window, spec).isChecked()
            == want
        )


def test_toggles_are_independent(window, qapp):
    """Flipping one dock never moves another."""
    for spec in DOCK_TOGGLES:
        _flip_via_menu(window, spec, True)
    qapp.processEvents()
    assert all(_open(window, s) for s in DOCK_TOGGLES)

    remaining = list(DOCK_TOGGLES)
    for target in DOCK_TOGGLES:
        _flip_via_menu(window, target, False)
        qapp.processEvents()
        remaining.remove(target)
        assert not _open(window, target)
        assert all(_open(window, s) for s in remaining)
