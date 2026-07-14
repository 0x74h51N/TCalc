/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/internal/helpers.hpp"
#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

void unit_rational(TestContext &ctx) {
    Calculator c;

    // -----------------------------------------------------------------------
    // Rational struct basics
    // -----------------------------------------------------------------------

    TEST_CASE(ctx, "struct :: integer constructor normalizes", {
        Rational r(6);
        EXPECT_EQ(ctx, r.numerator(), 6LL);
        EXPECT_EQ(ctx, r.denominator(), 1LL);
    });

    TEST_CASE(ctx, "struct :: num/den constructor normalizes via GCD", {
        Rational r(6, 4);
        EXPECT_EQ(ctx, r.numerator(), 3LL);
        EXPECT_EQ(ctx, r.denominator(), 2LL);
    });

    TEST_CASE(ctx, "struct :: negative denominator normalized", {
        Rational r(3, -4);
        EXPECT_EQ(ctx, r.numerator(), -3LL);
        EXPECT_EQ(ctx, r.denominator(), 4LL);
    });

    TEST_CASE(ctx, "struct :: to_double", {
        Rational r(1, 3);
        EXPECT_TRUE(ctx, approx(r.to_double(), 1.0 / 3.0));
    });

    TEST_CASE(ctx, "arithmetic :: add 1/3 + 1/6 = 1/2", {
        Rational a(1, 3), b(1, 6);
        auto result = Rational(a.frac + b.frac);
        EXPECT_EQ(ctx, result.numerator(), 1LL);
        EXPECT_EQ(ctx, result.denominator(), 2LL);
    });

    TEST_CASE(ctx, "arithmetic :: mul 2/3 * 3/4 = 1/2", {
        Rational a(2, 3), b(3, 4);
        auto result = Rational(a.frac * b.frac);
        EXPECT_EQ(ctx, result.numerator(), 1LL);
        EXPECT_EQ(ctx, result.denominator(), 2LL);
    });

    TEST_CASE(ctx, "arithmetic :: div 2/3 ÷ 4/5 = 5/6", {
        Rational a(2, 3), b(4, 5);
        auto result = Rational(a.frac / b.frac);
        EXPECT_EQ(ctx, result.numerator(), 5LL);
        EXPECT_EQ(ctx, result.denominator(), 6LL);
    });

    TEST_CASE(ctx, "arithmetic :: negate -2/3", {
        Rational a(2, 3);
        auto result = Rational(-a.frac);
        EXPECT_EQ(ctx, result.numerator(), -2LL);
        EXPECT_EQ(ctx, result.denominator(), 3LL);
    });

    TEST_CASE(ctx, "arithmetic :: 1/3 * 3 = 1 (exact cancellation)", {
        Rational a(1, 3), b(3, 1);
        auto result = Rational(a.frac * b.frac);
        EXPECT_EQ(ctx, result.numerator(), 1LL);
        EXPECT_EQ(ctx, result.denominator(), 1LL);
    });

    // -----------------------------------------------------------------------
    // Calculator::pow(Rational, Rational)
    // -----------------------------------------------------------------------

    TEST_CASE(ctx, "pow :: integer exponent", {
        // (2/3)^3 = 8/27
        auto r = c.pow(Rational(2, 3), Rational(3));
        EXPECT_EQ(ctx, r.numerator(), 8LL);
        EXPECT_EQ(ctx, r.denominator(), 27LL);
    });

    TEST_CASE(ctx, "pow :: zero exponent", {
        auto r = c.pow(Rational(7, 11), Rational(0));
        EXPECT_EQ(ctx, r.numerator(), 1LL);
        EXPECT_EQ(ctx, r.denominator(), 1LL);
    });

    TEST_CASE(ctx, "pow :: exponent one is identity", {
        auto r = c.pow(Rational(5, 3), Rational(1));
        EXPECT_EQ(ctx, r.numerator(), 5LL);
        EXPECT_EQ(ctx, r.denominator(), 3LL);
    });

    TEST_CASE(ctx, "pow :: negative exponent inverts", {
        // (2/3)^(-2) = 9/4
        auto r = c.pow(Rational(2, 3), Rational(-2));
        EXPECT_EQ(ctx, r.numerator(), 9LL);
        EXPECT_EQ(ctx, r.denominator(), 4LL);
    });

    TEST_CASE(ctx, "pow :: negative base even exp", {
        auto r = c.pow(Rational(-3), Rational(4));
        EXPECT_EQ(ctx, r.numerator(), 81LL);
        EXPECT_EQ(ctx, r.denominator(), 1LL);
    });

    TEST_CASE(ctx, "pow :: negative base odd exp", {
        auto r = c.pow(Rational(-3), Rational(3));
        EXPECT_EQ(ctx, r.numerator(), -27LL);
        EXPECT_EQ(ctx, r.denominator(), 1LL);
    });

    TEST_CASE(ctx, "pow :: fractional exponent throws", {
        EXPECT_THROWS(ctx, c.pow(Rational(2), Rational(1, 2)));
    });

    TEST_CASE(ctx, "pow :: zero base negative exp throws", {
        EXPECT_THROWS(ctx, c.pow(Rational(0), Rational(-1)));
    });

    // -----------------------------------------------------------------------
    // Calculator::sqrt/cbrt/root(Rational)
    // -----------------------------------------------------------------------

    TEST_CASE(ctx, "sqrt :: exact when both numerator and denominator are perfect squares", {
        auto r = c.sqrt(Rational(4, 9));
        EXPECT_EQ(ctx, r.numerator(), 2LL);
        EXPECT_EQ(ctx, r.denominator(), 3LL);
    });

    TEST_CASE(ctx, "cbrt :: odd degree of a negative base is fine", {
        auto r = c.cbrt(Rational(-8, 27));
        EXPECT_EQ(ctx, r.numerator(), -2LL);
        EXPECT_EQ(ctx, r.denominator(), 3LL);
    });

    TEST_CASE(ctx, "root :: 8^(1/3) = 2", {
        auto r = c.root(Rational(8), Rational(3));
        EXPECT_EQ(ctx, r.numerator(), 2LL);
        EXPECT_EQ(ctx, r.denominator(), 1LL);
    });

    TEST_CASE(ctx, "sqrt :: irrational throws", { EXPECT_THROWS(ctx, c.sqrt(Rational(2))); });

    TEST_CASE(ctx, "sqrt :: numerator has an exact root, denominator does not throws", {
        EXPECT_THROWS(ctx, c.sqrt(Rational(4, 5)));
    });

    TEST_CASE(ctx, "sqrt :: even degree of a negative has no real root throws", {
        EXPECT_THROWS(ctx, c.sqrt(Rational(-1)));
    });

    TEST_CASE(ctx, "root :: zero degree throws", {
        EXPECT_THROWS(ctx, c.root(Rational(4), Rational(0)));
    });

    // -----------------------------------------------------------------------
    // calc_detail::rational_pow_overflows (binding-layer guard)
    // -----------------------------------------------------------------------

    TEST_CASE(ctx, "pow_overflows :: 2^61 fits int64", {
        EXPECT_TRUE(ctx, !calc_detail::rational_pow_overflows(Rational(2), 61));
    });

    TEST_CASE(ctx, "pow_overflows :: 2^62 overflows int64", {
        EXPECT_TRUE(ctx, calc_detail::rational_pow_overflows(Rational(2), 62));
    });

    TEST_CASE(ctx, "pow_overflows :: negative exp uses abs — 2^(-62) overflows", {
        EXPECT_TRUE(ctx, calc_detail::rational_pow_overflows(Rational(2), -62));
    });

    TEST_CASE(ctx, "pow_overflows :: negative exp uses abs — 2^(-61) fits", {
        EXPECT_TRUE(ctx, !calc_detail::rational_pow_overflows(Rational(2), -61));
    });

    TEST_CASE(ctx, "pow_overflows :: base 1 never overflows", {
        EXPECT_TRUE(ctx, !calc_detail::rational_pow_overflows(Rational(1), 1000));
    });

    TEST_CASE(ctx, "pow_overflows :: base 0 never overflows", {
        EXPECT_TRUE(ctx, !calc_detail::rational_pow_overflows(Rational(0), 1000));
    });

    TEST_CASE(ctx, "pow_overflows :: denominator overflow (1/2)^62", {
        EXPECT_TRUE(ctx, calc_detail::rational_pow_overflows(Rational(1, 2), 62));
    });

    TEST_CASE(ctx, "pow_overflows :: denominator fits (1/2)^61", {
        EXPECT_TRUE(ctx, !calc_detail::rational_pow_overflows(Rational(1, 2), 61));
    });

    // -----------------------------------------------------------------------
    // add / sub / mul / div overflow
    //
    // A Rational holds its numerator and denominator in int64. When an exact
    // result does not fit, the operation must say so, and the caller falls back
    // to double. Returning a wrapped value is the one thing it must never do:
    // 0.0000000001 * 0.0000000001 has the exact denominator 1e20, and wrapping
    // it produces 1/7766279631452241920, a plausible-looking number that is off
    // by an order of magnitude.
    // -----------------------------------------------------------------------

    constexpr long long kI64Max = 9223372036854775807LL;
    constexpr long long kI64Min = -9223372036854775807LL - 1;

    TEST_CASE(ctx, "mul :: denominator overflow throws", {
        // 1/4e9 * 1/4e9 = 1/1.6e19, past int64
        EXPECT_THROWS(ctx, c.mul(Rational(1, 4000000000), Rational(1, 4000000000)));
    });

    TEST_CASE(ctx, "mul :: numerator overflow throws", {
        EXPECT_THROWS(ctx, c.mul(Rational(4000000000), Rational(4000000000)));
    });

    TEST_CASE(ctx, "add :: numerator overflow throws", {
        EXPECT_THROWS(ctx, c.add(Rational(kI64Max), Rational(1)));
    });

    TEST_CASE(ctx, "add :: denominator overflow throws", {
        // 1/4e9 + 1/(4e9 + 1): coprime denominators, so the product is the result's
        EXPECT_THROWS(ctx, c.add(Rational(1, 4000000000), Rational(1, 4000000001)));
    });

    TEST_CASE(ctx, "sub :: numerator overflow throws", {
        EXPECT_THROWS(ctx, c.sub(Rational(kI64Min), Rational(1)));
    });

    TEST_CASE(ctx, "div :: denominator overflow throws", {
        // (1/4e9) / 4e9 = 1/1.6e19
        EXPECT_THROWS(ctx, c.div(Rational(1, 4000000000), Rational(4000000000)));
    });

    // The guard must not reject a result that does fit.

    TEST_CASE(ctx, "mul :: a result at the edge of int64 is exact", {
        // 3037000499^2 = 9223372030926249001, just under int64 max
        auto r = c.mul(Rational(3037000499), Rational(3037000499));
        EXPECT_EQ(ctx, r.numerator(), 9223372030926249001LL);
        EXPECT_EQ(ctx, r.denominator(), 1LL);
    });

    TEST_CASE(ctx, "mul :: intermediates may overflow while the reduced result fits", {
        // 4e9/3 * 3/4e9 = 1: the raw products pass int64, the reduced result is 1/1
        auto r = c.mul(Rational(4000000000, 3), Rational(3, 4000000000));
        EXPECT_EQ(ctx, r.numerator(), 1LL);
        EXPECT_EQ(ctx, r.denominator(), 1LL);
    });

    TEST_CASE(ctx, "add :: a shared denominator does not overflow", {
        // 1/4e9 + 1/4e9 = 1/2e9: the denominators reduce, nothing overflows
        auto r = c.add(Rational(1, 4000000000), Rational(1, 4000000000));
        EXPECT_EQ(ctx, r.numerator(), 1LL);
        EXPECT_EQ(ctx, r.denominator(), 2000000000LL);
    });
}
