# The look: look.toml read once into typed tables, one per UI area
from __future__ import annotations

import tomllib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, fields
from pathlib import Path
from typing import TYPE_CHECKING, NewType

from tcalc.typed_tables import Toml, build, field_hints, is_dataclass_type

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

LOOK_PATH = Path(__file__).parent / "look.toml"

# A color of the theme's [colors], by name
ColorName = NewType("ColorName", str)
FontFamily = NewType("FontFamily", str)


@dataclass(frozen=True, slots=True)
class Colors:
    color: ColorName
    text_color: ColorName


@dataclass(frozen=True, slots=True)
class Edge:
    width: int
    light_color: ColorName
    shadow_color: ColorName


@dataclass(frozen=True, slots=True)
class FontRange:
    min_pt: int
    max_pt: int


@dataclass(frozen=True, slots=True)
class Insets:
    y: int
    x: int


@dataclass(frozen=True, slots=True)
class Text:
    color: ColorName
    font: FontRange


@dataclass(frozen=True, slots=True)
class Button:
    color: ColorName
    hover_color: ColorName
    pressed_color: ColorName
    text: Text
    disabled: Colors
    checked: Colors
    radius: int
    edge: Edge
    padding: Insets


@dataclass(frozen=True, slots=True)
class Panel:
    background_color: ColorName
    text: Text
    border_color: ColorName
    hover_color: ColorName
    separator_color: ColorName
    list_background_color: ColorName
    radius: int
    padding: Insets


@dataclass(frozen=True, slots=True)
class FontsLook:
    family_default: FontFamily
    size_default: int
    family_monospace: FontFamily


@dataclass(frozen=True, slots=True)
class PaletteLook:
    window_color: ColorName
    window_text_color: ColorName
    base_color: ColorName
    text_color: ColorName
    button_color: ColorName
    button_text_color: ColorName
    highlight_color: ColorName
    highlighted_text_color: ColorName
    icon_color: ColorName


@dataclass(frozen=True, slots=True)
class ExpressionLook:
    text: Text
    selection: Colors
    slot_focus_color: ColorName


@dataclass(frozen=True, slots=True)
class DisplayLook:
    background_color: ColorName
    expression: ExpressionLook
    radical_line_color: ColorName
    radical_symbol_color: ColorName
    status_text_color: ColorName
    status_error_text_color: ColorName
    divider_height: int
    root_border_width: int


@dataclass(frozen=True, slots=True)
class ResultLook:
    text: Text
    fraction: Button


@dataclass(frozen=True, slots=True)
class KeypadLook:
    button: Button
    number: Button
    operator: Button
    action: Button
    trig: Button
    function: Button
    power: Button
    hover_border_color: ColorName
    symbol_color: ColorName
    compact_padding: Insets


@dataclass(frozen=True, slots=True)
class CustomPadLook:
    add_key: Button
    spinbox: Button
    spinbox_focus_border_color: ColorName
    toolbar_separator_color: ColorName
    menu: Panel


@dataclass(frozen=True, slots=True)
class MenuLook:
    panel: Panel
    item: Button
    selected_border_color: ColorName
    constants_symbol_color: ColorName
    item_margin: int
    item_min_width: int
    icon_padding_left: int
    icon_padding_right: int
    separator_height: int
    separator_margin: Insets


@dataclass(frozen=True, slots=True)
class HistoryLook:
    background_color: ColorName
    text: Text
    row_color: ColorName
    alternate_row_color: ColorName
    selected: Colors
    math_font_size: int
    expression: Text
    result: Text
    icon_button_size: int
    button: Button
    copy: Button
    delete: Button
    clear: Button
    mode: Button


@dataclass(frozen=True, slots=True)
class ToastLook:
    text: Text
    info_color: ColorName
    warn_color: ColorName
    error_color: ColorName
    padding: Insets
    radius: int


@dataclass(frozen=True, slots=True)
class Look:
    fonts: FontsLook
    palette: PaletteLook
    display: DisplayLook
    result: ResultLook
    memory: Button
    keypad: KeypadLook
    custom_pad: CustomPadLook
    picker: Panel
    menu: MenuLook
    history: HistoryLook
    options: Button
    tooltip: Panel
    toast: ToastLook
    dock: Text
    tabs: Text


# Picks a place from the look; a caller that resolves its color on every theme switch keeps it
type ColorPlace = Callable[[Look], ColorName]


@dataclass(frozen=True, slots=True)
class ColorField:
    path: tuple[str, ...]
    color: ColorName


@dataclass(frozen=True, slots=True)
class ValueField:
    path: tuple[str, ...]
    value: int | FontFamily


type LookField = ColorField | ValueField


def look_fields(table: DataclassInstance, path: tuple[str, ...] = ()) -> Iterator[LookField]:
    # A NewType is gone at runtime, so a color is told apart by the declared type, not the value
    hints = field_hints(type(table))
    for f in fields(table):
        value, hint, at = getattr(table, f.name), hints[f.name], (*path, f.name)
        if is_dataclass_type(hint):
            yield from look_fields(value, at)
        elif hint is ColorName:
            yield ColorField(at, value)
        else:
            yield ValueField(at, value)


def qss_name(field: LookField) -> str:
    # $keypad_number_color is [keypad.number] color
    return "_".join(field.path)


def _merged(base: Toml, over: Toml) -> Toml:
    if not (isinstance(base, dict) and isinstance(over, dict)):
        return over
    return base | {k: _merged(base[k], v) if k in base else v for k, v in over.items()}


def with_shared_buttons(table: dict[str, Toml]) -> dict[str, Toml]:
    # An area's [x.button] is where its other buttons start; each one writes only what differs
    spread = dict(table)
    for name, cls in (("keypad", KeypadLook), ("history", HistoryLook)):
        area = table.get(name, {})
        # [[keypad]] stays as it is for override to report
        if not isinstance(area, dict):
            continue
        area = dict(area)
        if "button" in area:
            shared = area["button"]
            for key, hint in field_hints(cls).items():
                if hint is Button and key != "button":
                    area[key] = _merged(shared, area.get(key, {}))
        spread[name] = area
    return spread


with open(LOOK_PATH, "rb") as _file:
    DEFAULT_LOOK: Look = build(Look, with_shared_buttons(tomllib.load(_file)), "look")
