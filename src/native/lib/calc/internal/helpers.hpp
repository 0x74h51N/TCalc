/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <cmath>
#include <cstdint>
#include <limits>
#include <optional>

#include <boost/multiprecision/cpp_int.hpp>

#include "calc/pub/calculator.hpp"

namespace calc_detail {

constexpr double kDefaultEpsilon = 1e-12;

[[noreturn]] inline void math_error() {
    throw CalculatorError("Math error");
}

inline void require(bool ok) {
    if (!ok) {
        math_error();
    }
}

inline bool int_like(double x, double eps = kDefaultEpsilon) {
    const double rounded = std::round(x);
    return std::abs(x - rounded) <= eps;
}

inline void require_nonzero(double x) {
    require(x != 0.0);
}

inline void require_nonzero(const BigReal &x) {
    require(x != 0);
}

inline void require_nonzero(const boost::rational<std::int64_t> &x) {
    require(x != 0);
}

inline void require_nonzero(Calculator::Complex x) {
    require(!(x.real() == 0.0 && x.imag() == 0.0));
}

inline void require_nonzero(const BigComplex &x) {
    using boost::multiprecision::backends::eval_is_zero;
    const auto &re = x.backend().real_data();
    const auto &im = x.backend().imag_data();
    require(!(eval_is_zero(re) && eval_is_zero(im)));
}

inline bool nonneg_or_zero(long long n, long long k) {
    if (n < 0 || k < 0) {
        math_error();
    }
    return n >= k;
}

/// Safe bits for signed int64 overflow estimation.
inline constexpr double kInt64SafeBits = 62.0;

/// Check whether base^exp would overflow int64 for Rational pow.
inline bool rational_pow_overflows(const Rational &base, long long exp) {
    const double abs_exp = std::fabs(static_cast<double>(exp));
    if (abs_exp <= 1.0)
        return false;
    auto check = [abs_exp](std::int64_t val) -> bool {
        if (val == 0 || val == 1 || val == -1)
            return false;
        double log2_abs = std::log2(std::abs(static_cast<double>(val)));
        return log2_abs * abs_exp >= kInt64SafeBits;
    };
    return check(base.numerator()) || check(base.denominator());
}

/// Try to compute the exact integer q-th root of val (q >= 1).
/// Returns nullopt if val^(1/q) is not an exact integer.
inline std::optional<std::int64_t> exact_int_root(std::int64_t val, long long q) {
    if (q <= 0)
        return std::nullopt;
    if (q == 1)
        return val;
    if (val == 0)
        return std::int64_t(0);
    if (val == 1)
        return std::int64_t(1);
    if (val == -1)
        return (q % 2 != 0) ? std::optional<std::int64_t>(-1) : std::nullopt;

    const bool negative = val < 0;
    if (negative && (q % 2 == 0))
        return std::nullopt;

    const auto abs_val = static_cast<std::uint64_t>(negative ? -val : val);
    const auto abs_max = static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max());

    // Float approximation, then verify candidate ± 1.
    const double approx = std::pow(static_cast<double>(abs_val), 1.0 / static_cast<double>(q));
    auto lo = static_cast<std::int64_t>(std::floor(approx));
    if (lo < 2)
        lo = 2;

    for (std::int64_t c = lo; c <= lo + 2; ++c) {
        std::uint64_t power = 1;
        bool overflow = false;
        for (long long i = 0; i < q; ++i) {
            if (power > abs_max / static_cast<std::uint64_t>(c)) {
                overflow = true;
                break;
            }
            power *= static_cast<std::uint64_t>(c);
            if (power > abs_val) {
                overflow = true;
                break;
            }
        }
        if (!overflow && power == abs_val) {
            return negative ? -c : c;
        }
    }
    return std::nullopt;
}

/// Try to compute base^exp as an exact Rational.
/// Returns nullopt if the result is not exactly representable:
///   - integer exp: int64 overflow
///   - fractional exp (p/q): either overflow in base^p, or p-th power's
///     numerator/denominator is not a perfect q-th power
/// Caller is expected to fall back to double / BigReal.
inline std::optional<Rational>
try_rational_pow(const Calculator &calc, const Rational &base, const Rational &exp) {
    const long long p = exp.numerator();
    const long long q = exp.denominator();

    // Integer exponent.
    if (q == 1) {
        if (rational_pow_overflows(base, p))
            return std::nullopt;
        return calc.pow(base, exp);
    }

    // Fractional exponent p/q: compute base^p exactly, then try exact q-th root.
    if (rational_pow_overflows(base, p))
        return std::nullopt;

    const Rational powered = calc.pow(base, Rational(p));
    const auto nr = exact_int_root(powered.numerator(), q);
    const auto dr = exact_int_root(powered.denominator(), q);
    if (!nr || !dr)
        return std::nullopt;
    return Rational(*nr, *dr);
}

/// Wide rational for overflow-safe add/sub/mul/div: int64 arithmetic on
/// boost::rational wraps silently on overflow instead of reporting it, so the
/// four basic ops compute here, then narrow back and reject what does not fit.
using WideRational = boost::rational<boost::multiprecision::int256_t>;

inline WideRational widen(const Rational &r) {
    using boost::multiprecision::int256_t;
    return WideRational(int256_t(r.numerator()), int256_t(r.denominator()));
}

/// Reduced by boost::rational's own arithmetic; nullopt when either side of the
/// reduced fraction does not fit back into int64.
inline std::optional<Rational> narrow(const WideRational &w) {
    using boost::multiprecision::int256_t;
    constexpr auto kMax = std::numeric_limits<std::int64_t>::max();
    constexpr auto kMin = std::numeric_limits<std::int64_t>::min();
    const int256_t &num = w.numerator();
    const int256_t &den = w.denominator();
    if (num < int256_t(kMin) || num > int256_t(kMax) || den < int256_t(kMin) ||
        den > int256_t(kMax))
        return std::nullopt;
    return Rational(static_cast<std::int64_t>(num), static_cast<std::int64_t>(den));
}

} // namespace calc_detail
