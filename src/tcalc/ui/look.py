# The look: look.toml read once into typed tables, one per UI area
from __future__ import annotations

import tomllib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, fields
from pathlib import Path
from typing import TYPE_CHECKING, NewType

from tcalc.typed_tables import build, field_hints, is_dataclass_type

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

LOOK_PATH = Path(__file__).parent / "look.toml"

# A color of the theme's [colors], by name
ColorName = NewType("ColorName", str)
FontFamily = NewType("FontFamily", str)


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


@dataclass(frozen=True, slots=True)
class IconsLook:
    color: ColorName


@dataclass(frozen=True, slots=True)
class DisplayLook:
    background_color: ColorName
    expression_text_color: ColorName
    expression_selection_color: ColorName
    expression_selection_text_color: ColorName
    expression_slot_focus_color: ColorName
    radical_line_color: ColorName
    radical_symbol_color: ColorName
    status_text_color: ColorName
    status_error_text_color: ColorName
    divider_height: int
    root_border_width: int
    expression_font_size: int
    expr_max_pt: int


@dataclass(frozen=True, slots=True)
class ResultLook:
    text_color: ColorName
    fraction_button_color: ColorName
    fraction_button_hover_color: ColorName
    fraction_button_pressed_color: ColorName
    fraction_icon_color: ColorName
    font_size: int
    max_pt: int
    btn_padding: int
    frac_toggle_radius: int


@dataclass(frozen=True, slots=True)
class MemoryLook:
    button_color: ColorName
    button_text_color: ColorName
    button_hover_color: ColorName
    button_pressed_color: ColorName
    button_disabled_color: ColorName
    button_disabled_text_color: ColorName
    pad_y: int
    pad_x: int


@dataclass(frozen=True, slots=True)
class KeyRoleLook:
    color: ColorName
    text_color: ColorName
    pressed_color: ColorName


@dataclass(frozen=True, slots=True)
class KeypadLook:
    number: KeyRoleLook
    operator: KeyRoleLook
    action: KeyRoleLook
    trig: KeyRoleLook
    function: KeyRoleLook
    power: KeyRoleLook
    hover_border_color: ColorName
    checked_color: ColorName
    disabled_color: ColorName
    disabled_text_color: ColorName
    symbol_color: ColorName
    radius: int
    button_padding: int
    compact_pad_y: int
    compact_pad_x: int
    min_pt: int
    max_pt: int


@dataclass(frozen=True, slots=True)
class CustomPadLook:
    add_key_color: ColorName
    add_key_hover_color: ColorName
    spinbox_color: ColorName
    spinbox_text_color: ColorName
    spinbox_focus_border_color: ColorName
    toolbar_separator_color: ColorName
    menu_background_color: ColorName
    menu_text_color: ColorName
    menu_border_color: ColorName
    menu_selected_color: ColorName
    menu_separator_color: ColorName


@dataclass(frozen=True, slots=True)
class PickerLook:
    background_color: ColorName
    border_color: ColorName
    list_background_color: ColorName
    text_color: ColorName
    hover_color: ColorName
    font_size: int


@dataclass(frozen=True, slots=True)
class MenuLook:
    background_color: ColorName
    text_color: ColorName
    border_color: ColorName
    selected_color: ColorName
    selected_text_color: ColorName
    selected_border_color: ColorName
    disabled_text_color: ColorName
    separator_color: ColorName
    constants_symbol_color: ColorName
    item_padding_horizontal: int
    item_padding_vertical: int
    item_margin: int
    item_min_width: int
    item_border_radius: int
    icon_padding_left: int
    icon_padding_right: int
    separator_height: int
    separator_margin_vertical: int
    separator_margin_horizontal: int
    padding: int
    font_size: int


@dataclass(frozen=True, slots=True)
class HistoryLook:
    background_color: ColorName
    text_color: ColorName
    row_color: ColorName
    alternate_row_color: ColorName
    selected_color: ColorName
    selected_text_color: ColorName


@dataclass(frozen=True, slots=True)
class OptionsLook:
    text_color: ColorName
    hover_color: ColorName
    checked_color: ColorName
    checked_text_color: ColorName
    radius: int
    padding_y: int
    padding_x: int


@dataclass(frozen=True, slots=True)
class IconButtonLook:
    color: ColorName
    text_color: ColorName
    hover_color: ColorName
    pressed_color: ColorName
    light_color: ColorName
    shadow_color: ColorName
    radius: int
    padding: int


@dataclass(frozen=True, slots=True)
class TooltipLook:
    background_color: ColorName
    border_color: ColorName
    text_color: ColorName
    radius: int
    padding: int


@dataclass(frozen=True, slots=True)
class ToastLook:
    text_color: ColorName
    info_color: ColorName
    warn_color: ColorName
    error_color: ColorName
    pad_y: int
    pad_x: int
    radius: int
    font_size: int


@dataclass(frozen=True, slots=True)
class Look:
    fonts: FontsLook
    palette: PaletteLook
    icons: IconsLook
    display: DisplayLook
    result: ResultLook
    memory: MemoryLook
    keypad: KeypadLook
    custom_pad: CustomPadLook
    picker: PickerLook
    menu: MenuLook
    history: HistoryLook
    options: OptionsLook
    icon_button: IconButtonLook
    tooltip: TooltipLook
    toast: ToastLook


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


with open(LOOK_PATH, "rb") as _file:
    DEFAULT_LOOK: Look = build(Look, tomllib.load(_file), "look")
