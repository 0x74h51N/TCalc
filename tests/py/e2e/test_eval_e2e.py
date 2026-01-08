from __future__ import annotations

from decimal import Decimal
import pytest
import math

calc_native = pytest.importorskip("calc_native")
param = pytest.param

def _eval(expr: str) -> object:
    from tcalc.core.engine import Calculator
    from tcalc.core.parser import evaluate_tokens, tokenize_string

    calc = Calculator()
    return evaluate_tokens(tokenize_string(expr), calc)


@pytest.mark.parametrize(
    ("expr", "expected_type", "expected_value"),
    [
        # ----------------------------
        # precedence / associativity
        # ----------------------------
        param("1+2*3", "float", 7.0, id="precedence-mul-over-add"),
        param("(1+2)*3", "float", 9.0, id="paren-overrides-precedence"),
        param("2^3^2", "float", 512.0, id="pow-right-assoc"),
        param("(2^3)^2", "float", 64.0, id="pow-parens-left-group"),
        param("-2^2", "float", -4.0, id="unary-vs-pow"),
        param("(-2)^2", "float", 4.0, id="pow-negative-base"),
        param("1/2/3", "float", (1.0/2.0)/3.0, id="left-assoc-division-chain"),
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
        param("1e1610e + 0", "BigReal", "2.718281828459045e+1610", id="implicit-mul-constant-bigreal"),
        param("(1e-3 + 2e-3) * 1000", "float", 3.0, id="scientific-notation-flow"),
        param("2π", "float", 2.0 * math.pi, id="pi-symbol-implicit-mul"),
        param("π*10^309", "BigReal", "3.141592653589793e+309", id="pi-symbol-promotes-bigreal"),
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
        param("log(-1) + log(-2)", "complex", (0.3010299956639812, 2.728752707683683), id="complex-add-two-domains"),
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
    ],
)
def test_native_eval_golden(expr: str, expected_type: str, expected_value: object) -> None:
    if expected_type == "float":
        out = _eval(expr)
        assert isinstance(out, (int, float))
        assert float(out) == pytest.approx(expected_value)
        return

    if expected_type == "complex":
        out = _eval(expr)
        assert isinstance(out, complex)
        real, imag = out.real, out.imag
        exp_real, exp_imag = expected_value
        assert real == pytest.approx(exp_real)
        assert imag == pytest.approx(exp_imag)
        return

    out = _eval(expr)
    assert type(out).__name__ == expected_type
    assert expected_value in str(out)


def test_pow_boundary_exactness() -> None:
    out = _eval("(10^308*10)/(10^309)")
    assert isinstance(out, calc_native.BigReal)
    assert Decimal(str(out)) == Decimal(1)

def test_pow_exponent_is_int_after_parser_number_coercion() -> None:
    from tcalc.core import parser as parser_mod

    tokens = parser_mod.tokenize_string("2^3")
    number_literals = [t.value for t in tokens if t.kind == calc_native.TokenKind.Number]
    assert len(number_literals) >= 2

    exponent = parser_mod._coerce_token(number_literals[-1])
    assert exponent == 3
    assert isinstance(exponent, int)

    tokens = parser_mod.tokenize_string("2^3.0")
    number_literals = [t.value for t in tokens if t.kind == calc_native.TokenKind.Number]
    exponent = parser_mod._coerce_token(number_literals[-1])
    assert exponent == pytest.approx(3.0)
    assert isinstance(exponent, float)
