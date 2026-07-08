#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import math
import os
from decimal import Decimal

import pytest

pytest.importorskip("calc_native")
import calc_native

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "*=false")

param = pytest.param

_editor = None

# raw -> canonical round-trips for the current test; conftest dumps this only when
# the test fails, so a failing eval shows exactly where the round-trip landed.
CANON_LOG: list[tuple[str, str]] = []


def _canonicalize(expr: str) -> str:
    """Mirror the running app: raw text -> editor widgets (build_math_nodes folds
    trailing operands into empty script slots) -> get_plain_text() canonical form.
    The controller evaluates this canonical text, not the raw tokenize output, so
    `3^4` becomes `3^{4}` before eval."""
    global _editor
    from PySide6.QtWidgets import QApplication

    from tcalc.ui.widgets.calc.display.expression.expression import Expression

    # Subscript has no editor widget yet (a later UI phase); its `_{…}` form already
    # tokenizes to its final LatexToken, so eval it raw instead of round-tripping it
    # through a renderer that would drop it.
    if "_{" in expr:
        CANON_LOG.append((expr, expr))
        return expr

    app = QApplication.instance() or QApplication([])
    if _editor is None:
        _editor = Expression()
    _editor.set_plain_text(expr)
    app.processEvents()
    canonical = _editor.get_plain_text()
    CANON_LOG.append((expr, canonical))
    return canonical


def _eval(expr: str) -> object:
    from tcalc.core.engine import Calculator
    from tcalc.core.parser import evaluate_tokens, tokenize_string

    calc = Calculator()
    return evaluate_tokens(tokenize_string(_canonicalize(expr)), calc)


