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
from PySide6.QtGui import Qt

import tcalc.app_state as app_state_mod
from tcalc.app_state import PRESET_LAYOUTS, DockKind, KeypadPreset, get_app_state
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
    monkeypatch.setattr("tcalc.ui.layout_presets.QSettings", factory)
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


def test_preset_layouts_contents():
    from tcalc.app_state import PRESET_LAYOUTS, DockKind, KeypadPreset

    assert PRESET_LAYOUTS[KeypadPreset.SIMPLE].visible_keypads == (DockKind.NUMPAD,)
    assert PRESET_LAYOUTS[KeypadPreset.SIMPLE].angle_visible is False
    assert PRESET_LAYOUTS[KeypadPreset.SCIENCE].visible_keypads == (
        DockKind.TRIGPAD,
        DockKind.NUMPAD,
        DockKind.FUNCPAD,
    )
    assert PRESET_LAYOUTS[KeypadPreset.SCIENCE].angle_visible is True


def test_active_custom_id_default_and_persist(window):
    state = get_app_state()
    assert state.active_custom_id is None
    state.active_custom_id = 5
    assert state.active_custom_id == 5
    state.active_custom_id = None
    assert state.active_custom_id is None


PRESET_CASES = [
    param(KeypadPreset.SIMPLE, id="simple"),
    param(KeypadPreset.SCIENCE, id="science"),
]
KEYPADS = (DockKind.NUMPAD, DockKind.FUNCPAD, DockKind.TRIGPAD)


def _dock_open(window, kind) -> bool:
    return not window._docks[kind].isHidden()


@pytest.mark.parametrize("preset", PRESET_CASES)
def test_preset_applies_keypads_and_angle(window, qapp, preset):
    window.menubar.view_menu.ops.set_preset(preset)
    qapp.processEvents()
    layout = PRESET_LAYOUTS[preset]
    for kind in KEYPADS:
        assert _dock_open(window, kind) == (kind in layout.visible_keypads)
    assert window.calc_widget.topbar.is_angle_visible() == layout.angle_visible


@pytest.mark.parametrize("start_open", [param(True, id="open"), param(False, id="closed")])
def test_preset_preserves_history_visibility(window, qapp, start_open):
    hist = window._docks[DockKind.HISTORY]
    hist.setVisible(start_open)
    qapp.processEvents()
    window.menubar.view_menu.ops.set_preset(KeypadPreset.SCIENCE)
    qapp.processEvents()
    assert (not hist.isHidden()) == start_open
    assert window.dockWidgetArea(hist) == Qt.DockWidgetArea.RightDockWidgetArea


def test_switch_returns_to_default_after_manual_change(window, qapp):
    ops = window.menubar.view_menu.ops
    ops.set_preset(KeypadPreset.SIMPLE)
    qapp.processEvents()
    window._docks[DockKind.FUNCPAD].show()  # manual deviation
    qapp.processEvents()
    assert _dock_open(window, DockKind.FUNCPAD)
    ops.set_preset(KeypadPreset.SIMPLE)
    qapp.processEvents()
    assert not _dock_open(window, DockKind.FUNCPAD)


def test_restore_default_reapplies_active_preset(window, qapp):
    ops = window.menubar.view_menu.ops
    ops.set_preset(KeypadPreset.SCIENCE)
    qapp.processEvents()
    window._docks[DockKind.TRIGPAD].close()  # deviate
    qapp.processEvents()
    ops.restore_default_layout()
    qapp.processEvents()
    assert _dock_open(window, DockKind.TRIGPAD)


@pytest.fixture
def store(monkeypatch, tmp_path):
    from PySide6.QtCore import QSettings

    ini = str(tmp_path / "store.ini")

    def factory(*a, **k):
        return QSettings(ini, QSettings.Format.IniFormat)

    monkeypatch.setattr("tcalc.ui.layout_presets.QSettings", factory)
    from tcalc.ui.layout_presets import LayoutPresetStore

    return LayoutPresetStore()


def test_layout_preset_store_roundtrip(store):
    from PySide6.QtCore import QByteArray

    rec = store.add("alpha", QByteArray(b"\x01\x02"), True)
    assert rec.id == 0
    got = store.get(0)
    assert got is not None
    assert got.name == "alpha"
    assert bytes(got.state) == b"\x01\x02"
    assert got.angle_visible is True

    rec2 = store.add("beta", QByteArray(b"\x03"), False)
    assert rec2.id == 1
    assert [r.name for r in store.list()] == ["alpha", "beta"]

    store.rename(0, "renamed")
    assert store.get(0).name == "renamed"

    store.delete(0)
    assert store.get(0) is None
    assert [r.id for r in store.list()] == [1]


