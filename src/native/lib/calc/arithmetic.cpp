#include "calc/internal/calculator.hpp"
#include "calc/internal/helpers.hpp"

#include <cmath>
#include <complex>
#include <limits>

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
    return std::pow(a, b);
}

long long Calculator::intdiv(double a, double b) const {

    calc_detail::require_nonzero(b);
    return static_cast<long long>(a / b);
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
    using boost::multiprecision::pow;
    return pow(a, b);
}

BigReal Calculator::mod(const BigReal &a, const BigReal &b) const {
    calc_detail::require_nonzero(b);
    using boost::multiprecision::fmod;
    return fmod(a, b);
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
