#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#


from __future__ import annotations

import calc_native
from calc_native import Calculator as NativeCalculator
from calc_native import CalculatorError as NativeCalculatorError
from calc_native import Rational as NativeRational

try:
    from calc_native import BigComplex as NativeBigComplex
    from calc_native import BigReal as NativeBigReal
except ImportError:  # pragma: no cover
    import logging

    logging.getLogger(__name__).exception(
        "Failed to import calc_native.BigReal; native module is required."
    )
    raise

from tcalc.errors import ErrorKind, raise_error

from .constants import E
from .ops import Operation

_I64_MAX = (1 << 63) - 1
_I64_MIN = -(1 << 63)


def _to_rational(v: object) -> NativeRational | None:
    """Convert int to Rational; floats are never coerced."""
    if isinstance(v, NativeRational):
        return v
    if not isinstance(v, int) or isinstance(v, bool):
        return None
    if v < _I64_MIN or v > _I64_MAX:
        return None
    return NativeRational(v)


def _rational_downcast(args: tuple[object, ...]) -> tuple[object, ...]:
    """Downcast all Rational values to float."""
    return tuple(a.to_double() if isinstance(a, NativeRational) else a for a in args)


class Calculator:
    """Python wrapper for the native C++ calculator engine."""

    def __init__(self) -> None:
        self._native = NativeCalculator()

    def _to_big(self, v: object):
        if isinstance(v, NativeBigReal):
            return v
        if isinstance(v, NativeRational):
            return NativeBigReal(repr(v.to_double()))
        return NativeBigReal(repr(v))

    def _to_big_complex(self, v: object):
        if isinstance(v, NativeBigComplex):
            return v
        if isinstance(v, NativeRational):
            return NativeBigComplex(repr(v.to_double()))
        if not isinstance(v, (complex, NativeBigReal, int, float)):
            return v
        if isinstance(v, complex):
            return NativeBigComplex(repr(v.real), repr(v.imag))
        if isinstance(v, NativeBigReal):
            return NativeBigComplex(v)
        return NativeBigComplex(repr(v))

    def _to_complex(self, value: object) -> object:
        if isinstance(value, complex):
            return value
        if isinstance(value, NativeRational):
            return complex(value.to_double(), 0.0)
        if isinstance(value, (int, float)):
            return complex(float(value), 0.0)
        return value

    def _coerce_args(self, name: str, args: tuple[object, ...]) -> tuple[object, ...]:
        try:
            op = Operation(name)
        except ValueError:
            op = None
        supports_big = bool(op is not None and getattr(op, "big_supported", False))
        supports_bigcx = bool(op is not None and getattr(op, "bigcomplex_supported", False))

        has_rational = any(isinstance(a, NativeRational) for a in args)
        has_complex = any(isinstance(a, complex) for a in args)
        has_big = any(isinstance(a, NativeBigReal) for a in args)
        has_big_complex = any(isinstance(a, NativeBigComplex) for a in args)

        # BigComplex > Complex > BigReal > Rational
        if supports_bigcx and (has_big_complex or (has_big and has_complex)):
            return tuple(self._to_big_complex(a) for a in args)

        if has_complex:
            return tuple(self._to_complex(a) for a in args)

        if has_big:
            if supports_big:
                return tuple(self._to_big(a) if self._is_num_or_big(a) else a for a in args)
            return tuple(a for a in args)

        # Rational is the default numeric type.
        # Coerce all args to Rational when possible, otherwise downcast to float.
        if has_rational:
            coerced = []
            for a in args:
                r = _to_rational(a)
                if r is None:
                    return _rational_downcast(args)
                coerced.append(r)
            return tuple(coerced)

        return args

    def _is_num_or_big(self, value: object) -> bool:
        return isinstance(value, (int, float, NativeBigReal, NativeRational))

    def negate(self, a):
        if isinstance(a, NativeRational):
            return -a
        return self.sub(0, a)

    def unaryplus(self, a):
        return a

    def percent(self, a):
        return self.div(a, 100)

    def sqr(self, a):
        return self.pow(a, 2)

    def cube(self, a):
        return self.pow(a, 3)

    def recip(self, a):
        return self.pow(a, -1)

    def pow10(self, a):
        return self.pow(10, a)

    def exp(self, a):
        return self.pow(E, a)

    def _promote_complex(self, name: str, args: tuple[object, ...]) -> tuple[object, ...]:
        # Only attempt complex domain-promotion for float/int inputs.
        # BigReal values can be far outside float range; converting them to float
        # for domain checks can underflow to 0.0 and incorrectly force complex ops.
        # Rational inputs are handled via float fallback when the op raises TypeError.
        if (
            len(args) < 1
            or not isinstance(args[0], (int, float))
            or any(isinstance(a, NativeBigReal) for a in args)
        ):
            return args
        try:
            op = Operation(name)
        except ValueError:
            return args

        rule = op.cx
        if rule is None:
            return args

        x = float(args[0])
        if op._spec.arity == calc_native.OpArity.Binary and len(args) >= 2:
            y = float(args[1])  # type: ignore[arg-type]
            needs_complex = rule(x, y)
        else:
            needs_complex = rule(x)

        if not needs_complex:
            return args

        return (complex(x, 0.0),) + args[1:]

    def __getattr__(self, name: str):
        try:
            attr = getattr(self._native, name)
        except AttributeError as exc:
            raise_error(ErrorKind.INVALID, exc)

        if not callable(attr):
            return attr

        def _float_fallback(original_args, kwargs):
            float_args = _rational_downcast(original_args)
            float_args = self._promote_complex(name, float_args)
            float_args = self._coerce_args(name, float_args)
            try:
                return attr(*float_args, **kwargs)
            except (TypeError, NativeCalculatorError) as exc:
                raise_error(ErrorKind.MATH_ERR, exc)

        def wrapper(*args, **kwargs):
            original_args = args
            args = self._promote_complex(name, args)
            args = self._coerce_args(name, args)
            try:
                return attr(*args, **kwargs)
            except (TypeError, NativeCalculatorError) as exc:
                if any(isinstance(a, NativeRational) for a in original_args):
                    return _float_fallback(original_args, kwargs)
                raise_error(ErrorKind.MATH_ERR, exc)

        return wrapper
