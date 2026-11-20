/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"
#include "calc/pub/error_messages.hpp"

#include <cmath>
#include <complex>
#include <cstdint>
#include <limits>
#include <string>

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
    return calc_detail::trunc_div(a, b).quot;
}

BigReal Calculator::pow(const BigReal &a, const BigReal &b) const {
    calc_detail::require(b >= 0 || a != 0);
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

std::int64_t Calculator::intdiv(const Rational &a, const Rational &b) const {
    calc_detail::require_nonzero(b.frac);
    const calc_detail::WideRational q = calc_detail::widen(a) / calc_detail::widen(b);
    // int256 division truncates toward zero, as the double and BigReal arms do.
    if (auto r = calc_detail::narrow(calc_detail::WideRational(q.numerator() / q.denominator())))
        return r->numerator();
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

    // The reciprocal of int64 min does not fit int64; div raises the math error the retry reads.
    if (neg_exp)
        return div(Rational(1), Rational(result));

    return Rational(result);
}

Rational Calculator::root(const Rational &a, const Rational &b) const {
    calc_detail::require_nonzero(b.frac);
    const Rational inv = div(Rational(1), b);
    if (auto r = calc_detail::try_rational_pow(*this, a, inv)) {
        return *r;
    }
    calc_detail::math_error();
}

namespace {
/// Half an ulp, relative: past it a result's error can pass 1 ulp.
constexpr double kHalfUlp = std::numeric_limits<double>::epsilon() / 2;

/// n's relative error as a double; 0 up to 2^53. int128 holds the double of int64 max, 2^63.
double cast_loss(std::int64_t n) {
    const auto d = static_cast<double>(n);
    const __int128 lost = static_cast<__int128>(n) - static_cast<__int128>(d);
    return std::fabs(static_cast<double>(lost)) / std::fabs(d);
}

/// pow on the rounded |x| and y, and t, the log of the factor their roundings left out.
struct CorrectedPow {
    double r;
    double t;
};

CorrectedPow corrected_pow(const Rational &x, const Rational &y) {
    // INT64_MIN has no int64 negation; its double has one.
    const double a = std::fabs(static_cast<double>(x.numerator()));
    const auto c = static_cast<double>(x.denominator());
    const auto p = static_cast<double>(y.numerator());
    const auto q = static_cast<double>(y.denominator());
    const double b = a / c;
    const double e = p / q;
    // Both residuals are exact for operands that are doubles; log1p and expm1 keep a base near
    // 1 at a large exponent right, where a first-order term leaves it 9 ulps off.
    const double de = std::fma(-e, q, p) / q;
    const double db = std::fma(-b, c, a) / c;
    const double log_b = std::log(b);
    // The residuals read the rounded operands, so a digit the cast dropped is gone. A base's
    // relative error reaches the result |e| times, the exponent's |e ln b| times.
    const double loss =
        std::fabs(e) * (cast_loss(x.numerator()) + cast_loss(x.denominator())) +
        std::fabs(e * log_b) * (cast_loss(y.numerator()) + cast_loss(y.denominator()));
    if (loss > kHalfUlp)
        throw CalculatorError(std::string(tcalc::errmsg::kNeedsMultiprecision));
    return {.r = std::pow(b, e), .t = de * log_b + e * std::log1p(db / b)};
}
} // namespace

double Calculator::real_power(const Rational &x, const Rational &y) const {
    // A root at an integer degree keeps the real root kernel's correctly rounded result where
    // both the degree and the base are doubles exactly; a rounded quotient a/c leaves 2 ulps.
    const bool base_is_double =
        x.denominator() == 1 && x.numerator() >= -kExactIntLimit && x.numerator() <= kExactIntLimit;
    if (base_is_double && y.numerator() == 1 && y.denominator() <= kExactIntLimit)
        return root(x.to_double(), static_cast<double>(y.denominator()));
    const auto [r, t] = corrected_pow(x, y);
    const double m = std::fma(r, std::expm1(t), r);
    return x.numerator() < 0 && calc_detail::odd_integer(y.numerator()) ? -m : m;
}

Calculator::Complex Calculator::principal_power(const Rational &x, const Rational &y) const {
    const auto [r, t] = corrected_pow(x, y);
    // Each part is rounded to double once; a double product leaves a part 2 or 3 ulps off.
    const long double m = static_cast<long double>(r) +
                          static_cast<long double>(r) * static_cast<long double>(std::expm1(t));
    const auto turns = calc_detail::fold_half_turns<long double>(y);
    // Adding +0 turns the fold's -0 on an axis into +0.
    return {static_cast<double>(m * turns.cos) + 0.0, static_cast<double>(m * turns.sin) + 0.0};
}

Rational Calculator::sqrt(const Rational &a) const {
    return root(a, Rational(kSquare));
}

Rational Calculator::cbrt(const Rational &a) const {
    return root(a, Rational(kCube));
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