@pytest.mark.parametrize(
    ("expr", "expected_type", "expected_value"),
    [
        # ----------------------------
        # precedence / associativity
        # ----------------------------
        param("1+2*3", "float", 7.0, id="precedence-mul-over-add"),
        param("(1+2)*3", "float", 9.0, id="paren-overrides-precedence"),
        param("2^{3^{2}}", "float", 512.0, id="pow-right-assoc"),
        param("(2^3)^2", "float", 64.0, id="pow-parens-left-group"),
        param("-2^2", "float", -4.0, id="unary-vs-pow"),
        param("(-2)^2", "float", 4.0, id="pow-negative-base"),
        param("1/2/3", "float", (1.0 / 2.0) / 3.0, id="left-assoc-division-chain"),
        param("1/(2/3)", "float", 1.5, id="paren-changes-division-assoc"),
        # ----------------------------
        # unary / sign folding (edge, not repeats)
        # ----------------------------
        param("-(2+3)", "float", -5.0, id="unary-negate"),
        param("1+--+2", "float", 3.0, id="mixed-sign-collapse-plus"),
        param("1+-+--+--++--+2", "float", -1.0, id="insane-sign-collapse"),
        # ----------------------------
        # nesting + stack discipline
        # ----------------------------
        param("(1+(2*(3+(4*5))))", "float", 47.0, id="deep-nesting"),
        param("1/(2+3*4)", "float", 1.0 / 14.0, id="div-with-precedence"),
        # ----------------------------
        # implicit multiplication
        # ----------------------------
        param("10e + 0", "float", 27.18281828459045, id="implicit-mul-constant"),
        param(
            "1e1610e + 0", "BigReal", "2.718281828459045e+1610", id="implicit-mul-constant-bigreal"
        ),
        param("(1e-3 + 2e-3) * 1000", "float", 3.0, id="scientific-notation-flow"),
        param("2π", "float", 2.0 * math.pi, id="pi-symbol-implicit-mul"),
        param("π*10^309", "BigReal", "3.141592653589793e+309", id="pi-symbol-promotes-bigreal"),
        # ----------------------------
        # named constants (constant table)
        # ----------------------------
        param("pi", "float", math.pi, id="const-pi"),
        param("π", "float", math.pi, id="const-pi-symbol"),
        param("e", "float", math.e, id="const-e"),
        param("φ", "float", 1.618033988749895, id="const-phi"),
        param("τ", "float", 2.0 * math.pi, id="const-tau"),
        param("i", "complex", (0.0, 1.0), id="const-imaginary-unit"),
        # constants inside normal operations
        param("pi+e", "float", math.pi + math.e, id="const-sum"),
        param("i^2", "complex", (-1.0, 0.0), id="const-i-squared"),
        param("2τ", "float", 4.0 * math.pi, id="const-tau-implicit-mul"),
        param("c", "float", 299792458.0, id="const-c"),
        param("ℏ", "float", 6.62607015e-34 / (2 * math.pi), id="const-hbar"),
        param("2c", "float", 2 * 299792458.0, id="const-c-implicit-mul"),
        param("2(3+4)", "float", 14.0, id="implicit-mul-paren"),
        param("2sqrt(9)", "float", 6.0, id="implicit-mul-func"),
        param("(1+1)(1+2)", "float", 6.0, id="implicit-mul-paren-paren"),
        param("2(-3+4)", "float", 2.0, id="implicit-mul-paren-with-unary"),
        # ----------------------------
        # postfix percent
        # ----------------------------
        param("50%", "float", 0.5, id="postfix-percent"),
        param("200*3%", "float", 6.0, id="percent-postfix-after-mul"),
        param("50%+50%", "float", 1.0, id="percent-sum"),
        param("(1+1)%*200", "float", 4.0, id="percent-after-paren-then-mul"),
        param("3%*200", "float", 6.0, id="percent-then-mul"),
        # ----------------------------
        # function domain -> complex promotion
        # ----------------------------
        param("sqrt(4)", "float", 2.0, id="sqrt-positive"),
        param("sqrt(-1)", "complex", (0.0, 1.0), id="sqrt-domain-promotes-complex"),
        param("sqrt(-1)^2", "complex", (-1.0, 0.0), id="complex-pow-collapses-to-real"),
        param("sqrt(-1)*sqrt(-1)", "complex", (-1.0, 0.0), id="complex-mul-collapses-to-real"),
        param("log(-1)", "complex", (0.0, 1.364376353841841), id="log-domain-promotes-complex"),
        param("ln(-1)", "complex", (0.0, math.pi), id="ln-domain-promotes-complex"),
        # ----------------------------
        # root operator domain behavior
        # ----------------------------
        param("(-4) ⌄ 2", "complex", (0.0, 2.0), id="root-domain-complex"),
        param("-4 ⌄ 2", "float", -2.0, id="root-noncomplex-with-leading-minus"),
        param("sqrt(-1)*sqrt(-4)", "complex", (-2.0, 0.0), id="complex-mul-imaginary-units"),
        param(
            "log(-1) + log(-2)",
            "complex",
            (0.3010299956639812, 2.728752707683683),
            id="complex-add-two-domains",
        ),
        param("sqrt(-1) / sqrt(-4)", "complex", (0.5, 0.0), id="complex-div-imaginary-units"),
        param("(sqrt(-1))^2", "complex", (-1.0, 0.0), id="imaginary-unit-squared"),
        param("sqrt(-1)^4", "complex", (1.0, 0.0), id="imaginary-unit-fourth-power"),
        param("ln(-e)", "complex", (1.0, math.pi), id="ln-negative-e-exact"),
        param("sqrt(-2)*sqrt(-2)", "complex", (-2.0, 0.0), id="complex-mul-same-base"),
        # ----------------------------
        # BigReal promotion + non-overflow path
        # ----------------------------
        param("2^309", "float", 2.0**309, id="pow-large-exp-stays-float"),
        param("10^308", "BigReal", "e+308", id="pow-ten-308-promotes"),
        param(
            "1.7976931348623157e308^2",
            "BigReal",
            "e+616",
            id="pow-dblmax-squared-promotes-bigreal",
        ),
        param("14^308", "BigReal", "e+353", id="pow-overflow-promotes-bigreal"),
        param("10^(-400)", "BigReal", "e-400", id="pow-underflow-promotes-bigreal"),
        param("10^309", "BigReal", "e+309", id="pow-promotes-bigreal"),
        param("sqrt(10^309)", "BigReal", "e+154", id="bigreal-sqrt-does-not-overflow"),
        param("(10^307)/(10^306)", "float", 10.0, id="float-div-keeps-float"),
        param("(10^309)/(10^308)", "BigReal", "10", id="bigreal-div-keeps-bigreal"),
        param("1e16!", "BigReal", "e+155657055180967490", id="factorial-bigreal-huge"),
        param("1e17!", "BigReal", "inf", id="factorial-overflows-to-inf"),
        param("10^309 + e", "BigReal", "e+309", id="bigreal-promotes-e"),
        # ----------------------------
        # BigReal + complex -> BigComplex promotion
        # ----------------------------
        param(
            "10^309 + sqrt(-1)",
            "BigComplex",
            "e+309",
            id="bigreal-plus-complex-promotes-bigcomplex",
        ),
        param(
            "sqrt(-1) + 10^309",
            "BigComplex",
            "e+309",
            id="complex-plus-bigreal-promotes-bigcomplex",
        ),
        # ----------------------------
        # Collection literals (List / Point)
        # ----------------------------
        param("[1, 2, 3]", "List", [1, 2, 3], id="list-bare-numbers"),
        param("[]", "List", [], id="list-empty"),
        param("(3, 4)", "Point", (3, 4), id="point-arity-2"),
        param("(1, 2, 3)", "Point", (1, 2, 3), id="point-arity-3"),
        param("[\\frac{1}{2}, 3]", "List", [0.5, 3.0], id="list-with-latex-element"),
        param("[1+2, 3*4]", "List", [3, 12], id="list-with-expression-element"),
        param("[1,2,3", "List", [1, 2, 3], id="list-unclosed"),
        param("[(1,2)]", "List", [(1, 2)], id="list-singleton-point-wrapped"),
        param("[(1,2),(3,4)]", "List", [(1, 2), (3, 4)], id="list-of-points"),
        # arity-1 "(...)" is transparent grouping: "(x)" == "x" for collections too.
        param("([1, 2])", "List", [1, 2], id="paren-groups-list"),
        param("((1, 2))", "Point", (1, 2), id="paren-groups-point"),
        # ----------------------------
        # Variable assignment returns value (single-expr, integer result)
        # ----------------------------
        param("A = 5", "float", 5.0, id="assign-integer-returns-value"),
        param("ᵉ", "float", 1.602176634e-19, id="const-elementary-charge"),
        param("mₑ", "float", 9.1093837139e-31, id="const-electron-mass"),
        param("k", "float", 1.380649e-23, id="const-boltzmann"),
        param("R", "float", 8.314462618, id="const-gas"),
        param("Nₐ", "float", 6.02214076e23, id="const-avogadro"),
        param("F", "float", 96485.33212, id="const-faraday"),
        # ----------------------------
        # Collection arity-1 demote (scalar canonicalization)
        # ----------------------------
        param("[5]", "float", 5.0, id="list-arity-1-demote-scalar"),
        param("[2+3]", "float", 5.0, id="list-arity-1-demote-expression"),
        param("(2+3", "float", 5.0, id="paren-unclosed-grouping"),
        param("{2+3", "float", 5.0, id="brace-unclosed-grouping"),
        param("1+2)", "float", 3.0, id="stray-close-skipped"),
        param("[[5]]", "float", 5.0, id="nested-list-arity-1-demote-chain"),
    ],
)
def test_native_eval_golden(expr: str, expected_type: str, expected_value: object) -> None:
    if expected_type == "float":
        out = _eval(expr)
        if isinstance(out, calc_native.Rational):
            assert float(out.to_double()) == pytest.approx(expected_value)
        else:
            assert isinstance(out, (int, float))
            assert float(out) == pytest.approx(expected_value)
        return

    if expected_type == "complex":
        out = _eval(expr)
        assert isinstance(out, complex)
        assert isinstance(expected_value, tuple)
        real, imag = out.real, out.imag
        exp_real, exp_imag = expected_value
        assert real == pytest.approx(exp_real)
        assert imag == pytest.approx(exp_imag)
        return

    if expected_type in ("List", "Point"):
        assert isinstance(expected_value, (list, tuple))
        out = _eval(expr)
        assert isinstance(out, calc_native.Collection)
        kind = (
            calc_native.Collection.Kind.List
            if expected_type == "List"
            else calc_native.Collection.Kind.Point
        )
        assert out.kind == kind
        assert len(out) == len(expected_value)
        for actual, expected in zip(out, expected_value):
            if isinstance(expected, tuple):
                # Nested Point item inside a List of Points.
                assert isinstance(actual, calc_native.Collection)
                assert actual.kind == calc_native.Collection.Kind.Point
                assert list(actual) == list(expected)
            else:
                assert actual == expected
        return

    out = _eval(expr)
    assert type(out).__name__ == expected_type
    assert isinstance(expected_value, str)
    assert expected_value in str(out)


