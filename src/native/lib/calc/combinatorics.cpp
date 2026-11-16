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
#include <boost/math/special_functions/gamma.hpp>
#include <boost/multiprecision/cpp_dec_float.hpp>

double Calculator::fact(double a) const {
    if (calc_detail::int_like(a) && a < 0.0) {
        calc_detail::math_error();
    }

    return std::tgamma(a + 1.0);
}

double Calculator::gamma(double a) const {
    if (a <= 0.0 && calc_detail::int_like(a)) {
        calc_detail::math_error();
    }

    return std::tgamma(a);
}

BigReal Calculator::fact(const BigReal &a) const {
    calc_detail::require(a >= 0);

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
