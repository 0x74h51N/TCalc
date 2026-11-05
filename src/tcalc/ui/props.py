#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The Qt properties the stylesheets select on, and their values; test_props keeps the QSS in step
from __future__ import annotations

from enum import StrEnum


class Prop(StrEnum):
    UI_ROLE = "uiRole"
    KEYPAD_ROLE = "keypadRole"
    OPTION_ROLE = "optionRole"
    STATUS_KIND = "statusKind"
    TOAST_LEVEL = "toastLevel"
    EXPR_SLOT_KIND = "exprSlotKind"
    LATEX_KIND = "LatexKind"
    PRESSED = "pressed"
    ADD_BUTTON = "addButton"
    PAD_KEY = "padKey"
    EXPR_SLOT = "exprSlot"
    EXPR_INPUT = "exprInput"
    CUSTOM_PAD_MENU = "customPadMenu"
    RAISED = "raised"


class UiRole(StrEnum):
    KEYPAD = "keypad"
    HISTORY_LIST = "historyList"
    ICON_BUTTON = "iconButton"
    TOOLBAR_TOGGLE = "toolbarToggle"


class KeypadRole(StrEnum):
    DIGIT = "digit"
    OPERATOR = "operator"
    EQUALS = "equals"
    ACTION = "action"
    TRIG = "trig"
    FUNCTION = "function"
    POWER = "power"
    MEMORY = "memory"
    CUSTOM = "custom"


class OptionRole(StrEnum):
    OPTION = "option"


class StatusKind(StrEnum):
    INFO = "info"
    ERROR = "error"
