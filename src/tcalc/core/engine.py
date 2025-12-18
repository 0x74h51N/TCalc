from __future__ import annotations

from calc_native import Calculator as NativeCalculator
from calc_native import CalculatorError as NativeCalculatorError

try:
    from calc_native import BigReal as NativeBigReal
except ImportError:  # pragma: no cover
    import logging

    logging.getLogger(__name__).exception(
        "Failed to import calc_native.BigReal; native module is required."
    )
    raise

from tcalc.app_state import CalculatorMode, get_app_state

from .constants import E
from .ops import Operation


class CalculatorError(Exception):
    """Exception raised for calculator operation errors."""

    pass


class Calculator:
    """Python wrapper for the native C++ calculator engine."""

    def __init__(self) -> None:
        self._native = NativeCalculator()

    def _complex_allowed(self) -> bool:
        return get_app_state().mode == CalculatorMode.SCIENCE

    def _is_big(self, v: object) -> bool:
        return isinstance(v, NativeBigReal)

    def _to_big(self, v: object):
        if isinstance(v, NativeBigReal):
            return v
        if isinstance(v, int):
            return NativeBigReal(str(v))
        if isinstance(v, float):
            return NativeBigReal(repr(v))
        return NativeBigReal(str(v))

    def _big_to_float(self, v: object) -> float:
        return float(str(v))

    def _coerce_args(self, name: str, args: tuple[object, ...]) -> tuple[object, ...]:
        # Complex has top priority (native complex ops are double-based)
        if any(isinstance(a, complex) for a in args):
            coerced_complex: list[object] = []
            for a in args:
                if isinstance(a, complex):
                    coerced_complex.append(a)
                elif self._is_big(a):
                    coerced_complex.append(complex(self._big_to_float(a), 0.0))
                elif isinstance(a, (int, float)):
                    coerced_complex.append(complex(float(a), 0.0))
                else:
                    coerced_complex.append(a)
            return tuple(coerced_complex)

        try:
            op = Operation(name)
        except ValueError:
            op = None
        supports_big = bool(op is not None and getattr(op, "big_supported", False))

        # Auto-promote pow to BigReal for large real exponents (e.g. 10^1232)
        if (
            name == Operation.POW.value
            and len(args) >= 2
            and not self._is_big(args[0])
            and not self._is_big(args[1])
            and isinstance(args[1], (int, float))
            and abs(float(args[1])) >= 309.0
        ):
            return (self._to_big(args[0]), self._to_big(args[1]), *args[2:])

        # If any operand is BigReal, keep in BigReal for supported ops; otherwise downcast.
        if any(self._is_big(a) for a in args):
            if supports_big:
                coerced_big: list[object] = []
                for a in args:
                    if isinstance(a, (int, float)) or self._is_big(a):
                        coerced_big.append(self._to_big(a))
                    else:
                        coerced_big.append(a)
                return tuple(coerced_big)
            coerced_downcast: list[object] = []
            for a in args:
                if self._is_big(a):
                    coerced_downcast.append(self._big_to_float(a))
                else:
                    coerced_downcast.append(a)
            return tuple(coerced_downcast)

        return args

    # helpers
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

    def __getattr__(self, name: str):
        try:
            attr = getattr(self._native, name)
        except AttributeError as e:
            raise AttributeError(f"Calculator has no attribute '{name}'") from e

        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            allowed = self._complex_allowed()

            if not allowed:
                if name == Operation.POLAR.value:
                    raise CalculatorError("Math error")
                if any(isinstance(a, complex) for a in args) or any(
                    isinstance(v, complex) for v in kwargs.values()
                ):
                    raise CalculatorError("Math error")

            if allowed and len(args) >= 1 and isinstance(args[0], (int, float, NativeBigReal)):
                try:
                    op = Operation(name)
                except ValueError:
                    op = None
                rule = None if op is None else op.spec.cx
                if rule is not None:
                    x = (
                        float(args[0])
                        if isinstance(args[0], (int, float))
                        else self._big_to_float(args[0])
                    )

                    if name == Operation.ROOT.value and len(args) >= 2:
                        y = (
                            float(args[1])
                            if not self._is_big(args[1])
                            else self._big_to_float(args[1])
                        )
                        needs_complex = rule(x, y)
                    else:
                        needs_complex = rule(x)

                    if needs_complex:
                        if name == Operation.ROOT.value and len(args) >= 2:
                            args = (complex(x, 0.0), complex(float(args[1]), 0.0)) + args[2:]
                        else:
                            args = (complex(x, 0.0),) + args[1:]

            args = self._coerce_args(name, args)

            try:
                return attr(*args, **kwargs)
            except TypeError as exc:
                raise CalculatorError("Math error") from exc
            except NativeCalculatorError as exc:
                raise CalculatorError(str(exc)) from exc

        return wrapper
