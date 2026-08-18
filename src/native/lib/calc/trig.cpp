/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"

#include <array>
#include <cmath>
#include <complex>

#include <boost/math/constants/constants.hpp>
#include <boost/multiprecision/cpp_bin_float.hpp>
#include <boost/multiprecision/cpp_complex.hpp>
#include <boost/multiprecision/cpp_dec_float.hpp>
#include <boost/multiprecision/cpp_int.hpp>

namespace {

constexpr double kDegreesPerHalfTurn = 180.0;
constexpr double kGradsPerHalfTurn = 200.0;
constexpr double kDegreesPerFullTurn = 2.0 * kDegreesPerHalfTurn;
constexpr double kGradsPerFullTurn = 2.0 * kGradsPerHalfTurn;

constexpr double radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = boost::math::constants::pi<double>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return pi / kDegreesPerHalfTurn;
    case Calculator::AngleUnit::GRAD:
        return pi / kGradsPerHalfTurn;
    case Calculator::AngleUnit::RAD:
    default:
        return 1.0;
    }
}

constexpr double from_radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = boost::math::constants::pi<double>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return kDegreesPerHalfTurn / pi;
    case Calculator::AngleUnit::GRAD:
        return kGradsPerHalfTurn / pi;
    case Calculator::AngleUnit::RAD:
    default:
        return 1.0;
    }
}

// A full turn in the argument's own unit, or 0 when the unit has no exact one.
constexpr double turn_of(Calculator::AngleUnit unit) noexcept {
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return kDegreesPerFullTurn;
    case Calculator::AngleUnit::GRAD:
        return kGradsPerFullTurn;
    case Calculator::AngleUnit::RAD:
    default:
        return 0.0;
    }
}

// Reduce modulo a full turn before to_radians scales by an inexact factor. Exact in degrees and
// grads (360 and 400 are exact doubles, fmod is exact for finite operands), so nothing is lost.
// Radians have no exact turn to reduce against, and their conversion factor is 1, so no product
// is formed and there is nothing to fix.
inline double reduce_turn(double x, Calculator::AngleUnit unit) noexcept {
    const double turn = turn_of(unit);
    return turn == 0.0 ? x : std::fmod(x, turn);
}

template <typename T> inline T to_radians(T x, Calculator::AngleUnit unit) noexcept {
    return x * radians_factor(unit);
}

template <typename T> inline T from_radians(T x, Calculator::AngleUnit unit) noexcept {
    return x * from_radians_factor(unit);
}

inline BigReal radians_factor_big(Calculator::AngleUnit unit) {
    const BigReal &pi = boost::math::constants::pi<BigReal>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return pi / BigReal(kDegreesPerHalfTurn);
    case Calculator::AngleUnit::GRAD:
        return pi / BigReal(kGradsPerHalfTurn);
    case Calculator::AngleUnit::RAD:
    default:
        return BigReal(1);
    }
}

inline BigReal from_radians_factor_big(Calculator::AngleUnit unit) {
    const BigReal &pi = boost::math::constants::pi<BigReal>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return BigReal(kDegreesPerHalfTurn) / pi;
    case Calculator::AngleUnit::GRAD:
        return BigReal(kGradsPerHalfTurn) / pi;
    case Calculator::AngleUnit::RAD:
    default:
        return BigReal(1);
    }
}

inline BigReal to_radians(const BigReal &x, Calculator::AngleUnit unit) noexcept {
    return x * radians_factor_big(unit);
}

inline BigReal from_radians(const BigReal &x, Calculator::AngleUnit unit) noexcept {
    return x * from_radians_factor_big(unit);
}

inline BigComplex radians_factor_bigcx(Calculator::AngleUnit unit) {
    using BF = boost::multiprecision::cpp_bin_float_50;
    const BF &pi = boost::math::constants::pi<BF>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return BigComplex(pi / BF(kDegreesPerHalfTurn), BF(0));
    case Calculator::AngleUnit::GRAD:
        return BigComplex(pi / BF(kGradsPerHalfTurn), BF(0));
    case Calculator::AngleUnit::RAD:
    default:
        return BigComplex(BF(1), BF(0));
    }
}

inline BigComplex from_radians_factor_bigcx(Calculator::AngleUnit unit) {
    using BF = boost::multiprecision::cpp_bin_float_50;
    const BF &pi = boost::math::constants::pi<BF>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return BigComplex(BF(kDegreesPerHalfTurn) / pi, BF(0));
    case Calculator::AngleUnit::GRAD:
        return BigComplex(BF(kGradsPerHalfTurn) / pi, BF(0));
    case Calculator::AngleUnit::RAD:
    default:
        return BigComplex(BF(1), BF(0));
    }
}

inline BigComplex to_radians(const BigComplex &x, Calculator::AngleUnit unit) {
    return x * radians_factor_bigcx(unit);
}

inline BigComplex from_radians(const BigComplex &x, Calculator::AngleUnit unit) {
    return x * from_radians_factor_bigcx(unit);
}

