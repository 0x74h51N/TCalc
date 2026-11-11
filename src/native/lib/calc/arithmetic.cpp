/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"

#include <cmath>
#include <complex>

#include <boost/multiprecision/cpp_dec_float.hpp>

// -----------------
// Real
// -----------------

double Calculator::div(double a, double b) const {
    calc_detail::require_nonzero(b);
    return a / b;
}

double Calculator::mod(double a, double b) const {
    calc_detail::require_nonzero(b);
    return std::fmod(a, b);
}

double Calculator::pow(double a, long long b) const {
    calc_detail::require(b >= 0 || a != 0.0);

    long long exp = b;
    double result = 1.0;
    double base = a;

    if (exp < 0) {
        calc_detail::require_nonzero(base);
        exp = -exp;
        base = 1.0 / base;
    }

    while (exp > 0) {
        if ((exp & 1LL) != 0) {
            result *= base;
        }
        base *= base;
        exp >>= 1;
    }

    return result;
}

double Calculator::pow(double a, double b) const {
    calc_detail::require(b >= 0 || a != 0.0);
    // std::pow is nan for every negative base under a fractional exponent, even where the
    // root it means is real: (-2)^(1/3) is the cube root of -2.
    if (a < 0.0 && !calc_detail::whole(b) && calc_detail::odd_integer(1.0 / b))
        return this->root(a, std::round(1.0 / b));
    return std::pow(a, b);
}

long long Calculator::intdiv(double a, double b) const {

    calc_detail::require_nonzero(b);
    return static_cast<long long>(a / b);
}

double Calculator::trunc(double a) const {
    return std::trunc(a);
}

double Calculator::floor(double a) const {
    return std::floor(a);
}

double Calculator::ceil(double a) const {
    return std::ceil(a);
}

// -----------------
// BigReal
// -----------------

BigReal Calculator::div(const BigReal &a, const BigReal &b) const {
    calc_detail::require_nonzero(b);
    return a / b;
}

BigReal Calculator::intdiv(const BigReal &a, const BigReal &b) const {
    calc_detail::require_nonzero(b);
    return calc_detail::trunc_div(a, b).quot;
}

BigReal Calculator::pow(const BigReal &a, const BigReal &b) const {
    calc_detail::require(b >= 0 || a != 0);
    if (const BigReal m = BigReal(1) / b;
        a < 0 && !calc_detail::whole(b) && calc_detail::odd_integer(m))
        return this->root(a, calc_detail::snap_integer(m));
    using boost::multiprecision::pow;
    // An exact quotient sits under its integer in the guard digits, where Boost reads it.
    return pow(a, calc_detail::snap_integer(b));
}

BigReal Calculator::mod(const BigReal &a, const BigReal &b) const {
    calc_detail::require_nonzero(b);
    return calc_detail::trunc_div(a, b).rem;
}

BigReal Calculator::trunc(const BigReal &a) const {
    using boost::multiprecision::trunc;
    return trunc(calc_detail::snap_integer(a));
}

BigReal Calculator::floor(const BigReal &a) const {
    using boost::multiprecision::floor;
    return floor(calc_detail::snap_integer(a));
}

BigReal Calculator::ceil(const BigReal &a) const {
    using boost::multiprecision::ceil;
    return ceil(calc_detail::snap_integer(a));
}

// -----------------
// Rational
// -----------------

Rational Calculator::add(const Rational &a, const Rational &b) const {
    if (auto r = calc_detail::narrow(calc_detail::widen(a) + calc_detail::widen(b)))
        return *r;
    calc_detail::math_error();
}

Rational Calculator::sub(const Rational &a, const Rational &b) const {
    if (auto r = calc_detail::narrow(calc_detail::widen(a) - calc_detail::widen(b)))
        return *r;
    calc_detail::math_error();
}

