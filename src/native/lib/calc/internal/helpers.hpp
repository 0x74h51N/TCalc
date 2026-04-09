/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <cmath>
#include <cstdint>
#include <optional>

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

} // namespace calc_detail
