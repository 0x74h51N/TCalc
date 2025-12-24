#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"

#include <algorithm>
#include <cmath>

#include <boost/math/special_functions/gamma.hpp>
#include <boost/multiprecision/cpp_dec_float.hpp>

double Calculator::fact(double a) const {
    const double rounded = std::round(a);
    if (!calc_detail::int_like(a) || rounded < 0.0) {
        calc_detail::math_error();
    }

    return std::tgamma(rounded + 1.0);
}

double Calculator::gamma(double a) const {
    if (a <= 0.0 && calc_detail::int_like(a)) {
        calc_detail::math_error();
    }

    return std::tgamma(a);
}

BigReal Calculator::fact(const BigReal &a) const {
    calc_detail::require(a >= 0);
    using boost::multiprecision::floor;
    calc_detail::require(floor(a) == a);

    using boost::math::tgamma;
    return tgamma(a + 1);
}

BigReal Calculator::gamma(const BigReal &a) const {
    if (a <= 0) {
        using boost::multiprecision::floor;
        if (floor(a) == a) {
            calc_detail::math_error();
        }
    }

    using boost::math::tgamma;
    return tgamma(a);
}

//
// Permute
//
BigReal Calculator::permute(long long a, long long b) const {
    if (!calc_detail::nonneg_or_zero(a, b)) {
        return BigReal(0);
    }

    BigReal res = 1;

    for (long long i = 0; i < b; ++i) {
        res *= BigReal(a - i);
    }
    return res;
}

BigReal Calculator::choose(long long a, long long b) const {
    if (!calc_detail::nonneg_or_zero(a, b)) {
        return BigReal(0);
    }

    long long r = std::min(b, a - b);
    BigReal res = 1;

    for (long long i = 1; i <= r; ++i) {
        res *= BigReal(a - r + i);
        res /= BigReal(i);
    }

    return res;
}
