from __future__ import annotations

from calc_native import Calculator as NativeCalculator, CalculatorError as NativeCalculatorError


class CalculatorError(Exception):
    pass


class Calculator:
    def __init__(self) -> None:
        self._native = NativeCalculator()

    def __getattr__(self, name: str):
        try:
            attr = getattr(self._native, name)
            if callable(attr):
                def wrapper(*args, **kwargs):
                    try:
                        result = attr(*args, **kwargs)
                        return result
                    except NativeCalculatorError as exc:
                        raise CalculatorError(str(exc)) from exc
                return wrapper
            return attr
        except AttributeError as e:
            print(f"[ENGINE] AttributeError: {e}")
            raise AttributeError(f"Calculator has no attribute '{name}'")

