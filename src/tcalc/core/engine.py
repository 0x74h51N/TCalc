from __future__ import annotations

from calc_native import Calculator as NativeCalculator, CalculatorError as NativeCalculatorError

from ..app_state import get_app_state, CalculatorMode


class CalculatorError(Exception):
    """Exception raised for calculator operation errors."""
    pass


class Calculator:
    """Python wrapper for the native C++ calculator engine."""
    
    def __init__(self) -> None:
        self._native = NativeCalculator()

    def _complex_allowed(self) -> bool:
        return get_app_state().mode == CalculatorMode.SCIENCE

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
                if any(isinstance(a, complex) for a in args) or any(isinstance(v, complex) for v in kwargs.values()):
                    raise CalculatorError("Math error")

            if allowed and name == "sqrt":
                if len(args) >= 1:
                    x = args[0]
                    if isinstance(x, (int, float)) and x < 0:
                        args = (complex(float(x), 0.0),) + args[1:]

            try:
                return attr(*args, **kwargs)
            except NativeCalculatorError as exc:
                raise CalculatorError(str(exc)) from exc

        return wrapper