@pytest.mark.parametrize(
    ("expr", "expected_msg_substr"),
    [
        param("()", None, id="empty-point"),
        param("(1, 2, 3, 4)", None, id="point-arity-too-many"),
        param("[1, ]", None, id="empty-element-in-list"),
        param("[[1,2], 3]", "List of List", id="nested-list-in-list-arity2"),
        param("[[1,2]]", "List of List", id="singleton-list-in-list"),
        param("[[1,2],[3,4]]", "List of List", id="list-of-lists-multi"),
        param("[(1,2), (3,4,5)]", None, id="list-of-points-mixed-arity"),
        param("[1, (2,3)]", "mix scalars and points", id="list-mixed-scalar-then-point"),
        param("[(1,2), 3]", "mix scalars and points", id="list-mixed-point-then-scalar"),
        param("5 + [1, 2]", None, id="scalar-plus-collection-undefined"),
        param("((1,2),(3,4))", "Point item cannot be a collection", id="point-of-points-multi"),
        param("(1, [2,3])", "Point item cannot be a collection", id="point-with-list-item"),
        # ----------------------------
        # Variable assignment errors
        # ----------------------------
        param("2 = 5", None, id="assign-non-variable-lhs"),
        param("e = 1", None, id="assign-reserved-name"),
        param("mean(B)", None, id="undefined-variable-reference"),
    ],
)
def test_collection_eval_errors(expr: str, expected_msg_substr: str | None) -> None:
    from tcalc.errors import Error

    with pytest.raises(Error) as exc_info:
        _eval(expr)
    if expected_msg_substr is not None:
        assert expected_msg_substr in str(exc_info.value)


