/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"

#include <cmath>
#include <complex>

#include <boost/math/constants/constants.hpp>
#include <boost/multiprecision/cpp_bin_float.hpp>
#include <boost/multiprecision/cpp_complex.hpp>
#include <boost/multiprecision/cpp_dec_float.hpp>

namespace {

constexpr double kDegreesPerCircle = 180.0;
constexpr double kGradsPerCircle = 200.0;

constexpr double radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = boost::math::constants::pi<double>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return pi / kDegreesPerCircle;
    case Calculator::AngleUnit::GRAD:
        return pi / kGradsPerCircle;
    case Calculator::AngleUnit::RAD:
    default:
        return 1.0;
    }
}

constexpr double from_radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = boost::math::constants::pi<double>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return kDegreesPerCircle / pi;
    case Calculator::AngleUnit::GRAD:
        return kGradsPerCircle / pi;
    case Calculator::AngleUnit::RAD:
    default:
        return 1.0;
    }
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
        return pi / BigReal(kDegreesPerCircle);
    case Calculator::AngleUnit::GRAD:
        return pi / BigReal(kGradsPerCircle);
    case Calculator::AngleUnit::RAD:
    default:
        return BigReal(1);
    }
}

inline BigReal from_radians_factor_big(Calculator::AngleUnit unit) {
    const BigReal &pi = boost::math::constants::pi<BigReal>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return BigReal(kDegreesPerCircle) / pi;
    case Calculator::AngleUnit::GRAD:
        return BigReal(kGradsPerCircle) / pi;
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
        return BigComplex(pi / BF(kDegreesPerCircle), BF(0));
    case Calculator::AngleUnit::GRAD:
        return BigComplex(pi / BF(kGradsPerCircle), BF(0));
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
        return BigComplex(BF(kDegreesPerCircle) / pi, BF(0));
    case Calculator::AngleUnit::GRAD:
        return BigComplex(BF(kGradsPerCircle) / pi, BF(0));
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

} // namespace

Calculator::Complex Calculator::polar(double a, AngleUnit unit) const {
    const double t = to_radians(a, unit);
    return std::polar(1.0, t);
}

Calculator::Complex Calculator::polar(Complex a, AngleUnit unit) const {
    const Complex t = to_radians(a, unit);
    return std::exp(Complex(0.0, 1.0) * t);
}

double Calculator::sin(double a, AngleUnit unit) const {
    return std::sin(to_radians(a, unit));
}
double Calculator::cos(double a, AngleUnit unit) const {
    return std::cos(to_radians(a, unit));
}
double Calculator::tan(double a, AngleUnit unit) const {
    return std::tan(to_radians(a, unit));
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
