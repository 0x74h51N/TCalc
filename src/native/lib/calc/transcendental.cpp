/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"

#include <cmath>
#include <complex>
#include <limits>
#include <optional>

#include <boost/multiprecision/cpp_dec_float.hpp>
#include <boost/multiprecision/cpp_complex.hpp>
#include <boost/math/tools/roots.hpp>

namespace {
// The base a bare log is taken in, and the one base with a dedicated library function.
constexpr int kBaseTen = 10;
// The one degree with a dedicated library function, sqrt.
constexpr double kSquareDegree = 2.0;

/// Newton on z^n - x from the pow guess, whose exp(log) leaves noise in both parts.
BigComplex newton_root(const BigComplex &x, int n) {
    using boost::multiprecision::pow;
    const auto f = [&](const BigComplex &z) {
        const BigComplex p = pow(z, n - 1);
        return std::pair<BigComplex, BigComplex>(p * z - x, BigComplex(n) * p);
    };
    return boost::math::tools::complex_newton(f, pow(x, BigComplex(1) / BigComplex(n)));
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
        calc_detail::require(calc_detail::odd_integer(y));
        return -this->pow(-x, 1.0 / y);
    }

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
    if (b == kBaseTen)
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
    // Unlike double, a BigReal operand is never domain-checked ahead of the kernel: reading
    // it as a double to test the domain rule could underflow it to 0 and force a promotion
    // that was never warranted. So this guard is the only one it gets.
    calc_detail::require(a > 0);
    calc_detail::require(b > 0 && b != 1);
    using boost::multiprecision::log10;
    if (b == kBaseTen)
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
        calc_detail::require(calc_detail::odd_integer(y));
        return -this->pow(-x, BigReal(1) / y);
    }

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
        if (y.real() == kSquareDegree)
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
        if (y.real() == kSquareDegree)
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
