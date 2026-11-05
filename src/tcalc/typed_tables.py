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
from types import GenericAlias, UnionType
from typing import TYPE_CHECKING, NewType, TypeGuard, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

_log = logging.getLogger(__name__)

# What tomllib and json give
type Toml = int | float | bool | str | list[Toml] | dict[str, Toml]
# What a converted field holds
type Value = int | float | bool | str | Path | Enum | tuple[Value, ...] | DataclassInstance
# What a field may be declared as
type Hint = type | GenericAlias | NewType

# The annotations are strings (postponed), and get_type_hints compiles them again on every call
field_hints: Callable[[type], dict[str, Hint]] = functools.cache(get_type_hints)


class TableError(Exception):
    """A table that does not match its dataclass."""


def build[T: DataclassInstance](cls: type[T], table: Toml, where: str) -> T:
    """*table* as a *cls*; a missing, unknown or wrongly typed key raises a TableError."""
    converted, errors = _convert_keys(table, field_hints(cls).get, _convert_key, where)
    if errors:
        raise errors[0]
    for field in dataclasses.fields(cls):
        missing = field.default is dataclasses.MISSING
        if missing and field.default_factory is dataclasses.MISSING and field.name not in converted:
            raise TableError(f"{where}.{field.name}: missing")
    return cls(**converted)


def override[T: DataclassInstance](obj: T, table: Toml, where: str) -> T:
    """*obj* with the keys of *table* applied; a bad key is logged and skipped, never raised."""

    def convert(key: str, value: Toml, hint: Hint, at: str) -> Value:
        # A theme table lays over the default one, so a nested table may name only some fields
        if is_dataclass_type(hint):
            current: DataclassInstance = getattr(obj, key)
            return override(current, value, at)
        return _convert(value, hint, at)

    converted, errors = _convert_keys(table, field_hints(type(obj)).get, convert, where)
    _log_all(errors)
    return dataclasses.replace(obj, **converted)


def values[V: Value](table: Toml, kind: type[V], where: str) -> dict[str, V]:
    """The values of *table*, all of type *kind*; a wrongly typed one is logged and skipped."""

    def convert(_key: str, value: Toml, _hint: Hint, at: str) -> V:
        if type(value) is not kind:
            raise TableError(f"{at}: expected {kind.__name__}, got {type(value).__name__}")
        return value

    converted, errors = _convert_keys(table, lambda _key: kind, convert, where)
    _log_all(errors)
    return converted


def _convert_key(_key: str, value: Toml, hint: Hint, where: str) -> Value:
    return _convert(value, hint, where)


def _convert_keys[R](
    table: Toml,
    hint_of: Callable[[str], Hint | None],
    convert: Callable[[str, Toml, Hint, str], R],
    where: str,
) -> tuple[dict[str, R], list[TableError]]:
    if not isinstance(table, dict):
        return {}, [TableError(f"{where}: expected a table, got {type(table).__name__}")]
    converted: dict[str, R] = {}
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


def is_dataclass_type(hint: Hint) -> TypeGuard[type[DataclassInstance]]:
    return isinstance(hint, type) and dataclasses.is_dataclass(hint)


def _log_all(errors: list[TableError]) -> None:
    for error in errors:
        _log.warning("%s", error)


def _convert(value: Toml, hint: Hint, where: str) -> Value:
    if isinstance(hint, NewType):
        # A NewType is its supertype at runtime: a ColorName is a str
        return _convert(value, hint.__supertype__, where)
    if is_dataclass_type(hint):
        return build(hint, value, where)
    if get_origin(hint) is UnionType:
        arms = get_args(hint)
        for arm in arms:
            try:
                return _convert(value, arm, where)
            except TableError:
                pass
        names = " or ".join(arm.__name__ for arm in arms)
        raise TableError(f"{where}: expected {names}, got {type(value).__name__}")
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
    # type() and not isinstance(): a bool is an int to isinstance. A list or a table reaches a
    # field only as a tuple or a dataclass above, so what is left is a scalar
    if type(value) is hint and isinstance(value, int | float | str):
        return value
    raise TableError(f"{where}: expected {hint.__name__}, got {type(value).__name__}")


def _enum[E: Enum](value: Toml, enum: type[E], where: str) -> E:
    # Theme files name a member by value ("contain"); config.toml names Qt's by name ("InCubic")
    try:
        return enum(value)
    except ValueError:
        if isinstance(value, str) and value in enum.__members__:
            return enum[value]
    raise TableError(f"{where}: expected {enum.__name__}, got {type(value).__name__} {value!r}")