def test_pow_boundary_exactness() -> None:
    out = _eval("(10^308*10)/(10^309)")
    assert isinstance(out, calc_native.BigReal)
    assert Decimal(str(out)) == Decimal(1)


# ============================================================================
# Rational arithmetic edge cases
# ============================================================================


class TestRational:
    """Rational arithmetic: exact results, downcast, promotion, errors, no-crash."""

    # -- Exact Rational results (num/den check) --
    @pytest.mark.parametrize(
        ("expr", "num", "den"),
        [
            # basic four ops
            param("1+2", 3, 1, id="add-integers"),
            param("7-3", 4, 1, id="sub-integers"),
            param("3*4", 12, 1, id="mul-integers"),
            param("10/3", 10, 3, id="div-integers-non-trivial"),
            param("1/3 + 2/3", 1, 1, id="frac-add-to-one"),
            param("1/2 + 1/3", 5, 6, id="frac-add-diff-denom"),
            param("3/4 - 1/4", 1, 2, id="frac-sub-same-denom"),
            param("2/3 * 3/4", 1, 2, id="frac-mul-cancels"),
            param("(2/3) / (4/5)", 5, 6, id="frac-div-frac"),
            # unary / negate
            param("-5", -5, 1, id="negate-int"),
            param("-(1/3)", -1, 3, id="negate-frac"),
            param("--5", 5, 1, id="double-negate"),
            # percent
            param("50%", 1, 2, id="percent-half"),
            param("200*50%", 100, 1, id="percent-mul"),
            param("1%", 1, 100, id="percent-one"),
            param("1/3 + 0.5", 5, 6, id="frac-plus-decimal-half"),
            param("0.25 + 0.75", 1, 1, id="decimal-quarter-sum"),
            param("0.1 + 0.2", 3, 10, id="decimal-point-one-plus-point-two"),
            param("6/4", 3, 2, id="auto-normalization"),
            param("(-6)/4", -3, 2, id="negative-result-normalization"),
            # identities
            param("(7/11) * 1", 7, 11, id="mul-identity"),
            param("(7/11) + 0", 7, 11, id="add-identity"),
            param("(3/7) - (3/7)", 0, 1, id="subtract-self-zero"),
            param("(3/7) * (7/3)", 1, 1, id="mul-reciprocal-one"),
            param("(-3) * (-4)", 12, 1, id="neg-times-neg"),
            param("0 + 0", 0, 1, id="zero-rational"),
            param("1/2/3/4/5/6/7", 1, 5040, id="chained-division"),
            # pow
            param("2^3", 8, 1, id="pow-int-cubed"),
            param("3^4", 81, 1, id="pow-int-fourth"),
            param("(1/2)^3", 1, 8, id="pow-frac-cubed"),
            param("(2/3)^2", 4, 9, id="pow-frac-squared"),
            param("(3/5)^3", 27, 125, id="pow-frac-cubed-general"),
            param("5^0", 1, 1, id="pow-any-to-zero"),
            param("(7/11)^0", 1, 1, id="pow-frac-to-zero"),
            param("(7/11)^1", 7, 11, id="pow-frac-to-one"),
            param("(-2)^2", 4, 1, id="pow-neg-base-even"),
            param("(-2)^3", -8, 1, id="pow-neg-base-odd"),
            param("(-1/2)^4", 1, 16, id="pow-neg-frac-even"),
            param("(-1/2)^3", -1, 8, id="pow-neg-frac-odd"),
            param("1^100", 1, 1, id="pow-one-to-large"),
            param("(-1)^99", -1, 1, id="pow-neg-one-odd"),
            param("(-1)^100", 1, 1, id="pow-neg-one-even"),
            param("2^(-1)", 1, 2, id="pow-int-neg-one"),
            param("2^(-3)", 1, 8, id="pow-int-neg-three"),
            param("(2/3)^(-1)", 3, 2, id="pow-frac-reciprocal"),
            param("(2/3)^(-2)", 9, 4, id="pow-frac-neg-two"),
            param("(3/4)^(-3)", 64, 27, id="pow-frac-neg-three"),
            param("(-2)^(-1)", -1, 2, id="pow-neg-base-neg-exp"),
            param("(-2)^(-2)", 1, 4, id="pow-neg-base-neg-even"),
            param("2^61", 2**61, 1, id="pow-i64-boundary-fits"),
            param("(1/2)^(-61)", 2**61, 1, id="pow-neg-exp-i64-boundary-fits"),
            param("(1/4)^(1/2)", 1, 2, id="pow-frac-exp-exact-half"),
            param("8^(1/3)", 2, 1, id="pow-frac-exp-cbrt8"),
            param("27^(2/3)", 9, 1, id="pow-frac-exp-27-2-3"),
            param("4^(1/2)", 2, 1, id="pow-frac-exp-sqrt4"),
            param("9^(1/2)", 3, 1, id="pow-frac-exp-sqrt9"),
            param("16^(1/4)", 2, 1, id="pow-frac-exp-fourth-root"),
            param("4^(3/2)", 8, 1, id="pow-frac-exp-4-3-2"),
            param("(-8)^(1/3)", -2, 1, id="pow-neg-base-cube-root"),
            param("2^{2^{2^{2}}}", 65536, 1, id="pow-chain-2-2-2-2"),
            param("(2^3) + (3^2)", 17, 1, id="pow-then-add"),
            param("(1/2)^2 * 8", 2, 1, id="pow-then-mul"),
            # ----------------------------
            # Variable assignment returns value (single-expression)
            # ----------------------------
            param("A = 1/2", 1, 2, id="assign-fraction-returns-value"),
            param("A = 2/3 * 3/4", 1, 2, id="assign-expr-result-rational"),
        ],
    )
    def test_stays_rational(self, expr: str, num: int, den: int) -> None:
        out = _eval(expr)
        assert isinstance(out, calc_native.Rational), (
            f"Expected Rational, got {type(out).__name__}: {out}"
        )
        assert out.numerator == num, f"numerator: expected {num}, got {out.numerator}"
        assert out.denominator == den, f"denominator: expected {den}, got {out.denominator}"

    # -- Downcast to float --
    @pytest.mark.parametrize(
        ("expr", "expected_approx"),
        [
            # irrational functions
            param("sqrt(2)", 1.4142135623730951, id="sqrt-irrational"),
            param("sqrt(3)", 1.7320508075688772, id="sqrt-three"),
            param("ln(2)", 0.6931471805599453, id="ln-drops-rational"),
            param("log(10)", 1.0, id="log10-drops-rational"),
            param("sin(1)", None, id="sin-drops-rational"),
            param("cos(1)", None, id="cos-drops-rational"),
            param("tan(1)", None, id="tan-drops-rational"),
            param("exp(1)", 2.718281828459045, id="exp-drops-rational"),
            param("exp(0)", 1.0, id="exp-zero"),
            # fractional exponent => irrational result
            param("2^(1/2)", 1.4142135623730951, id="pow-frac-exp-sqrt2"),
            param("3^(1/3)", 1.4422495703074083, id="pow-frac-exp-cbrt3"),
            # factorial
            param("5!", 120.0, id="factorial-drops-rational"),
            param("0!", 1.0, id="factorial-zero"),
            param("3^40", 3.0**40, id="pow-i64-overflow"),
            param("2^62", 2.0**62, id="pow-i64-boundary-overflows"),
            param("(1/2)^(-62)", 2.0**62, id="pow-neg-exp-i64-boundary-overflows"),
            param("(3/2)^100", (3 / 2) ** 100, id="pow-frac-overflow"),
        ],
    )
    def test_downcasts_to_float(self, expr: str, expected_approx: float | None) -> None:
        out = _eval(expr)
        assert isinstance(out, (int, float)), f"Expected float, got {type(out).__name__}: {out}"
        if expected_approx is not None:
            assert float(out) == pytest.approx(expected_approx)

    # -- Promote to complex --
    @pytest.mark.parametrize(
        ("expr", "exp_real", "exp_imag"),
        [
            param("sqrt(-1)", 0.0, 1.0, id="sqrt-neg-to-complex"),
            param("sqrt(-4)", 0.0, 2.0, id="sqrt-neg4-to-complex"),
            param("ln(-1)", 0.0, math.pi, id="ln-neg-to-complex"),
            param("log(-1)", 0.0, 1.364376353841841, id="log-neg-to-complex"),
        ],
    )
    def test_promotes_to_complex(self, expr: str, exp_real: float, exp_imag: float) -> None:
        out = _eval(expr)
        assert isinstance(out, complex), f"Expected complex, got {type(out).__name__}: {out}"
        assert out.real == pytest.approx(exp_real)
        assert out.imag == pytest.approx(exp_imag)

    # -- Promote to BigReal --
    @pytest.mark.parametrize(
        "expr",
        [
            param("1/3 + 10^309", id="rational-plus-bigreal"),
            param("10^309 - 1", id="bigreal-minus-rational"),
            param("2 * 10^309", id="rational-times-bigreal"),
            param("2^1024", id="pow-2-1024"),
            param("10^400", id="pow-10-400"),
            param("3^700", id="pow-3-700"),
        ],
    )
    def test_promotes_to_bigreal(self, expr: str) -> None:
        out = _eval(expr)
        assert isinstance(out, calc_native.BigReal), (
            f"Expected BigReal, got {type(out).__name__}: {out}"
        )

    # -- Math errors --
    @pytest.mark.parametrize(
        "expr",
        [
            param("1/0", id="div-by-zero"),
            param("0/0", id="zero-div-zero"),
            param("(1/3)/0", id="frac-div-by-zero"),
            param("0^(-1)", id="zero-to-neg-power"),
            param("0^(-2)", id="zero-to-neg-even-power"),
            param("0^(-3)", id="zero-frac-neg-odd"),
            param("(0/1)^(-2)", id="zero-frac-neg-exp"),
        ],
    )
    def test_raises_math_error(self, expr: str) -> None:
        from tcalc.errors import Error

        with pytest.raises(Error, match="Math Error"):
            _eval(expr)

    # -- No-crash stress --
    @pytest.mark.parametrize(
        "expr",
        [
            param("2^63", id="pow-i64-overflow"),
            param("2^100", id="pow-huge-overflow"),
            param("(2^31) * (2^31)", id="large-numerator-mul"),
            param("1/(1+1/(1+1/(1+1/(1+1/2))))", id="deeply-nested-fraction"),
            param("2^20^20^20", id="pow-chain-huge"),
            param("2^(-200)", id="pow-large-neg-exp"),
            param("(1/2)^200", id="pow-frac-base-large-exp"),
        ],
    )
    def test_no_crash(self, expr: str) -> None:
        from tcalc.errors import Error

        try:
            out = _eval(expr)
        except Error:
            return
        assert isinstance(out, (int, float, complex, calc_native.BigReal, calc_native.Rational))


