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
    // GCD / LCM
    // -----------------------------------------------------------------------

    TEST_CASE(ctx, "gcd :: basic", {
        EXPECT_EQ(ctx, c.gcd(12, 8), 4LL);
        EXPECT_EQ(ctx, c.gcd(7, 13), 1LL);
        EXPECT_EQ(ctx, c.gcd(100, 75), 25LL);
    });

    TEST_CASE(ctx, "gcd :: zero", {
        EXPECT_EQ(ctx, c.gcd(0, 5), 5LL);
        EXPECT_EQ(ctx, c.gcd(5, 0), 5LL);
        EXPECT_EQ(ctx, c.gcd(0, 0), 0LL);
    });

    TEST_CASE(ctx, "gcd :: negative", {
        EXPECT_EQ(ctx, c.gcd(-12, 8), 4LL);
        EXPECT_EQ(ctx, c.gcd(12, -8), 4LL);
        EXPECT_EQ(ctx, c.gcd(-12, -8), 4LL);
    });

    TEST_CASE(ctx, "gcd :: same number", { EXPECT_EQ(ctx, c.gcd(42, 42), 42LL); });

    TEST_CASE(ctx, "gcd :: coprime", { EXPECT_EQ(ctx, c.gcd(17, 31), 1LL); });

    TEST_CASE(ctx, "lcm :: basic", {
        EXPECT_EQ(ctx, c.lcm(4, 6), 12LL);
        EXPECT_EQ(ctx, c.lcm(3, 5), 15LL);
        EXPECT_EQ(ctx, c.lcm(12, 8), 24LL);
    });

    TEST_CASE(ctx, "lcm :: zero", {
        EXPECT_EQ(ctx, c.lcm(0, 5), 0LL);
        EXPECT_EQ(ctx, c.lcm(5, 0), 0LL);
        EXPECT_EQ(ctx, c.lcm(0, 0), 0LL);
    });

    TEST_CASE(ctx, "lcm :: one", {
        EXPECT_EQ(ctx, c.lcm(1, 7), 7LL);
        EXPECT_EQ(ctx, c.lcm(7, 1), 7LL);
    });

    TEST_CASE(ctx, "lcm :: same number", { EXPECT_EQ(ctx, c.lcm(42, 42), 42LL); });
}
