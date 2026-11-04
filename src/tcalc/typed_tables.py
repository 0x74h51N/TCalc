#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
# TOML and JSON tables read into dataclasses by their fields
from __future__ import annotations

import dataclasses
import functools
import logging
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

_log = logging.getLogger(__name__)

# The annotations are strings (postponed), and get_type_hints compiles them again on every call
_hints = functools.cache(get_type_hints)


class TableError(Exception):
    """A table that does not match its dataclass."""


def build[T: DataclassInstance](cls: type[T], table: object, where: str) -> T:
    """*table* as a *cls*; a missing, unknown or wrongly typed key raises a TableError."""
    converted, errors = _convert_keys(table, _hints(cls).get, _convert_key, where)
    if errors:
        raise errors[0]
    for field in dataclasses.fields(cls):
        missing = field.default is dataclasses.MISSING
        if missing and field.default_factory is dataclasses.MISSING and field.name not in converted:
            raise TableError(f"{where}.{field.name}: missing")
    return cls(**converted)


def override[T: DataclassInstance](obj: T, table: object, where: str) -> T:
    """*obj* with the keys of *table* applied; a bad key is logged and skipped, never raised."""

    def convert(key: str, value: object, hint: Any, at: str) -> Any:
        # A theme table lays over the default one, so a nested table may name only some fields
        if _is_dataclass_type(hint):
            return override(getattr(obj, key), value, at)
        return _convert(value, hint, at)

    converted, errors = _convert_keys(table, _hints(type(obj)).get, convert, where)
    _log_all(errors)
    return dataclasses.replace(obj, **converted)


def values[V](table: object, kind: type[V], where: str) -> dict[str, V]:
    """The values of *table*, all of type *kind*; a wrongly typed one is logged and skipped."""
    converted, errors = _convert_keys(table, lambda _key: kind, _convert_key, where)
    _log_all(errors)
    return converted


def _convert_key(_key: str, value: object, hint: Any, where: str) -> Any:
    return _convert(value, hint, where)


def _convert_keys(
    table: object,
    hint_of: Callable[[str], Any],
    convert: Callable[[str, object, Any, str], Any],
    where: str,
) -> tuple[dict[str, Any], list[TableError]]:
    if not isinstance(table, dict):
        return {}, [TableError(f"{where}: expected a table, got {type(table).__name__}")]
    converted: dict[str, Any] = {}
    errors: list[TableError] = []
    for key, value in table.items():
        hint = hint_of(key)
        if hint is None:
            errors.append(TableError(f"{where}.{key}: unknown key"))
            continue
        try:
            converted[key] = convert(key, value, hint, f"{where}.{key}")
        except TableError as error:
            errors.append(error)
    return converted, errors


def _is_dataclass_type(hint: Any) -> bool:
    return isinstance(hint, type) and dataclasses.is_dataclass(hint)


def _log_all(errors: list[TableError]) -> None:
    for error in errors:
        _log.warning("%s", error)


def _convert(value: object, hint: Any, where: str) -> Any:
    if _is_dataclass_type(hint):
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
