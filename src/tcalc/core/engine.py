from __future__ import annotations

from calc_native import Calculator as NativeCalculator
from calc_native import CalculatorError as NativeCalculatorError


try:
    from calc_native import BigComplex as NativeBigComplex
    from calc_native import BigReal as NativeBigReal
except ImportError:  # pragma: no cover
    import logging

    logging.getLogger(__name__).exception(
        "Failed to import calc_native.BigReal; native module is required."
    )
    raise

from .constants import E
from .errors import ErrorKind, raise_error
from .ops import Operation


class Calculator:
    """Python wrapper for the native C++ calculator engine."""

    def __init__(self) -> None:
        self._native = NativeCalculator()

    def _to_big(self, v: object):
        if isinstance(v, NativeBigReal):
            return v
        return NativeBigReal(repr(v))

    def _to_big_complex(self, v: object):
        if isinstance(v, NativeBigComplex):
            return v
        if not isinstance(v, (complex, NativeBigReal, int, float)):
            return v
        if isinstance(v, complex):
            return NativeBigComplex(repr(v.real), repr(v.imag))
        return NativeBigComplex(repr(v))

    def _to_complex(self, value: object) -> object:
        if isinstance(value, complex):
            return value
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

        has_complex = any(isinstance(a, complex) for a in args)
        has_big = any(isinstance(a, NativeBigReal) for a in args)
        has_big_complex = any(isinstance(a, NativeBigComplex) for a in args)

        if (
            name == Operation.POW.value
            and len(args) >= 2
            and not has_big_complex
            and isinstance(args[1], (int, float))
            and abs(float(args[1])) >= 309.0
        ):
            return self._pow_big_prom(args, has_complex, supports_bigcx)

        if supports_bigcx and (has_big_complex or (has_big and has_complex)):
            return tuple(self._to_big_complex(a) for a in args)

        if has_complex:
            return tuple(self._to_complex(a) for a in args)

        # If any operand is BigReal, keep in BigReal for supported ops; otherwise downcast.
        if has_big:
            if supports_big:
                return tuple(self._to_big(a) if self._is_num_or_big(a) else a for a in args)

            return tuple(a for a in args)

        return args

    def _is_num_or_big(self, value: object) -> bool:
        return isinstance(value, (int, float, NativeBigReal))

    def _pow_big_prom(
        self, args: tuple[object, ...], has_complex: bool, supports_bigcx: bool
    ) -> tuple[object, ...]:
        if has_complex and supports_bigcx:
            return tuple(self._to_big_complex(a) for a in args)
        return tuple(self._to_big(a) for a in args)

    def negate(self, a):
        return self.sub(0, a)

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
        rule = op.spec.cx

        if rule is None:
            return args

        x = float(args[0])
        if len(args) >= 2:
            y = float(args[1])
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

        def wrapper(*args, **kwargs):
            args = self._promote_complex(name, args)
            args = self._coerce_args(name, args)

            try:
                return attr(*args, **kwargs)
            except TypeError as exc:
                raise_error(ErrorKind.MATH_ERR, exc)
            except NativeCalculatorError as exc:
                raise_error(ErrorKind.MATH_ERR, exc)

        return wrapper
