/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"

#include <algorithm>
#include <cmath>

#include <boost/math/special_functions/beta.hpp>
#include <boost/math/special_functions/factorials.hpp>
#include <boost/math/special_functions/gamma.hpp>
#include <boost/multiprecision/cpp_dec_float.hpp>

namespace {
/// 20! is the largest factorial int64 holds.
constexpr std::int64_t kMaxInt64Factorial = 20;
} // namespace

double Calculator::fact(double a) const {
    if (calc_detail::int_like(a) && a < 0.0) {
        calc_detail::math_error();
    }
    // Boost's table is correctly rounded; tgamma misses a whole number by a few ulp (#261).
    if (calc_detail::whole(a) && a >= 0.0 && a <= boost::math::max_factorial<double>::value)
        return boost::math::factorial<double>(static_cast<unsigned>(a));

    return std::tgamma(a + 1.0);
}

double Calculator::gamma(double a) const {
    if (a <= 0.0 && calc_detail::int_like(a)) {
        calc_detail::math_error();
    }
    if (calc_detail::whole(a) && a >= 1.0 && a <= boost::math::max_factorial<double>::value + 1)
        return boost::math::factorial<double>(static_cast<unsigned>(a) - 1);

    return std::tgamma(a);
}

// Past 20, or for a fraction, it throws, and the op's row retries a whole number in BigReal and
// a fraction in double. Every factorial up to 20 is exact in Boost's double table.
std::int64_t Calculator::fact(const Rational &a) const {
    calc_detail::require(calc_detail::whole(a));
    const std::int64_t n = a.numerator();
    calc_detail::require(n >= 0 && n <= kMaxInt64Factorial);
    return static_cast<std::int64_t>(boost::math::factorial<double>(static_cast<unsigned>(n)));
}

// The pole check also keeps n - 1 from overflowing at INT64_MIN.
std::int64_t Calculator::gamma(const Rational &a) const {
    calc_detail::require(calc_detail::whole(a) && a.numerator() >= 1);
    return fact(Rational(a.numerator() - 1));
}

BigReal Calculator::fact(const BigReal &a) const {
    calc_detail::require(a >= 0);
    // Boost's BigReal table is exact to 50 digits and far cheaper than its tgamma.
    if (calc_detail::snapped_whole(a) && a <= boost::math::max_factorial<BigReal>::value)
        return boost::math::factorial<BigReal>(a.convert_to<unsigned>());

    using boost::math::tgamma;
    return tgamma(a + 1);
}

BigReal Calculator::gamma(const BigReal &a) const {
    if (a <= 0) {
        // gamma's poles sit on the non-positive integers, so integerness is read at the
        // precision BigReal advertises rather than off its guard digits.
        const BigReal snapped = calc_detail::snap_integer(a);
        using boost::multiprecision::floor;
        if (floor(snapped) == snapped) {
            calc_detail::math_error();
        }
    }
    if (calc_detail::snapped_whole(a) && a <= boost::math::max_factorial<BigReal>::value + 1)
        return boost::math::factorial<BigReal>(a.convert_to<unsigned>() - 1);

    using boost::math::tgamma;
    return tgamma(a);
}

//
// Permute
//
BigReal Calculator::permute(long long a, long long b) const {
    if (!calc_detail::nonneg_or_zero(a, b)) {
        return BigReal(0);
    }

    // a! / (a-b)! as one gamma ratio, so neither factorial is formed on its own.
    return round(
        boost::math::tgamma_delta_ratio(BigReal(a) + 1, BigReal(-b), calc_detail::InfOnOverflow()));
}

BigReal Calculator::choose(long long a, long long b) const {
    if (!calc_detail::nonneg_or_zero(a, b)) {
        return BigReal(0);
    }

    const long long k = std::min(b, a - b);
    // beta(0, x) is a pole.
    if (k == 0) {
        return BigReal(1);
    }
    // In BigReal, beta's last digit is off past 1e47 and round would take the neighbor.
    using calc_detail::WideReal;
    return BigReal(round(1 / (WideReal(k) * boost::math::beta(WideReal(k), WideReal(a - k) + 1))));
}