# ============================================================================
# Stateful multi-line variable tests (shared env across lines)
# ============================================================================


def _to_int(v) -> int:
    if isinstance(v, calc_native.Rational):
        assert v.denominator == 1, f"expected integer Rational, got {v}"
        return v.numerator
    return int(v)


def _ev_multi(lines, *, assert_env_key=None):
    from tcalc.core.engine import Calculator
    from tcalc.core.parser import evaluate_tokens, tokenize_string
    from tcalc.core.varstore import VarStore

    calc, env = Calculator(), VarStore()
    result = None
    for line in lines:
        result = evaluate_tokens(tokenize_string(_canonicalize(line)), calc, env)
    if assert_env_key is not None:
        return env.get(assert_env_key)
    return result


@pytest.mark.parametrize(
    ("lines", "assert_env_key", "check"),
    [
        param(
            ["A = [1, 2, 4, 5]", "mean(A)"],
            None,
            lambda v: v == 3.0,
            id="cross-line-collection-mean",
        ),
        param(
            ["a = 2", "b = 3", "ab"],
            None,
            lambda v: _to_int(v) == 6,
            id="implicit-mul-ab",
        ),
        param(
            ["a = 2", "b = 3", "ba"],
            None,
            lambda v: _to_int(v) == 6,
            id="implicit-mul-ba",
        ),
        param(
            ["A = 34", "A = A^2"],
            "A",
            lambda v: _to_int(v) == 1156,
            id="eager-self-reference",
        ),
        param(
            ["A = 2^4", "mean(A)"],
            None,
            lambda v: v == 16,
            id="scalar-var-feeds-mean",
        ),
        param(
            ["A = 1/2"],
            "A",
            lambda v: isinstance(v, calc_native.Rational),
            id="type-preserved-rational",
        ),
    ],
)
def test_stateful_variable_cases(lines, assert_env_key, check) -> None:
    result = _ev_multi(lines, assert_env_key=assert_env_key)
    assert check(result)