// Niven's theorem as a table: at a rational multiple of pi the only rational values are
// 0, +-1/2, +-1. Sine and cosine land on them at the twelfths of a turn, tangent at the
// quarters. Entries are doubled so 2 is 1 and 1 is 1/2; kNoExact marks an irrational step.
//
// See: https://en.wikipedia.org/wiki/Niven%27s_theorem
constexpr std::int8_t kNoExact = 127;
constexpr std::int8_t kTanPole = 126;
constexpr std::array<std::int8_t, 12> kSinHalves{
    0, 1, kNoExact, 2, kNoExact, 1, 0, -1, kNoExact, -2, kNoExact, -1};
constexpr std::array<std::int8_t, 12> kCosHalves{
    2, kNoExact, 1, 0, -1, kNoExact, -2, kNoExact, -1, 0, 1, kNoExact};
constexpr std::array<std::int8_t, 4> kTanHalves{0, 2, kTanPole, -2};

} // namespace

// unit is DEG or GRAD: a radian argument's exact case (zero) is resolved by the caller before
// this is ever reached, via the pi-coefficient test in scalar_half_turns, not this conversion.
std::optional<Rational> Calculator::half_turns(const Rational &a, AngleUnit unit) const {
    const auto half = static_cast<std::int64_t>(turn_of(unit) / 2.0); // 180 or 200
    // A denominator coprime to half can overflow int64 once boost multiplies it by half; decline
    // rather than divide into undefined behaviour.
    if (calc_detail::rational_div_overflows(a, half))
        return std::nullopt;
    return Rational(a.frac / boost::rational<std::int64_t>(half));
}

std::optional<Rational> Calculator::exact_half_turns(TrigFn fn, const Rational &t) const {
    const bool is_tan = fn == TrigFn::Tan;
    // t is in half turns, so a step is 1/6 of one for sine and cosine, 1/4 for tangent, and t
    // is on the grid only when its denominator divides that.
    const std::int64_t grid = is_tan ? 4 : 6;
    const std::int64_t period = is_tan ? 4 : 12;
    if (grid % t.denominator() != 0)
        return std::nullopt;
    // Which step t lands on, brought into one period. The modulo before the multiply is what
    // keeps the product small whatever the numerator was.
    std::int64_t k = t.numerator() % period * (grid / t.denominator()) % period;
    if (k < 0)
        k += period;
    const auto idx = static_cast<std::size_t>(k);
    const std::int8_t halves =
        is_tan ? kTanHalves[idx] : (fn == TrigFn::Sin ? kSinHalves[idx] : kCosHalves[idx]);
    if (halves == kTanPole)
        calc_detail::math_error();
    return halves == kNoExact ? std::nullopt : std::optional<Rational>(Rational(halves, 2));
}

// t here has any denominator, not just the small ones exact_half_turns's grid filters for, so
// the int64 fold below can overflow; int64 is still the path taken and int256_t the fallback,
// because a wide-rational route measured 3.3x an int64 one.
//
// Casting num and 2*q to double independently loses the residual exactly when num is close to
// q, so the nearer of num and q - num is what gets cast, at the cost of one more swap.
double Calculator::real_half_turns(TrigFn fn, const Rational &t) const {
    // u = t mod 2 half turns, then quadrant = floor(2u) and num/2q = u - quadrant/2, in [0, 1/2).
    const std::int64_t q = t.denominator();
    std::int64_t quadrant = 0;
    bool upper_half = false;
    double eps =
        0.0; // pi times the fold's residual from whichever quadrant edge is nearer, in [0, pi/4]
    if (!calc_detail::half_turn_fold_overflows(q)) {
        std::int64_t p = t.numerator() % (2 * q);
        if (p < 0)
            p += 2 * q;
        quadrant = (2 * p) / q;                        // 0..3, since 0 <= 2p < 4q
        const std::int64_t num = 2 * p - quadrant * q; // in [0, q)
        upper_half = 2 * num > q;
        const std::int64_t near = upper_half ? q - num : num;
        eps = boost::math::constants::pi<double>() *
              (static_cast<double>(near) / static_cast<double>(2 * q));
    } else {
        using boost::multiprecision::int256_t;
        const int256_t wq(q);
        const int256_t two_q = 2 * wq;
        int256_t p = int256_t(t.numerator()) % two_q;
        if (p < 0)
            p += two_q;
        const int256_t wquadrant = 2 * p / wq; // 0..3, since 0 <= 2p < 4q
        quadrant = static_cast<std::int64_t>(wquadrant);
        const int256_t num = 2 * p - wquadrant * wq; // in [0, q)
        upper_half = 2 * num > wq;
        const int256_t near = upper_half ? wq - num : num;
        eps = boost::math::constants::pi<double>() *
              (near.convert_to<double>() / two_q.convert_to<double>());
    }
    const double s0 = std::sin(eps);
    const double c0 = std::cos(eps);
    // Within a quadrant, sine and cosine are these swapped and sign-changed at the edges; the
    // upper_half swap is the same identity applied a second time, at the finer pi/4 boundary.
    const double s = upper_half ? c0 : s0;
    const double k = upper_half ? s0 : c0;
    const double sin_v = quadrant == 0 ? s : quadrant == 1 ? k : quadrant == 2 ? -s : -k;
    const double cos_v = quadrant == 0 ? k : quadrant == 1 ? -s : quadrant == 2 ? -k : s;
    switch (fn) {
    case TrigFn::Sin:
        return sin_v;
    case TrigFn::Cos:
        return cos_v;
    case TrigFn::Tan:
        break;
    }
    if (cos_v == 0.0)
        calc_detail::math_error();
    return sin_v / cos_v;
}

