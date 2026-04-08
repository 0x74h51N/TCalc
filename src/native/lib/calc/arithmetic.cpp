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
    const BigReal q = a / b;
    using boost::multiprecision::ceil;
    using boost::multiprecision::floor;
    if (q < 0) {
        return ceil(q);
    }
    return floor(q);
}

BigReal Calculator::pow(const BigReal &a, const BigReal &b) const {
    calc_detail::require(b >= 0 || a != 0);
    using boost::multiprecision::pow;
    return pow(a, b);
}

BigReal Calculator::mod(const BigReal &a, const BigReal &b) const {
    calc_detail::require_nonzero(b);
    using boost::multiprecision::fmod;
    return fmod(a, b);
}

BigReal Calculator::trunc(const BigReal &a) const {
    using boost::multiprecision::trunc;
    return trunc(a);
}

BigReal Calculator::floor(const BigReal &a) const {
    using boost::multiprecision::floor;
    return floor(a);
}

BigReal Calculator::ceil(const BigReal &a) const {
    using boost::multiprecision::ceil;
    return ceil(a);
}

// -----------------
// Rational
// -----------------

Rational Calculator::add(const Rational &a, const Rational &b) const {
    return Rational(a.frac + b.frac);
}

Rational Calculator::sub(const Rational &a, const Rational &b) const {
    return Rational(a.frac - b.frac);
}

Rational Calculator::mul(const Rational &a, const Rational &b) const {
    return Rational(a.frac * b.frac);
}

Rational Calculator::div(const Rational &a, const Rational &b) const {
    calc_detail::require_nonzero(b.frac);
    return Rational(a.frac / b.frac);
}

Rational Calculator::pow(const Rational &base, const Rational &exp) const {
    calc_detail::require(exp.denominator() == 1);

    long long e = exp.numerator();
    calc_detail::require(e >= 0 || base.frac != 0);

    if (e == 0)
        return Rational(1);

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

// -----------------
// Complex
// -----------------

Calculator::Complex Calculator::div(Complex a, Complex b) const {
    calc_detail::require_nonzero(b);
    return a / b;
}

Calculator::Complex Calculator::pow(Complex a, Complex b) const {
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
    using boost::multiprecision::pow;
    return pow(a, b);
}
