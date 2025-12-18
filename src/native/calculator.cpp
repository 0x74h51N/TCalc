#include "calculator.hpp"

#include <cmath>
#include <complex>
#include <limits>
#include <algorithm>
#include <boost/multiprecision/cpp_dec_float.hpp>
#include <boost/math/constants/constants.hpp>

namespace {

[[noreturn]] void math_error() {
    throw CalculatorError("Math error");
}

inline void require(bool ok) {
    if (!ok) {
        math_error();
    }
}

inline bool int_like(double x, double eps = 1e-12) {
    const double rounded = std::round(x);
    return std::abs(x - rounded) <= eps;
}

inline void require_nonzero(double x) {
    require(x != 0.0);
}

inline void require_nonzero(const BigReal& x) {
    require(x != 0);
}

inline void require_nonzero(Calculator::Complex x) {
    require(!(x.real() == 0.0 && x.imag() == 0.0));
}

inline bool nonneg_or_zero(long long n, long long k) {
    if (n < 0 || k < 0) {
        math_error();
    }
    return n >= k;
}

}  // namespace


// -----------------
// Real ops
// -----------------

double Calculator::div(double a, double b) const {
    require_nonzero(b);
    return a / b;
}

double Calculator::pow(double a, long long b) const {

    require(!(b < 0 && a == 0.0));

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


// -----------------
// Bigreal ops
// -----------------

BigReal Calculator::div(const BigReal& a, const BigReal& b) const {
    require_nonzero(b);

    return a / b;
}

BigReal Calculator::intdiv(double a, double b) const {
    require_nonzero(b);
    BigReal q = BigReal(a) / BigReal(b);
    using boost::multiprecision::floor;
    return floor(q);
}

BigReal Calculator::intdiv(const BigReal& a, const BigReal& b) const {
    require_nonzero(b);
    BigReal q = a / b;
    using boost::multiprecision::floor;
    return floor(q);
}

BigReal Calculator::pow(const BigReal& a, const BigReal& b) const {
    using boost::multiprecision::pow;
    return pow(a, b);
}

BigReal Calculator::sqrt(const BigReal& a) const {
    require(a >= 0);
    using boost::multiprecision::sqrt;
    return sqrt(a);
}

BigReal Calculator::log(const BigReal& a) const {
    require(a > 0);
    using boost::multiprecision::log10;
    return log10(a);
}

BigReal Calculator::ln(const BigReal& a) const {
    require(a > 0);
    using boost::multiprecision::log;
    return log(a);
}

BigReal Calculator::mod(const BigReal& a, const BigReal& b) const {
    require_nonzero(b);
    using boost::multiprecision::fmod;
    return fmod(a, b);
}

BigReal Calculator::root(const BigReal& x, const BigReal& y) const {
    require_nonzero(y);
    require(!(x == 0 && y < 0));

    if (x < 0) {
        using boost::multiprecision::floor;
        const BigReal yi = floor(y);
        require(yi == y);
        using boost::multiprecision::fmod;
        require(fmod(yi, BigReal(2)) != 0);

        return -this->pow(-x, BigReal(1) / y);
    }

    return this->pow(x, BigReal(1) / y);
}

double Calculator::sqrt(double a) const {
    require(a >= 0.0);
    return std::sqrt(a);
}

double Calculator::cbrt(double a) const {
    return std::cbrt(a);
}

double Calculator::root(double x, double y) const {
    require_nonzero(y);
    require(!(x == 0.0 && y < 0.0));

    if (x < 0.0) {
        require(int_like(y));
        const double rounded = std::round(y);
        require(std::fmod(rounded, 2.0) != 0.0);
        return -this->pow(-x, 1.0 / y);
    }

    return this->pow(x, 1.0 / y);
}




// -----------------
// Complex ops
// -----------------

Calculator::Complex Calculator::div(Complex a, Complex b) const {
    require_nonzero(b);
    return a / b;
}

Calculator::Complex Calculator::pow(Complex a, Complex b) const {
    return std::pow(a, b);
}

Calculator::Complex Calculator::sqrt(Complex a) const {
    return std::sqrt(a);
}

Calculator::Complex Calculator::root(Complex x, Complex y) const {
    require_nonzero(y);
    return this->pow(x, 1.0 / y);
}



// -----------------
// Trig ops
// -----------------

namespace {

constexpr double radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = boost::math::constants::pi<double>();
    switch (unit) {
        case Calculator::AngleUnit::DEG:  return pi / 180.0;
        case Calculator::AngleUnit::GRAD: return pi / 200.0;
        case Calculator::AngleUnit::RAD:
        default: return 1.0;
    }
}

constexpr double from_radians_factor(Calculator::AngleUnit unit) noexcept {
    constexpr double pi = boost::math::constants::pi<double>();
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

// -----------------
// Polar
// -----------------

Calculator::Complex Calculator::polar(double a, AngleUnit unit) const {
    const double t = to_radians(a, unit);
    return std::polar(1.0, t);
}

Calculator::Complex Calculator::polar(Complex a, AngleUnit unit) const {
    const Complex t = to_radians(a, unit);
    return std::exp(Complex(0.0, 1.0) * t);
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
    require(a > 0.0);
    return std::log10(a);
}

Calculator::Complex Calculator::log(Complex a) const {
    require_nonzero(a);
    return std::log10(a);
}

double Calculator::ln(double a) const {
    require(a > 0.0);
    return std::log(a);
}

Calculator::Complex Calculator::ln(Complex a) const {
    require_nonzero(a);
    return std::log(a);
}

double Calculator::mod(double a, double b) const {
    require_nonzero(b);
    return std::fmod(a, b);
}


double Calculator::fact(double a) const {
    const double rounded = std::round(a);
    if (!int_like(a) || rounded < 0.0) {
        math_error();
    }

    return std::tgamma(rounded + 1.0);
}

double Calculator::gamma(double a) const {
    if (a <= 0.0 && int_like(a)) {
        math_error();
    }

    return std::tgamma(a);
}


BigReal Calculator::permute(long long a, long long b) const {
    if (!nonneg_or_zero(a, b)) {
        return BigReal(0);
    }

    BigReal res = 1;

    for (long long i=0; i < b; ++i){
        res *= BigReal(a - i);
    }
    return res;
}   


BigReal Calculator::choose(long long a, long long b) const {
    if (!nonneg_or_zero(a, b)) {
        return BigReal(0);
    }

    long long r = std::min(b, a-b);
    BigReal res = 1;

    for (long long i = 1; i <= r; ++i){
        res *= BigReal(a - r + i);
        res /= BigReal(i);
    }

    return res;
}
