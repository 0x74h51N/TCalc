#include "calculator.hpp"

#include <cmath>
#include <complex>
#include <numbers>
#include <limits>

// -----------------
// Real ops
// -----------------

double Calculator::div(double a, double b) const {
    if (b == 0.0) {
        throw CalculatorError("Math error");
    }
    return a / b;
}

double Calculator::pow(double a, long long b) const {

    if (b == std::numeric_limits<long long>::min()) {
        throw CalculatorError("Math error");
    }

    if (b < 0 && a == 0.0) {
        throw CalculatorError("Math error");
    }

    long long exp = b;
    double result = 1.0;
    double base = a;

    if (exp < 0) {
        exp = -exp;
        base = 1.0 / base;
    }

    while (exp > 0) {
        if (exp & 1) result *= base;
        base *= base;
        exp >>= 1;
    }

    return result;
}

double Calculator::pow(double a, double b) const {
    
    return std::pow(a, b);
}

double Calculator::sqrt(double a) const {
    if (a < 0.0) {
        throw CalculatorError("Math error");
    }
    return std::sqrt(a);
}

// -----------------
// Complex ops
// -----------------

Calculator::Complex Calculator::div(Complex a, Complex b) const {
    if (b.real() == 0.0 && b.imag() == 0.0) {
        throw CalculatorError("Math error");
    }
    return a / b;
}

Calculator::Complex Calculator::pow(Complex a, Complex b) const {
    return std::pow(a, b);
}

Calculator::Complex Calculator::sqrt(Complex a) const {
    return std::sqrt(a);
}


// -----------------
// Trig ops
// -----------------

namespace {

constexpr double radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = std::numbers::pi_v<double>;
    switch (unit) {
        case Calculator::AngleUnit::DEG:  return pi / 180.0;
        case Calculator::AngleUnit::GRAD: return pi / 200.0;
        case Calculator::AngleUnit::RAD:
        default: return 1.0;
    }
}

constexpr double from_radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = std::numbers::pi_v<double>;
    switch (unit) {
        case Calculator::AngleUnit::DEG:  return 180.0 / pi;
        case Calculator::AngleUnit::GRAD: return 200.0 / pi;
        case Calculator::AngleUnit::RAD:
        default: return 1.0;
    }
}

template <typename T>
inline T to_radians(T x, Calculator::AngleUnit unit) noexcept {
    return x * radians_factor(unit);
}

template <typename T>
inline T from_radians(T x, Calculator::AngleUnit unit) noexcept {
    return x * from_radians_factor(unit);
}

} 

// Real trig
double Calculator::sin(double a, AngleUnit unit) const { return std::sin(to_radians(a, unit)); }
double Calculator::cos(double a, AngleUnit unit) const { return std::cos(to_radians(a, unit)); }
double Calculator::tan(double a, AngleUnit unit) const { return std::tan(to_radians(a, unit)); }

// Complex trig
Calculator::Complex Calculator::sin(Complex a, AngleUnit unit) const { return std::sin(to_radians(a, unit)); }
Calculator::Complex Calculator::cos(Complex a, AngleUnit unit) const { return std::cos(to_radians(a, unit)); }
Calculator::Complex Calculator::tan(Complex a, AngleUnit unit) const { return std::tan(to_radians(a, unit)); }

// Hyperbolic trig
double Calculator::sinh(double a) const { return std::sinh(a); }
double Calculator::cosh(double a) const { return std::cosh(a); }
double Calculator::tanh(double a) const { return std::tanh(a); }

Calculator::Complex Calculator::sinh(Complex a) const { return std::sinh(a); }
Calculator::Complex Calculator::cosh(Complex a) const { return std::cosh(a); }
Calculator::Complex Calculator::tanh(Complex a) const { return std::tanh(a); }


// Inverse trig
double Calculator::asin(double a, AngleUnit unit) const { return from_radians(std::asin(a), unit); }
double Calculator::acos(double a, AngleUnit unit) const { return from_radians(std::acos(a), unit); }
double Calculator::atan(double a, AngleUnit unit) const { return from_radians(std::atan(a), unit); }

Calculator::Complex Calculator::asin(Complex a, AngleUnit unit) const { return from_radians(std::asin(a), unit); }
Calculator::Complex Calculator::acos(Complex a, AngleUnit unit) const { return from_radians(std::acos(a), unit); }
Calculator::Complex Calculator::atan(Complex a, AngleUnit unit) const { return from_radians(std::atan(a), unit); }

// Hyperbolic inverse trig
double Calculator::asinh(double a) const { return std::asinh(a); }
double Calculator::acosh(double a) const { return std::acosh(a); }
double Calculator::atanh(double a) const { return std::atanh(a); }

Calculator::Complex Calculator::asinh(Complex a) const { return std::asinh(a); }
Calculator::Complex Calculator::acosh(Complex a) const { return std::acosh(a); }
Calculator::Complex Calculator::atanh(Complex a) const { return std::atanh(a); }



// Log ops
double Calculator::log(double a) const {
    if (a <= 0.0) {
        throw CalculatorError("Math error");
    }
    return std::log10(a);
}

Calculator::Complex Calculator::log(Complex a) const {
    if (a == 0.0) {
        throw CalculatorError("Math error");
    }
    return std::log10(a);
}

double Calculator::ln(double a) const {
    if (a <= 0.0) {
        throw CalculatorError("Math error");
    }
    return std::log(a);
}

Calculator::Complex Calculator::ln(Complex a) const {
    if (a == 0.0) {
        throw CalculatorError("Math error");
    }
    return std::log(a);
}

double Calculator::mod(double a, double b) const {
    if (b == 0.0) {
        throw CalculatorError("Math error");
    }
    return std::fmod(a, b);
}