Calculator::Complex Calculator::polar(double a, AngleUnit unit) const {
    const double t = to_radians(a, unit);
    return std::polar(1.0, t);
}

Calculator::Complex Calculator::polar(Complex a, AngleUnit unit) const {
    const Complex t = to_radians(a, unit);
    return std::exp(Complex(0.0, 1.0) * t);
}

double Calculator::sin(double a, AngleUnit unit) const {
    return std::sin(to_radians(reduce_turn(a, unit), unit));
}
double Calculator::cos(double a, AngleUnit unit) const {
    return std::cos(to_radians(reduce_turn(a, unit), unit));
}
double Calculator::tan(double a, AngleUnit unit) const {
    const double r = reduce_turn(a, unit);
    const double half = turn_of(unit) / 2.0;
    if (half != 0.0) {
        // An odd quarter turn is a pole. Comparing exactly is sound here and only here: in
        // degrees and grads the quarter turn is an exact double, so a value either is one or is
        // not, and there is no epsilon to choose.
        const double m = std::fmod(r, half);
        const double quarter = half / 2.0; // a quarter turn, the pole
        if (m == quarter || m == -quarter)
            calc_detail::math_error();
    }
    return std::tan(to_radians(r, unit));
}

Calculator::Complex Calculator::sin(Complex a, AngleUnit unit) const {
    return std::sin(to_radians(a, unit));
}
Calculator::Complex Calculator::cos(Complex a, AngleUnit unit) const {
    return std::cos(to_radians(a, unit));
}
Calculator::Complex Calculator::tan(Complex a, AngleUnit unit) const {
    return std::tan(to_radians(a, unit));
}

BigReal Calculator::sin(const BigReal &a, AngleUnit unit) const {
    return boost::multiprecision::sin(to_radians(a, unit));
}
BigReal Calculator::cos(const BigReal &a, AngleUnit unit) const {
    return boost::multiprecision::cos(to_radians(a, unit));
}
BigReal Calculator::tan(const BigReal &a, AngleUnit unit) const {
    return boost::multiprecision::tan(to_radians(a, unit));
}

BigComplex Calculator::sin(const BigComplex &a, AngleUnit unit) const {
    return boost::multiprecision::sin(to_radians(a, unit));
}
BigComplex Calculator::cos(const BigComplex &a, AngleUnit unit) const {
    return boost::multiprecision::cos(to_radians(a, unit));
}
BigComplex Calculator::tan(const BigComplex &a, AngleUnit unit) const {
    return boost::multiprecision::tan(to_radians(a, unit));
}

double Calculator::sinh(double a) const {
    return std::sinh(a);
}
double Calculator::cosh(double a) const {
    return std::cosh(a);
}
double Calculator::tanh(double a) const {
    return std::tanh(a);
}

Calculator::Complex Calculator::sinh(Complex a) const {
    return std::sinh(a);
}
Calculator::Complex Calculator::cosh(Complex a) const {
    return std::cosh(a);
}
Calculator::Complex Calculator::tanh(Complex a) const {
    return std::tanh(a);
}

double Calculator::asin(double a, AngleUnit unit) const {
    return from_radians(std::asin(a), unit);
}
double Calculator::acos(double a, AngleUnit unit) const {
    return from_radians(std::acos(a), unit);
}
double Calculator::atan(double a, AngleUnit unit) const {
    return from_radians(std::atan(a), unit);
}

Calculator::Complex Calculator::asin(Complex a, AngleUnit unit) const {
    return from_radians(std::asin(a), unit);
}
Calculator::Complex Calculator::acos(Complex a, AngleUnit unit) const {
    return from_radians(std::acos(a), unit);
}
Calculator::Complex Calculator::atan(Complex a, AngleUnit unit) const {
    return from_radians(std::atan(a), unit);
}

double Calculator::asinh(double a) const {
    return std::asinh(a);
}
double Calculator::acosh(double a) const {
    return std::acosh(a);
}
double Calculator::atanh(double a) const {
    return std::atanh(a);
}

Calculator::Complex Calculator::asinh(Complex a) const {
    return std::asinh(a);
}
Calculator::Complex Calculator::acosh(Complex a) const {
    return std::acosh(a);
}
Calculator::Complex Calculator::atanh(Complex a) const {
    return std::atanh(a);
}