def test_window_capture_and_apply_custom(window, qapp):
    window.menubar.view_menu.ops.set_preset(KeypadPreset.SCIENCE)
    qapp.processEvents()
    state, angle = window.capture_layout()
    assert angle is True

    window.menubar.view_menu.ops.set_preset(KeypadPreset.SIMPLE)
    qapp.processEvents()
    assert window.calc_widget.topbar.is_angle_visible() is False

    from tcalc.ui.layout_presets import LayoutPreset

    window.apply_custom_layout(LayoutPreset(0, "x", state, angle))
    qapp.processEvents()
    assert window.calc_widget.topbar.is_angle_visible() is True


def test_custom_preset_roundtrip_via_ops(window, qapp):
    ops = window.menubar.view_menu.ops
    ops.set_preset(KeypadPreset.SCIENCE)
    qapp.processEvents()
    rec = ops.save_custom_preset("mine")
    assert get_app_state().active_custom_id == rec.id

    ops.set_preset(KeypadPreset.SIMPLE)
    qapp.processEvents()
    assert not _dock_open(window, DockKind.FUNCPAD)
    assert get_app_state().active_custom_id is None

    ops.apply_custom_preset(rec.id)
    qapp.processEvents()
    assert get_app_state().active_custom_id == rec.id
    assert _dock_open(window, DockKind.FUNCPAD)
    assert window.calc_widget.topbar.is_angle_visible() is True


def test_delete_active_custom_falls_back_to_builtin(window, qapp):
    ops = window.menubar.view_menu.ops
    ops.set_preset(KeypadPreset.SIMPLE)
    qapp.processEvents()
    rec = ops.save_custom_preset("temp")
    assert get_app_state().active_custom_id == rec.id
    ops.delete_custom_preset(rec.id)
    qapp.processEvents()
    assert get_app_state().active_custom_id is None
    assert not _dock_open(window, DockKind.FUNCPAD)


def test_active_custom_clears_builtin_checkmarks(window, qapp):
    view_menu = window.menubar.view_menu
    # Select Science the way the user does (triggers ops + checkmark update).
    view_menu._preset_actions[KeypadPreset.SCIENCE].trigger()
    qapp.processEvents()
    assert view_menu._preset_actions[KeypadPreset.SCIENCE].isChecked()

    rec = view_menu.ops.save_custom_preset("mine")
    view_menu._populate_custom_presets()  # what aboutToShow triggers
    assert not any(a.isChecked() for a in view_menu._preset_actions.values())
    assert view_menu._custom_preset_actions[rec.id].isChecked()


def test_angle_buttons_toggle_and_preset_reset(window, qapp):
    ops = window.menubar.view_menu.ops
    state = get_app_state()
    ops.set_preset(KeypadPreset.SIMPLE)
    qapp.processEvents()
    assert state.angle_visible is False

    ops.toggle_angle(True)  # manual show, independent of preset
    qapp.processEvents()
    assert state.angle_visible is True
    assert window.calc_widget.topbar.is_angle_visible()

    ops.set_preset(KeypadPreset.SIMPLE)  # switch re-applies canonical -> off
    qapp.processEvents()
    assert state.angle_visible is False
    assert not window.calc_widget.topbar.is_angle_visible()


def test_update_custom_preset_overwrites_layout(window, qapp):
    ops = window.menubar.view_menu.ops
    ops.set_preset(KeypadPreset.SCIENCE)
    qapp.processEvents()
    rec = ops.save_custom_preset("mine")  # captured with funcpad visible

    ops.set_preset(KeypadPreset.SIMPLE)
    qapp.processEvents()
    ops.update_custom_preset(rec.id)  # overwrite with SIMPLE (funcpad hidden)

    ops.set_preset(KeypadPreset.SCIENCE)
    qapp.processEvents()
    ops.apply_custom_preset(rec.id)
    qapp.processEvents()
    assert not _dock_open(window, DockKind.FUNCPAD)


def test_update_button_enabled_only_when_layout_differs(window, qapp):
    view_menu = window.menubar.view_menu
    ops = view_menu.ops
    ops.set_preset(KeypadPreset.SCIENCE)
    qapp.processEvents()
    rec = ops.save_custom_preset("mine")  # active; current == saved

    view_menu._populate_custom_presets()
    view_menu._on_preset_hover(view_menu._custom_preset_actions[rec.id])  # hover reveals bar
    assert not view_menu._preset_bar.update_btn.isEnabled()

    window._docks[DockKind.FUNCPAD].close()  # deviate from saved
    qapp.processEvents()
    view_menu._populate_custom_presets()
    view_menu._on_preset_hover(view_menu._custom_preset_actions[rec.id])
    assert view_menu._preset_bar.update_btn.isEnabled()
