from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, TypeVar

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from tcalc.app_state import AppState, CalculatorMode
from tcalc.ui.controller.menubar import EditOperations, FileOperations, SettingsOperations
from tcalc.ui.keyboard.shortcuts import ShortcutId

if TYPE_CHECKING:
    from ..keyboard import ShortcutManager
    from ..window import MainWindow

OpsType = TypeVar("OpsType", FileOperations, EditOperations, SettingsOperations)


def _get_icon(theme_name: str) -> QIcon:
    if not theme_name:
        return QIcon()
    icon = QIcon.fromTheme(theme_name)
    return icon if not icon.isNull() else QIcon()


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


@dataclass(frozen=True, slots=True)
class ModeMenuContext(BaseMenuContext):
    on_mode_selected: Callable[[CalculatorMode], None]


TMenuContext = TypeVar("TMenuContext", bound=BaseMenuContext, contravariant=True)


class MenuItem(ABC, Generic[TMenuContext]):
    @abstractmethod
    def add_to(self, menu: QMenu, ctx: TMenuContext) -> QAction | None: ...


class MenuSeparatorItem(MenuItem[BaseMenuContext]):
    def add_to(self, menu: QMenu, ctx: BaseMenuContext) -> None:
        menu.addSeparator()
        return None


@dataclass(frozen=True, slots=True)
class MenuActionItem(MenuItem[TMenuContext], Generic[TMenuContext]):
    text: str
    icon: str = ""
    checkable: bool = False
    enabled: bool = True

    def _create_action(self, ctx: BaseMenuContext) -> QAction:
        action = QAction(_get_icon(self.icon), self.text, ctx.window)
        action.setCheckable(self.checkable)
        action.setEnabled(self.enabled)
        return action


@dataclass(frozen=True, slots=True)
class MenuButtonItem(MenuActionItem[BaseMenuContext]):
    on_trigger: Callable[[BaseMenuContext], None] | None = None

    def add_to(self, menu: QMenu, ctx: BaseMenuContext) -> QAction:
        action = self._create_action(ctx)
        if self.on_trigger is not None:
            action.triggered.connect(lambda _checked=False, fn=self.on_trigger, ctx=ctx: fn(ctx))
        menu.addAction(action)
        return action


@dataclass(frozen=True, slots=True, kw_only=True)
class MenuOpsActionItem(MenuActionItem[OpsMenuContext[OpsType]], Generic[OpsType]):
    action_id: ShortcutId
    fn: Callable[[OpsType], None]

    def add_to(self, menu: QMenu, ctx: OpsMenuContext[OpsType]) -> QAction:
        action = self._create_action(ctx)
        ctx.shortcuts.bind_action(self.action_id, action)
        action.triggered.connect(lambda _checked=False, fn=self.fn, ops=ctx.ops: fn(ops))
        menu.addAction(action)
        return action


@dataclass(frozen=True, slots=True, kw_only=True)
class MenuToggleItem(MenuActionItem[ToggleMenuContext[OpsType]], Generic[OpsType]):
    toggle_fn: Callable[[OpsType, bool], None]
    checked_attr: str

    def add_to(self, menu: QMenu, ctx: ToggleMenuContext[OpsType]) -> QAction:
        action = self._create_action(ctx)
        action.setChecked(bool(getattr(ctx.app_state, self.checked_attr)))
        ctx.shortcuts.bind_action(self.toggle_fn, action)
        action.triggered.connect(lambda checked, fn=self.toggle_fn, ops=ctx.ops: fn(ops, checked))
        menu.addAction(action)
        return action


@dataclass(frozen=True, slots=True, kw_only=True)
class MenuModeItem(MenuActionItem[ModeMenuContext]):
    mode: CalculatorMode

    def add_to(self, menu: QMenu, ctx: ModeMenuContext) -> QAction:
        action = self._create_action(ctx)
        ctx.shortcuts.bind_action(self.mode, action)
        action.triggered.connect(lambda _checked, m=self.mode: ctx.on_mode_selected(m))
        menu.addAction(action)
        return action
