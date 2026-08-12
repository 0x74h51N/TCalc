/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <optional>
#include <utility>

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

/// Check whether dividing a Rational by a positive integer divisor would overflow int64.
/// boost::rational's operator/= reduces gcd(numerator, divisor) first, so the result denominator
/// is denominator * (divisor / gcd); a large denominator with a numerator coprime to divisor can
/// push that product past INT64_MAX with no bound check of its own. Declining is the right call:
/// nothing about the input is invalid, there is just no exact quotient to report.
inline bool rational_div_overflows(const Rational &a, std::int64_t divisor) {
    // std::gcd takes the argument's absolute value internally, which is UB at INT64_MIN
    // (libstdc++ asserts and aborts); declining here is the correct answer anyway, since
    // there is no exact quotient path for a numerator this size.
    if (a.numerator() == (std::numeric_limits<std::int64_t>::min)())
        return true;
    const std::int64_t factor = divisor / std::gcd(a.numerator(), divisor);
    return a.denominator() > (std::numeric_limits<std::int64_t>::max)() / factor;
}

/// Whether folding t into the first quadrant (Calculator::real_half_turns) would overflow
/// int64: the reduction forms p in [0, 2*denominator) and then 2*p to find the quadrant, so
/// 2*p reaches up to 4*denominator - 2. A denominator past a quarter of int64's range cannot
/// take the plain int64 fold. Written as a division comparison, never a multiplication, since
/// multiplying denominator by 4 first is exactly the overflow this is checking for.
inline bool half_turn_fold_overflows(std::int64_t denominator) {
    return denominator > (std::numeric_limits<std::int64_t>::max)() / 4;
}

/// floor(m^(1/q)) for m >= 2, q >= 2, over exact big integers. Only a floor estimate; the
/// caller is what verifies r^q == m. Boost has an exact integer square root but no general
/// integer n-th root, so q == 2 uses that directly and larger q falls to Newton, the same
/// method GMP's mpz_root uses internally. Returns 1 when q exceeds m's bit length: any r >= 2
/// already overshoots there (2^q > m), so no Newton run can help.
/// See: https://en.wikipedia.org/wiki/Nth_root_algorithm
inline boost::multiprecision::cpp_int
integer_root_floor(const boost::multiprecision::cpp_int &m, long long q) {
    using boost::multiprecision::cpp_int;
    const auto bits = static_cast<long long>(boost::multiprecision::msb(m)) + 1;
    if (q > bits)
        return 1;
    if (q == 2)
        return boost::multiprecision::sqrt(m);
    // Newton for the integer q-th root, quadratic convergence from an overestimate:
    // r_{k+1} = ((q-1) r_k + m / r_k^(q-1)) / q.
    const auto qu = static_cast<unsigned>(q); // q <= bits here, so this always fits
    cpp_int r = 1;
    r <<= static_cast<unsigned>((bits + q - 1) / q); // 2^ceil(bits/q) >= the true root
    while (true) {
        const cpp_int next = ((q - 1) * r + m / boost::multiprecision::pow(r, qu - 1)) / q;
        if (next >= r)
            return r;
        r = next;
    }
}

/// Try to compute the exact integer q-th root of val (q >= 1).
/// Returns nullopt if val^(1/q) is not an exact integer: an irrational magnitude, or an even
/// root of a negative value. The verification is on the *signed* value, so (-4)^(1/2) declines
/// while (-8)^(1/3) is -2.
///
/// Templated on the integer type, with the arithmetic done in arbitrary precision, so one body
/// serves both the int64 (Rational) and the cpp_int (closed-form) callers: a double
/// approximation of the root cannot decide rootness once the value passes double's precision
/// (pow(8.0, 1.0/3.0) is 1.9999999999999998) or its range.
template <class Int> std::optional<Int> exact_int_root(const Int &val, long long q) {
    using boost::multiprecision::cpp_int;
    if (q <= 0)
        return std::nullopt;
    if (q == 1)
        return val;
    // Binds directly for a cpp_int caller; for an int64 one it lifetime-extends the converted
    // temporary. Either way no copy of an already-big value.
    const cpp_int &v = val;
    if (v == 0 || v == 1)
        return val; // 0^(1/q) = 0, 1^(1/q) = 1
    if (v == -1)
        return (q % 2 != 0) ? std::optional<Int>(val) : std::nullopt;
    const bool negative = v < 0;
    if (negative && (q % 2 == 0))
        return std::nullopt;
    const cpp_int mag = boost::multiprecision::abs(v);
    const cpp_int r = integer_root_floor(mag, q);
    if (r < 2)
        return std::nullopt; // mag > 1 here, so a floor root of 1 cannot be exact
    // r >= 2 implies 2^q <= r^q <= mag, so q is bounded by mag's bit length and the cast fits.
    if (boost::multiprecision::pow(r, static_cast<unsigned>(q)) != mag)
        return std::nullopt;
    return static_cast<Int>(negative ? -r : r);
}

/// Numerator/denominator of a rational value: Rational exposes member accessors, boost's
/// cpp_rational needs its free boost::multiprecision::numerator/denominator. These two
/// overloads bridge that so exact_rational_root can be written once, templated over both,
/// instead of once per accessor style.
inline std::pair<std::int64_t, std::int64_t> rational_parts(const Rational &r) {
    return {r.numerator(), r.denominator()};
}
inline std::pair<boost::multiprecision::cpp_int, boost::multiprecision::cpp_int>
rational_parts(const boost::multiprecision::cpp_rational &r) {
    return {boost::multiprecision::numerator(r), boost::multiprecision::denominator(r)};
}

/// Exact q-th root of a rational c (Rational or boost's cpp_rational), or nullopt when it does
/// not exist. Numerator and denominator are rooted separately by exact_int_root and recombined;
/// every guard that matters (q <= 0, q == 1, the 0/1/-1 cases, an even root of a negative value)
/// already lives inside exact_int_root, so this adds none of its own. The verification is on
/// each part's *signed* value, so (-4)^(1/2) declines while (-8)^(1/3) is -2.
template <class R> std::optional<R> exact_rational_root(const R &c, long long q) {
    const auto [num, den] = rational_parts(c);
    const auto nr = exact_int_root(num, q);
    const auto dr = exact_int_root(den, q);
    if (!nr || !dr)
        return std::nullopt;
    return R(*nr, *dr);
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
    return exact_rational_root(powered, q);
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
