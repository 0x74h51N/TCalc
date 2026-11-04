# The look: look.toml read once into typed tables, one per UI area
from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import dataclass, fields
from pathlib import Path

from tcalc.typed_tables import build

LOOK_PATH = Path(__file__).parent / "look.toml"


@dataclass(frozen=True, slots=True)
class FontsLook:
    family_default: str
    size_default: int
    family_monospace: str


@dataclass(frozen=True, slots=True)
class PaletteLook:
    window_color: str
    window_text_color: str
    base_color: str
    text_color: str
    button_color: str
    button_text_color: str
    highlight_color: str
    highlighted_text_color: str


@dataclass(frozen=True, slots=True)
class IconsLook:
    color: str


@dataclass(frozen=True, slots=True)
class DisplayLook:
    background_color: str
    expression_text_color: str
    expression_selection_color: str
    expression_selection_text_color: str
    expression_slot_focus_color: str
    radical_line_color: str
    radical_symbol_color: str
    status_text_color: str
    status_error_text_color: str
    divider_height: int
    root_border_width: int
    expression_font_size: int
    expr_max_pt: int


@dataclass(frozen=True, slots=True)
class ResultLook:
    text_color: str
    fraction_button_color: str
    fraction_button_hover_color: str
    fraction_button_pressed_color: str
    fraction_icon_color: str
    font_size: int
    max_pt: int
    btn_padding: int
    frac_toggle_radius: int


@dataclass(frozen=True, slots=True)
class MemoryLook:
    button_color: str
    button_text_color: str
    button_hover_color: str
    button_pressed_color: str
    button_disabled_color: str
    button_disabled_text_color: str
    pad_y: int
    pad_x: int


@dataclass(frozen=True, slots=True)
class KeypadLook:
    number_color: str
    number_text_color: str
    number_pressed_color: str
    operator_color: str
    operator_text_color: str
    operator_pressed_color: str
    action_color: str
    action_text_color: str
    action_pressed_color: str
    equals_color: str
    equals_text_color: str
    equals_pressed_color: str
    trig_color: str
    trig_text_color: str
    trig_pressed_color: str
    function_color: str
    function_text_color: str
    function_pressed_color: str
    power_color: str
    power_text_color: str
    power_pressed_color: str
    equals_border_color: str
    hover_border_color: str
    checked_color: str
    disabled_color: str
    disabled_text_color: str
    symbol_color: str
    radius: int
    button_padding: int
    compact_pad_y: int
    compact_pad_x: int
    min_pt: int
    max_pt: int


@dataclass(frozen=True, slots=True)
class CustomPadLook:
    add_key_color: str
    add_key_hover_color: str
    spinbox_color: str
    spinbox_text_color: str
    spinbox_focus_border_color: str
    toolbar_separator_color: str
    menu_background_color: str
    menu_text_color: str
    menu_border_color: str
    menu_selected_color: str
    menu_separator_color: str


@dataclass(frozen=True, slots=True)
class PickerLook:
    background_color: str
    border_color: str
    list_background_color: str
    text_color: str
    hover_color: str
    font_size: int


@dataclass(frozen=True, slots=True)
class MenuLook:
    background_color: str
    text_color: str
    border_color: str
    selected_color: str
    selected_text_color: str
    selected_border_color: str
    disabled_text_color: str
    separator_color: str
    constants_symbol_color: str
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
    background_color: str
    text_color: str
    row_color: str
    alternate_row_color: str
    selected_color: str
    selected_text_color: str


@dataclass(frozen=True, slots=True)
class OptionsLook:
    text_color: str
    hover_color: str
    checked_color: str
    checked_text_color: str
    radius: int
    padding_y: int
    padding_x: int


@dataclass(frozen=True, slots=True)
class IconButtonLook:
    color: str
    text_color: str
    hover_color: str
    pressed_color: str
    light_color: str
    shadow_color: str
    radius: int
    padding: int


@dataclass(frozen=True, slots=True)
class TooltipLook:
    background_color: str
    border_color: str
    text_color: str
    radius: int
    padding: int


@dataclass(frozen=True, slots=True)
class ToastLook:
    text_color: str
    info_color: str
    warn_color: str
    error_color: str
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
type ColorPlace = Callable[[Look], str]


def color_places(look: Look) -> dict[str, str]:
    return {
        f"{area.name}_{f.name}": getattr(getattr(look, area.name), f.name)
        for area in fields(look)
        for f in fields(getattr(look, area.name))
        if f.name.endswith("_color")
    }


with open(LOOK_PATH, "rb") as _file:
    DEFAULT_LOOK: Look = build(Look, tomllib.load(_file), "look")
