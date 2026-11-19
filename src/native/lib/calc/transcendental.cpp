/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"

#include <cmath>
#include <cstdint>
#include <complex>
#include <limits>
#include <optional>
#include <utility>

#include <boost/multiprecision/cpp_dec_float.hpp>
#include <boost/multiprecision/cpp_complex.hpp>
#include <boost/math/tools/roots.hpp>

namespace {

/// Newton on z^n - x from the pow guess, whose exp(log) leaves noise in both parts.
BigComplex newton_root(const BigComplex &x, int n) {
    using boost::multiprecision::pow;
    const auto f = [&](const BigComplex &z) {
        const BigComplex p = pow(z, n - 1);
        return std::pair<BigComplex, BigComplex>(p * z - x, BigComplex(n) * p);
    };
    return boost::math::tools::complex_newton(f, pow(x, BigComplex(1) / BigComplex(n)));
}

/// Up to this |ilogb(x)| pow's root stays within 1 ulp, the accepted error (findings
/// real-root.md); past it the rounded 1/n times ln x reaches several ulps.
constexpr int kRootPowWithinUlpExponent = 8;
/// Boost's Newton takes a step cap; it bounds a stall, not the usual run from the pow guess.
constexpr std::uintmax_t kRootNewtonMaxIter = 20;

constexpr long double kLongDoubleOne = 1.0L;

/// z^k by squaring: std::pow on a long double is exp(log) again.
long double power_by_squaring(long double z, int k) {
    auto m = static_cast<unsigned>(k < 0 ? -static_cast<long long>(k) : k);
    long double r = kLongDoubleOne;
    for (; m != 0; m >>= 1U, z *= z)
        if ((m & 1U) != 0)
            r *= z;
    return k < 0 ? kLongDoubleOne / r : r;
}

/// Newton on z^n - x in long double, within 1 ulp once rounded to double. The derivative
/// is n p / z from the same p, so no n - 1 overflows at degree INT_MIN.
double newton_root(double x, int n) {
    const long double lx = x;
    const auto f = [&](long double z) {
        const long double p = power_by_squaring(z, n);
        return std::pair<long double, long double>(p - lx, static_cast<long double>(n) * p / z);
    };
    const long double guess = std::pow(x, 1.0 / n);
    std::uintmax_t iter = kRootNewtonMaxIter;
    const long double z = boost::math::tools::newton_raphson_iterate(
        f, guess, guess / 2, guess * 2, std::numeric_limits<long double>::digits, iter);
    const auto r = static_cast<double>(z);
    // A z on the midpoint of two doubles rounds twice, the tie going either way
    // ((7.4762568165974985e-159)⌄(-4)): the sign of z^n - x mostly says which side the root
    // is on (157 of 176 midpoints, findings real-root.md).
    const double other = std::nextafter(
        r,
        z > r ? std::numeric_limits<double>::infinity() : -std::numeric_limits<double>::infinity());
    if (z != (static_cast<long double>(r) + other) / 2)
        return r;
    const bool root_below = (f(z).first > 0) == (n > 0);
    return root_below ? std::fmin(r, other) : std::fmax(r, other);
}

/// pow's root is within 1 ulp near 1; Newton pays only where it is not.
bool root_needs_newton(double x) {
    return std::abs(std::ilogb(x)) > kRootPowWithinUlpExponent;
}

/// Newton from the pow guess, then the root at its 50 advertised digits when that is
/// exact: Newton leaves a residue in the guard digits even on 8e300 at 3.
BigReal newton_root(const BigReal &x, int n) {
    using boost::multiprecision::pow;
    const auto f = [&](const BigReal &z) {
        const BigReal p = pow(z, n);
        return std::pair<BigReal, BigReal>(p - x, BigReal(n) * p / z);
    };
    const BigReal guess = pow(x, BigReal(1) / n);
    std::uintmax_t iter = kRootNewtonMaxIter;
    const BigReal z = boost::math::tools::newton_raphson_iterate(
        f, guess, BigReal(0), BigReal(guess * 2), std::numeric_limits<BigReal>::digits, iter);
    const BigReal rounded(z.str(kBigRealPrecisionDigits));
    return pow(rounded, n) == x ? rounded : z;
}
} // namespace

// -----------------
// Real
// -----------------

double Calculator::sqrt(double a) const {
    calc_detail::require(a >= 0.0);
    return std::sqrt(a);
}

double Calculator::cbrt(double a) const {
    return std::cbrt(a);
}

double Calculator::root(double x, double y) const {
    calc_detail::require_nonzero(y);
    calc_detail::require(!(x == 0.0 && y < 0.0));

    if (x < 0.0) {
        if (calc_detail::whole(1.0 / y))
            return this->pow(x, 1.0 / y);
        calc_detail::require(calc_detail::odd_integer(y));
        if (const auto n = calc_detail::as_int(y); n && root_needs_newton(x))
            return -newton_root(-x, *n);
        return -this->pow(-x, 1.0 / y);
    }

    const auto n = calc_detail::as_int(y);
    // sqrt is correctly rounded; the Newton rounds twice ((1.7976931348623157e308)⌄2).
    if (n == 2)
        return this->sqrt(x);
    if (n && root_needs_newton(x))
        return newton_root(x, *n);
    return this->pow(x, 1.0 / y);
}

/// exp is its own primitive: routing it through pow(e, a) would go via log(e), which
/// costs the last digit and an order of magnitude in BigReal.
double Calculator::exp(double a) const {
    return std::exp(a);
}

BigReal Calculator::exp(const BigReal &a) const {
    using boost::multiprecision::exp;
    return exp(a);
}

Calculator::Complex Calculator::exp(Complex a) const {
    return std::exp(a);
}