# ============================================================================
# Superscript ^{} power + subscript _{} variable (script fold)
# ============================================================================


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        param("2^{3}", 8, id="caret-pow-simple"),
        param("(2+5)^{4}", 2401, id="caret-pow-paren-base"),  # (2+5)=7, 7^4
        param("2^{1+1}", 4, id="caret-pow-braced-exp"),
        param("2^{3^{2}}", 512, id="caret-pow-nested"),
    ],
)
def test_caret_power(expr, expected) -> None:
    assert _to_int(_eval(expr)) == expected


@pytest.mark.parametrize(
    ("lines", "check"),
    [
        param(["n_{2} = 5", "n_{2}"], lambda v: _to_int(v) == 5, id="subscript-bind-resolve"),
        param(
            ["n_{1} = 1", "n_{2} = 2", "n_{1} + n_{2}"],
            lambda v: _to_int(v) == 3,
            id="subscript-independent-names",
        ),
        param(
            ["n = 7", "n_{2} = 5", "n + n_{2}"],
            lambda v: _to_int(v) == 12,
            id="subscript-distinct-from-bare",
        ),
    ],
)
def test_subscript_variable(lines, check) -> None:
    assert check(_ev_multi(lines))


@pytest.mark.parametrize("expr", ["y_{7}", "2_{3}"])
def test_subscript_invalid_raises(expr) -> None:
    from tcalc.errors import Error

    with pytest.raises(Error):
        _eval(expr)