Rational Calculator::mul(const Rational &a, const Rational &b) const {
    if (auto r = calc_detail::narrow(calc_detail::widen(a) * calc_detail::widen(b)))
        return *r;
    calc_detail::math_error();
}

Rational Calculator::div(const Rational &a, const Rational &b) const {
    calc_detail::require_nonzero(b.frac);
    if (auto r = calc_detail::narrow(calc_detail::widen(a) / calc_detail::widen(b)))
        return *r;
    calc_detail::math_error();
}

Rational Calculator::pow(const Rational &base, const Rational &exp) const {
    // A fractional exponent is a root, and a root is exact only when it comes out
    // rational: 4^(1/2) is 2, while 2^(1/2) is not a rational at all and is left to the
    // float retry above.
    if (exp.denominator() != 1) {
        if (auto r = calc_detail::try_rational_pow(*this, base, exp))
            return *r;
        calc_detail::math_error();
    }

    long long e = exp.numerator();
    calc_detail::require(e >= 0 || base.frac != 0);

    if (e == 0)
        return Rational(1);

    // Repeated squaring below multiplies boost::rational<int64_t>'s own numerator and
    // denominator; with no overflow guard those overflow silently (UB) rather than
    // raising, unlike every sibling that shares this exponentiation (root already
    // guards through try_rational_pow). Same estimator, same threshold.
    if (calc_detail::rational_pow_overflows(base, e))
        calc_detail::math_error();

    bool neg_exp = e < 0;
    if (neg_exp) {
        calc_detail::require_nonzero(base.frac);
        e = -e;
    }

    boost::rational<std::int64_t> result(1);
    boost::rational<std::int64_t> b = base.frac;
    long long rem = e;

    while (rem > 0) {
        if (rem & 1)
            result *= b;
        rem >>= 1;
        if (rem > 0)
            b *= b;
    }

    if (neg_exp) {
        result = boost::rational<std::int64_t>(result.denominator(), result.numerator());
    }

    return Rational(result);
}

Rational Calculator::root(const Rational &a, const Rational &b) const {
    calc_detail::require_nonzero(b.frac);
    const Rational inv(b.denominator(), b.numerator());
    if (auto r = calc_detail::try_rational_pow(*this, a, inv)) {
        return *r;
    }
    calc_detail::math_error();
}

Rational Calculator::sqrt(const Rational &a) const {
    return root(a, Rational(2));
}

Rational Calculator::cbrt(const Rational &a) const {
    return root(a, Rational(3));
}

// -----------------
// Complex
// -----------------

Calculator::Complex Calculator::div(Complex a, Complex b) const {
    calc_detail::require_nonzero(b);
    return a / b;
}

Calculator::Complex Calculator::pow(Complex a, Complex b) const {
    // An integer or a root's exponent takes root's exact steps; exp(b log a) leaves noise.
    if (b.imag() == 0.0) {
        if (const auto m = calc_detail::as_int(b.real()))
            if (const auto r = calc_detail::integer_power(a, *m))
                return *r;
        // A zero base would come back here from root's last step.
        if (const auto n = calc_detail::as_int(1.0 / b.real()); n && a != 0.0)
            return this->root(a, Complex(*n, 0.0));
    }
    return std::pow(a, b);
}

// -----------------
// BigComplex
// -----------------

BigComplex Calculator::div(const BigComplex &a, const BigComplex &b) const {
    calc_detail::require_nonzero(b);
    return a / b;
}

BigComplex Calculator::pow(const BigComplex &a, const BigComplex &b) const {
    // Same steps as the Complex overload.
    if (b.imag() == 0) {
        if (const auto m = calc_detail::as_int(b.real()))
            if (const auto r = calc_detail::integer_power(a, *m))
                return *r;
        if (const auto n = calc_detail::as_int(BigComplex::value_type(1) / b.real()); n && a != 0)
            return this->root(a, BigComplex(*n));
    }
    using boost::multiprecision::pow;
    return pow(a, b);
}
