#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QSettings


@dataclass
class LayoutPreset:
    id: int
    name: str
    state: QByteArray
    angle_visible: bool


class LayoutPresetStore:
    _IDS_KEY = "layout_presets/ids"

    def __init__(self) -> None:
        self._settings = QSettings("TCalc", "TCalc")

    def _ids(self) -> list[int]:
        raw = self._settings.value(self._IDS_KEY, [])
        return [int(str(i)) for i in raw] if isinstance(raw, list) else []

    def _set_ids(self, ids: list[int]) -> None:
        self._settings.setValue(self._IDS_KEY, ids)

    def list(self) -> list[LayoutPreset]:
        out: list[LayoutPreset] = []
        for pid in self._ids():
            rec = self.get(pid)
            if rec is not None:
                out.append(rec)
        return out

    def get(self, preset_id: int) -> LayoutPreset | None:
        if preset_id not in self._ids():
            return None
        base = f"layout_presets/{preset_id}/"
        name = str(self._settings.value(base + "name", ""))
        state = self._settings.value(base + "state", QByteArray())
        if not isinstance(state, QByteArray):
            state = QByteArray()
        angle = bool(self._settings.value(base + "angle_visible", False, type=bool))
        return LayoutPreset(preset_id, name, state, angle)

    def add(self, name: str, state: QByteArray, angle_visible: bool) -> LayoutPreset:
        ids = self._ids()
        new_id = (max(ids) + 1) if ids else 0
        base = f"layout_presets/{new_id}/"
        self._settings.setValue(base + "name", name)
        self._settings.setValue(base + "state", state)
        self._settings.setValue(base + "angle_visible", angle_visible)
        self._set_ids(ids + [new_id])
        return LayoutPreset(new_id, name, state, angle_visible)

    def rename(self, preset_id: int, name: str) -> None:
        if preset_id in self._ids():
            self._settings.setValue(f"layout_presets/{preset_id}/name", name)

    def update(self, preset_id: int, state: QByteArray, angle_visible: bool) -> None:
        if preset_id not in self._ids():
            return
        base = f"layout_presets/{preset_id}/"
        self._settings.setValue(base + "state", state)
        self._settings.setValue(base + "angle_visible", angle_visible)

    def delete(self, preset_id: int) -> None:
        ids = self._ids()
        if preset_id not in ids:
            return
        self._settings.remove(f"layout_presets/{preset_id}")
        self._set_ids([i for i in ids if i != preset_id])
