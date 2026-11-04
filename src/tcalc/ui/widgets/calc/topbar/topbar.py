from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from tcalc.app_state import AngleUnit
from tcalc.theme import get_theme
from tcalc.ui.config import CONFIG
from tcalc.ui.props import KeypadRole
from tcalc.ui.styles import theme_events
from tcalc.ui.widgets.common import KeyButton, OptionGroup
from tcalc.ui.widgets.common.types import KeyDef
from tcalc.ui.widgets.utils import fit_radius, key_fit_timer, set_raised, shortest_side

from ...keypad.utils import (
    add_keys_to_grid,
    handle_button_clicked,
    make_grid,
)
from .defins import ANGLE_OPTIONS, MEMORY_L_KEYS, MemoryKey

MEMORY_SELECTOR = 'QPushButton[keypadRole="memory"]'


class TopBar(QWidget):
    key_pressed = Signal(str, object)
    angle_changed = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._buttons: dict[str, QPushButton] = {}

        topbar = CONFIG.calc.topbar

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            topbar.side_margin,
            topbar.top_margin,
            topbar.side_margin,
            topbar.bottom_margin,
        )
        layout.setSpacing(topbar.grid_spacing)

        self._angle_group = OptionGroup(
            options=ANGLE_OPTIONS,
            current=AngleUnit.DEG,
            look=lambda look: look.options,
            parent=self,
            tooltips={
                AngleUnit.DEG: "Degrees",
                AngleUnit.RAD: "Radians",
                AngleUnit.GRAD: "Gradians",
            },
        )
        self._angle_group.selection_changed.connect(self.angle_changed)
        layout.addWidget(self._angle_group)

        layout.addStretch(topbar.spacer_stretch)

        # Memory keys
        self._memory_widget = QWidget(self)
        self._memory_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        memory_grid = make_grid(topbar.grid_spacing, self._memory_widget)
        add_keys_to_grid(MEMORY_L_KEYS, memory_grid, self._add_key)
        layout.addWidget(self._memory_widget)

        # The keys take their size from the layout and the theme font
        self._memory_radius: int | None = None
        self._fit_timer = key_fit_timer(self, self._fit_memory_radius)
        theme_events.applied.connect(self._fit_timer.start)
        self._update_raised()
        theme_events.applied.connect(self._update_raised)

    def _update_raised(self) -> None:
        set_raised(self._memory_widget, get_theme().look.memory.edge_width > 0)

    def _fit_memory_radius(self) -> None:
        side = shortest_side(self._buttons.values())
        if side is not None:
            radius = get_theme().look.memory.radius
            self._memory_radius = fit_radius(
                self._memory_widget, MEMORY_SELECTOR, radius, side, self._memory_radius
            )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._fit_timer.start()

    def _add_key(self, key_def: KeyDef, role: KeypadRole, grid) -> None:
        button = KeyButton(key_def, role, grid.parentWidget() or self)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.clicked.connect(
            lambda _=False, kd=key_def: handle_button_clicked(self.key_pressed, kd)
        )
        self._buttons[key_def.label] = button
        button.place(grid, key_def)

    def get_button(self, label: str) -> Optional[QPushButton]:
        return self._buttons.get(label)

    def set_angle_visible(self, visible: bool) -> None:
        self._angle_group.setVisible(visible)

    def is_angle_visible(self) -> bool:
        return self._angle_group.isVisibleTo(self)

    def set_angle(self, unit: AngleUnit) -> None:
        self._angle_group.set_current(unit)

    def set_memory_available(self, available: bool) -> None:
        for key in (MemoryKey.MC, MemoryKey.MR):
            btn = self._buttons.get(key.value)
            if btn is not None:
                btn.setEnabled(available)
