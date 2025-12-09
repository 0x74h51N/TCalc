from __future__ import annotations

from calc_native import Calculator as NativeCalculator, CalculatorError as NativeCalculatorError


class CalculatorError(Exception):
    """Python-side alias so callers don't depend on calc_native directly."""

    pass


class Calculator:
    """Thin facade over the native Calculator implementation."""

    def __init__(self) -> None:
        self._native = NativeCalculator()

    def add(self, a: float, b: float) -> float:
        return self._native.add(a, b)

    def sub(self, a: float, b: float) -> float:
        return self._native.sub(a, b)

    def mul(self, a: float, b: float) -> float:
        return self._native.mul(a, b)

    def div(self, a: float, b: float) -> float:
        try:
            return self._native.div(a, b)
        except NativeCalculatorError as exc:
            raise CalculatorError(str(exc)) from exc


