#pragma once

#include <pybind11/pybind11.h>

#include <cmath>

void bind_bigreal(pybind11::module_& m);
void bind_angle_unit(pybind11::module_& m);
void bind_calculator(pybind11::module_& m);

template <typename BigFn>
inline pybind11::object promote_inf_to_big(double r, BigFn&& big_fn) {
    if (!std::isinf(r)) {
        return pybind11::float_(r);
    }
    return pybind11::cast(big_fn());
}
