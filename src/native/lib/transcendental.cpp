#include "calculator.hpp"
#include "internal/internal.hpp"

#include <cmath>
#include <complex>

#include <boost/multiprecision/cpp_dec_float.hpp>

// -----------------
// Real transcendental ops
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
        calc_detail::require(calc_detail::int_like(y));
        const double rounded = std::round(y);
        calc_detail::require(std::fmod(rounded, 2.0) != 0.0);
        return -this->pow(-x, 1.0 / y);
    }

    return this->pow(x, 1.0 / y);
}

double Calculator::log(double a) const {
    calc_detail::require(a > 0.0);
    return std::log10(a);
}

double Calculator::ln(double a) const {
    calc_detail::require(a > 0.0);
    return std::log(a);
}

// -----------------
// BigReal transcendental ops
// -----------------

BigReal Calculator::sqrt(const BigReal& a) const {
    calc_detail::require(a >= 0);
    using boost::multiprecision::sqrt;
    return sqrt(a);
}

BigReal Calculator::log(const BigReal& a) const {
    calc_detail::require(a > 0);
    using boost::multiprecision::log10;
    return log10(a);
}

BigReal Calculator::ln(const BigReal& a) const {
    calc_detail::require(a > 0);
    using boost::multiprecision::log;
    return log(a);
}

BigReal Calculator::root(const BigReal& x, const BigReal& y) const {
    calc_detail::require_nonzero(y);
    calc_detail::require(!(x == 0 && y < 0));

    if (x < 0) {
        using boost::multiprecision::floor;
        const BigReal yi = floor(y);
        calc_detail::require(yi == y);
        using boost::multiprecision::fmod;
        calc_detail::require(fmod(yi, BigReal(2)) != 0);

        return -this->pow(-x, BigReal(1) / y);
    }

    return this->pow(x, BigReal(1) / y);
}

// -----------------
// Complex transcendental ops
// -----------------

Calculator::Complex Calculator::sqrt(Complex a) const {
    return std::sqrt(a);
}

Calculator::Complex Calculator::root(Complex x, Complex y) const {
    calc_detail::require_nonzero(y);
    return this->pow(x, 1.0 / y);
}

Calculator::Complex Calculator::log(Complex a) const {
    calc_detail::require_nonzero(a);
    return std::log10(a);
}

Calculator::Complex Calculator::ln(Complex a) const {
    calc_detail::require_nonzero(a);
    return std::log(a);
}
