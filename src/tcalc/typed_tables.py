#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
# TOML and JSON tables read into dataclasses by their fields
from __future__ import annotations

import dataclasses
import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

_log = logging.getLogger(__name__)


class TableError(Exception):
    """A table that does not match its dataclass."""


def build[T: DataclassInstance](cls: type[T], table: object, where: str) -> T:
    """*table* as a *cls*; a missing, unknown or wrongly typed key raises a TableError."""
    table = _table(table, where)
    hints = get_type_hints(cls)
    for key in table:
        if key not in hints:
            raise TableError(f"{where}.{key}: unknown key")
    values: dict[str, Any] = {}
    for field in dataclasses.fields(cls):
        if field.name in table:
            values[field.name] = _convert(
                table[field.name], hints[field.name], f"{where}.{field.name}"
            )
        elif field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
            raise TableError(f"{where}.{field.name}: missing")
    return cls(**values)


def override[T: DataclassInstance](obj: T, table: object, where: str) -> T:
    """*obj* with the keys of *table* applied; a bad key is logged and skipped, never raised."""
    hints = get_type_hints(type(obj))
    changed: dict[str, Any] = {}
    for key, value in _logged_table(table, where).items():
        try:
            if key not in hints:
                raise TableError(f"{where}.{key}: unknown key")
            changed[key] = _convert(value, hints[key], f"{where}.{key}")
        except TableError as error:
            _log.warning("%s", error)
    return dataclasses.replace(obj, **changed)


def values[V](table: object, kind: type[V], where: str) -> dict[str, V]:
    """The values of *table*, all of type *kind*; a wrongly typed one is logged and skipped."""
    result: dict[str, V] = {}
    for key, value in _logged_table(table, where).items():
        try:
            result[key] = _convert(value, kind, f"{where}.{key}")
        except TableError as error:
            _log.warning("%s", error)
    return result


def _logged_table(table: object, where: str) -> dict[str, Any]:
    try:
        return _table(table, where)
    except TableError as error:
        _log.warning("%s", error)
        return {}


def _table(table: object, where: str) -> dict[str, Any]:
    if not isinstance(table, dict):
        raise TableError(f"{where}: expected a table, got {type(table).__name__}")
    return table


def _convert(value: object, hint: Any, where: str) -> Any:
    if isinstance(hint, type) and dataclasses.is_dataclass(hint):
        return build(hint, value, where)
    if get_origin(hint) is tuple:
        if not isinstance(value, list):
            raise TableError(f"{where}: expected a list, got {type(value).__name__}")
        item = get_args(hint)[0]
        return tuple(_convert(v, item, where) for v in value)
    if isinstance(hint, type) and issubclass(hint, Enum):
        return _enum(value, hint, where)
    # TOML writes a whole number without a point; it is still a valid float
    if hint is float and type(value) is int:
        return float(value)
    if hint is Path and isinstance(value, str):
        return Path(value)
    # type() and not isinstance(): a bool is an int to isinstance
    if type(value) is not hint:
        raise TableError(f"{where}: expected {hint.__name__}, got {type(value).__name__}")
    return value


def _enum[E: Enum](value: object, enum: type[E], where: str) -> E:
    # Theme files name a member by value ("contain"); config.toml names Qt's by name ("InCubic")
    try:
        return enum(value)
    except ValueError:
        if isinstance(value, str) and value in enum.__members__:
            return enum[value]
    raise TableError(f"{where}: expected {enum.__name__}, got {type(value).__name__} {value!r}")