BigComplex Calculator::exp(const BigComplex &a) const {
    using boost::multiprecision::exp;
    return exp(a);
}

double Calculator::log(double a) const {
    calc_detail::require(a > 0.0);
    return std::log10(a);
}

double Calculator::log(double a, double b) const {
    calc_detail::require(b > 0.0 && b != 1.0);
    // log(1e21) is exactly 21 today through std::log10, and log(a)/log(10) is
    // 20.999999999999996. Base ten keeps its own function so this arm does not regress it.
    if (b == kDecimalBase)
        return std::log10(a);
    return std::log(a) / std::log(b);
}

double Calculator::ln(double a) const {
    calc_detail::require(a > 0.0);
    return std::log(a);
}

// -----------------
// BigReal
// -----------------

BigReal Calculator::sqrt(const BigReal &a) const {
    calc_detail::require(a >= 0);
    using boost::multiprecision::sqrt;
    return sqrt(a);
}

BigReal Calculator::log(const BigReal &a) const {
    calc_detail::require(a > 0);
    using boost::multiprecision::log10;
    return log10(a);
}

BigReal Calculator::log(const BigReal &a, const BigReal &b) const {
    calc_detail::require(a > 0);
    calc_detail::require(b > 0 && b != 1);
    using boost::multiprecision::log10;
    if (b == kDecimalBase)
        return log10(a);
    using boost::multiprecision::log;
    return log(a) / log(b);
}

BigReal Calculator::ln(const BigReal &a) const {
    calc_detail::require(a > 0);
    using boost::multiprecision::log;
    return log(a);
}

BigReal Calculator::root(const BigReal &x, const BigReal &y) const {
    calc_detail::require_nonzero(y);
    calc_detail::require(!(x == 0 && y < 0));

    if (x < 0) {
        if (const BigReal m = BigReal(1) / y; calc_detail::whole(m))
            return this->pow(x, m);
        calc_detail::require(calc_detail::odd_integer(y));
        if (const auto n = calc_detail::as_int(calc_detail::snap_integer(y)))
            return -newton_root(-x, *n);
        return -this->pow(-x, BigReal(1) / y);
    }

    if (const auto n = calc_detail::as_int(calc_detail::snap_integer(y)))
        return newton_root(x, *n);
    return this->pow(x, BigReal(1) / y);
}

// -----------------
// Complex
// -----------------

Calculator::Complex Calculator::sqrt(Complex a) const {
    return std::sqrt(a);
}

Calculator::Complex Calculator::root(Complex x, Complex y) const {
    calc_detail::require_nonzero(y);
    if (y.imag() == 0.0) {
        if (y.real() == kSquare)
            return this->sqrt(x);
        if (const auto m = calc_detail::as_int(1.0 / y.real()))
            if (const auto r = calc_detail::integer_power(x, *m))
                return *r;
        // Newton in double leaves an irrational part one ulp off, so it runs in BigComplex.
        if (calc_detail::as_int(y.real()) && x != 0.0) {
            const BigComplex r = this->root(BigComplex(x.real(), x.imag()), BigComplex(y.real()));
            return {static_cast<double>(r.real()), static_cast<double>(r.imag())};
        }
    }
    return this->pow(x, 1.0 / y);
}

Calculator::Complex Calculator::log(Complex a) const {
    calc_detail::require_nonzero(a);
    return std::log10(a);
}

Calculator::Complex Calculator::log(Complex a, Complex b) const {
    // A complex base has no ordering, so there is no b != 1 shortcut to write here: only
    // what the type can express is guarded, the same as the unary overload above.
    calc_detail::require_nonzero(a);
    calc_detail::require_nonzero(b);
    return std::log(a) / std::log(b);
}

Calculator::Complex Calculator::ln(Complex a) const {
    calc_detail::require_nonzero(a);
    return std::log(a);
}

// -----------------
// BigComplex
// -----------------

BigComplex Calculator::sqrt(const BigComplex &a) const {
    using boost::multiprecision::sqrt;
    return sqrt(a);
}

BigComplex Calculator::root(const BigComplex &x, const BigComplex &y) const {
    calc_detail::require_nonzero(y);
    if (y.imag() == 0) {
        if (y.real() == kSquare)
            return this->sqrt(x);
        if (const auto m = calc_detail::as_int(BigComplex::value_type(1) / y.real()))
            if (const auto r = calc_detail::integer_power(x, *m))
                return *r;
        if (const auto n = calc_detail::as_int(y.real()); n && x != 0) {
            // Newton stops on an absolute tolerance below 1, so (-1e300) root -2 kept a real part.
            if (*n < 0)
                return BigComplex(1) / this->root(x, -y);
            return newton_root(x, *n);
        }
    }
    return this->pow(x, BigComplex(1) / y);
}

BigComplex Calculator::log(const BigComplex &a) const {
    calc_detail::require_nonzero(a);
    using boost::multiprecision::log10;
    return log10(a);
}

BigComplex Calculator::log(const BigComplex &a, const BigComplex &b) const {
    // Same reasoning as the Complex overload: no ordering on a complex base, so guard only
    // what the type can express.
    calc_detail::require_nonzero(a);
    calc_detail::require_nonzero(b);
    using boost::multiprecision::log;
    return log(a) / log(b);
}

BigComplex Calculator::ln(const BigComplex &a) const {
    calc_detail::require_nonzero(a);
    using boost::multiprecision::log;
    return log(a);
}

// -----------------
// Rational
// -----------------

Rational Calculator::log(const Rational &a, const Rational &b) const {
    if (const auto k = calc_detail::exact_rational_log(a, b))
        return Rational(*k);
    calc_detail::math_error();
}