# ============================================================================
# Constant table non-eval checks
# ============================================================================


def test_const_table_binding_shape() -> None:
    rows = {s.id: s for s in calc_native.const_table()}
    pi = rows[calc_native.ConstId.Pi]
    assert pi.symbol == "π"
    assert "pi" in pi.aliases
    assert isinstance(pi.value, float) and pi.value == math.pi
    iv = rows[calc_native.ConstId.Imaginary].value
    assert isinstance(iv, complex) and iv == 1j


def test_constants_module_derived_from_table() -> None:
    from tcalc.core import constants

    assert (
        constants.CONST_VALUES[calc_native.ConstId.Pi]
        == constants.CONST_BY_ID[calc_native.ConstId.Pi].value
    )
    assert not hasattr(constants, "CONSTANTS")


def test_assign_to_constant_rejected() -> None:
    from tcalc.core.engine import Calculator
    from tcalc.core.parser import evaluate_tokens, tokenize_string
    from tcalc.errors import CalculatorError

    with pytest.raises(CalculatorError) as e:
        evaluate_tokens(tokenize_string("pi = 3"), Calculator())
    assert "constant" in str(e.value)


@pytest.mark.parametrize(
    ("const_id", "symbol", "category", "value"),
    [
        param(
            calc_native.ConstId.PlanckHbar,
            "ℏ",
            calc_native.CategoryId.Universal,
            6.62607015e-34 / (2 * math.pi),
            id="hbar",
        ),
        param(
            calc_native.ConstId.Gravitation,
            "G",
            calc_native.CategoryId.Universal,
            6.67430e-11,
            id="G",
        ),
        param(
            calc_native.ConstId.VacuumImpedance,
            "Z₀",
            calc_native.CategoryId.Electromagnetism,
            376.730313412,
            id="Z0",
        ),
        param(
            calc_native.ConstId.ElementaryCharge,
            "ᵉ",
            calc_native.CategoryId.Electromagnetism,
            1.602176634e-19,
            id="elem-charge",
        ),
        param(
            calc_native.ConstId.Rydberg,
            "R∞",
            calc_native.CategoryId.AtomicNuclear,
            10973731.568157,
            id="rydberg",
        ),
        param(
            calc_native.ConstId.ElectronMass,
            "mₑ",
            calc_native.CategoryId.AtomicNuclear,
            9.1093837139e-31,
            id="m_e",
        ),
        param(
            calc_native.ConstId.Avogadro,
            "Nₐ",
            calc_native.CategoryId.Chemistry,
            6.02214076e23,
            id="avogadro",
        ),
        param(
            calc_native.ConstId.AtomicMass,
            "mᵤ",
            calc_native.CategoryId.Chemistry,
            1.66053906892e-27,
            id="atomic-mass",
        ),
    ],
)
def test_physics_constant_spec(const_id, symbol, category, value) -> None:
    spec = {s.id: s for s in calc_native.const_table()}[const_id]
    assert spec.symbol == symbol
    assert spec.category == category
    assert isinstance(spec.value, float)
    assert spec.value == value  # exact: no float() cast, no tolerance


def test_every_constant_symbol_and_alias_tokenizes() -> None:
    for spec in calc_native.const_table():
        spellings = [spec.symbol, *spec.aliases]
        for s in spellings:
            branch = calc_native.tokenize_string(s)
            assert len(branch.tokens) == 1, f"{s!r} -> {len(branch.tokens)} tokens"
            tok = branch.tokens[0]
            assert tok.kind == calc_native.TokenKind.Const, f"{s!r} -> {tok.kind}"
            assert tok.as_const().id == spec.id, f"{s!r} -> {tok.as_const().id}, want {spec.id}"
