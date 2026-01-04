#pragma once

#include <pybind11/pybind11.h>

#include <cmath>
#include <utility>

void bind_bigreal(pybind11::module_ &m);
void bind_bigcomplex(pybind11::module_ &m);
void bind_angle_unit(pybind11::module_ &m);
void bind_calculator(pybind11::module_ &m);
void bind_parser(pybind11::module_ &m);

inline bool pow_to_big(double base, double exp, bool exp_is_int) {
    const double base_mag = std::fabs(base);
    if (!std::isfinite(base) || !std::isfinite(exp) || exp == 0.0 || base == 0.0 ||
        base_mag == 1.0 || (base < 0.0 && !exp_is_int)) {
        return false;
    }

    if (base_mag == 10.0 && exp_is_int && std::fabs(exp) >= 308.0) {
        return true;
    }

    const double log10_mag = exp * std::log10(base_mag);
    return log10_mag > 308.0 || log10_mag < -324.0;
}

template <typename BigFn> inline pybind11::object promote_inf_to_big(double r, BigFn &&big_fn) {
    if (!std::isinf(r)) {
        return pybind11::float_(r);
    }
    return pybind11::cast(std::forward<BigFn>(big_fn)());
}
