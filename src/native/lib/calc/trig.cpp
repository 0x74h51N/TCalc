#include "calc/internal/calculator.hpp"

#include <cmath>
#include <complex>

#include <boost/math/constants/constants.hpp>

namespace {

constexpr double radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = boost::math::constants::pi<double>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return pi / 180.0;
    case Calculator::AngleUnit::GRAD:
        return pi / 200.0;
    case Calculator::AngleUnit::RAD:
    default:
        return 1.0;
    }
}

constexpr double from_radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = boost::math::constants::pi<double>();
    switch (unit) {
    case Calculator::AngleUnit::DEG:
        return 180.0 / pi;
    case Calculator::AngleUnit::GRAD:
        return 200.0 / pi;
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
