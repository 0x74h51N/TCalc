#pragma once

#include <cmath>

#include "calc/pub/calculator.hpp"

namespace calc_detail {

[[noreturn]] inline void math_error() {
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

inline void require_nonzero(const BigReal &x) {
    require(x != 0);
}

inline void require_nonzero(Calculator::Complex x) {
    require(!(x.real() == 0.0 && x.imag() == 0.0));
}

inline void require_nonzero(const BigComplex &x) {
    using boost::multiprecision::backends::eval_is_zero;
    const auto &re = x.backend().real_data();
    const auto &im = x.backend().imag_data();
    require(!(eval_is_zero(re) && eval_is_zero(im)));
}

inline bool nonneg_or_zero(long long n, long long k) {
    if (n < 0 || k < 0) {
        math_error();
    }
    return n >= k;
}

} // namespace calc_detail
