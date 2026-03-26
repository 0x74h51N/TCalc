#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable, Generic, TypeVar, cast

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from tcalc.app_state import AppState, CalculatorMode
from tcalc.ui.controller.menubar import EditOperations, FileOperations, SettingsOperations
from tcalc.ui.utils import get_icon

if TYPE_CHECKING:
    from ..keyboard import ShortcutManager
    from ..window import MainWindow

OpsType = TypeVar("OpsType", FileOperations, EditOperations, SettingsOperations)


class MenuActionType(Enum):
    """Menu action item type - determines callback behavior and context."""

    OPS = "ops"  # fn(ops) - EditOperations/FileOperations/SettingsOperations
    TOGGLE = "toggle"  # fn(ops, checked) - with app_state
    BUTTON = "button"  # fn(ctx)


@dataclass(frozen=True, slots=True)
class BaseMenuContext:
    window: MainWindow
    shortcuts: ShortcutManager


@dataclass(frozen=True, slots=True)
class OpsMenuContext(BaseMenuContext, Generic[OpsType]):
    ops: OpsType


@dataclass(frozen=True, slots=True)
class ToggleMenuContext(OpsMenuContext[OpsType], Generic[OpsType]):
    app_state: AppState


TMenuContext = TypeVar("TMenuContext", bound=BaseMenuContext, contravariant=True)


class MenuItem(ABC, Generic[TMenuContext]):
    @abstractmethod
    def add_to(self, menu: QMenu, ctx: TMenuContext) -> list[tuple[MenuActionItem, QAction]]: ...


class MenuSeparatorItem(MenuItem[BaseMenuContext]):
    def add_to(self, menu: QMenu, ctx: BaseMenuContext) -> list[tuple[MenuActionItem, QAction]]:
        menu.addSeparator()
        return []


@dataclass(frozen=True, slots=True, kw_only=True)
class MenuActionItem(MenuItem[TMenuContext], Generic[TMenuContext]):
    """Single unified action item. Type determines callback behavior."""

    text: str
    icon: str = ""
    checkable: bool = False
    enabled: bool = True
    item_type: MenuActionType = MenuActionType.OPS
    checked_getter: Callable[[AppState], bool] | None = None
    fn: Callable
    mode: CalculatorMode | None = None

    def _create_action(self, ctx: BaseMenuContext) -> QAction:
        action = QAction(get_icon(self.icon), self.text, ctx.window)
        action.setCheckable(self.checkable)
        action.setEnabled(self.enabled)
        return action

    def _setup_initial_state(self, action: QAction, ctx: TMenuContext) -> None:
        """Setup checked state and shortcuts."""
        if self.item_type == MenuActionType.TOGGLE and self.checked_getter is not None:
            toggle_ctx = cast(ToggleMenuContext, ctx)
            action.setChecked(self.checked_getter(toggle_ctx.app_state))

        if self.item_type in (MenuActionType.OPS, MenuActionType.TOGGLE):
            ctx.shortcuts.bind_action(self.fn, action)

    def _build_callback(self, ctx: TMenuContext) -> Callable:
        """Build callback based on item type."""
        match self.item_type:
            case MenuActionType.OPS:
                assert callable(self.fn)
                ops_ctx = cast(OpsMenuContext, ctx)
                return lambda: self.fn(ops_ctx.ops)
            case MenuActionType.TOGGLE:
                assert callable(self.fn)
                toggle_ctx = cast(ToggleMenuContext, ctx)
                return lambda checked: self.fn(toggle_ctx.ops, checked)
            case MenuActionType.BUTTON:
                assert callable(self.fn)
                return lambda: self.fn(ctx)

    def add_to(self, menu: QMenu, ctx: TMenuContext) -> list[tuple[MenuActionItem, QAction]]:
        action = self._create_action(ctx)
        self._setup_initial_state(action, ctx)
        action.triggered.connect(self._build_callback(ctx))
        menu.addAction(action)
        return [(self, action)]


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmenuItem(MenuItem[TMenuContext], Generic[TMenuContext]):
    """A submenu container. Adds a child QMenu and populates it with *items*."""

    text: str
    icon: str = ""
    items: tuple[MenuItem, ...] = ()

    def add_to(self, menu: QMenu, ctx: TMenuContext) -> list[tuple[MenuActionItem, QAction]]:
        submenu = menu.addMenu(get_icon(self.icon), self.text)
        results: list[tuple[MenuActionItem, QAction]] = []
        for item in self.items:
            results.extend(item.add_to(submenu, ctx))
        return results
