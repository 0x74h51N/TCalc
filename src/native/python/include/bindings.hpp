#pragma once

#include <pybind11/pybind11.h>

#include <cmath>
#include <utility>

void bind_bigreal(pybind11::module_ &m);
void bind_bigcomplex(pybind11::module_ &m);
void bind_angle_unit(pybind11::module_ &m);
void bind_calculator(pybind11::module_ &m);
void bind_parser(pybind11::module_ &m);

namespace detail {
inline constexpr int kPythonPrecision = 16;
inline constexpr double kPowToBigUp = 308.0;
inline constexpr double kPowToBigLow = -324.0;
inline constexpr double kBaseTen = 10.0;
} // namespace detail

inline bool pow_to_big(double base, double exp, bool exp_is_int) {
    const double base_mag = std::fabs(base);

    if (base_mag == detail::kBaseTen && exp_is_int && std::fabs(exp) >= detail::kPowToBigUp) {
        return true;
    }

    const double log10_mag = exp * std::log10(base_mag);
    if (log10_mag > detail::kPowToBigUp || log10_mag < detail::kPowToBigLow) {
        return true;
    }
    return false;
}

template <typename BigFn> inline pybind11::object promote_inf_to_big(double r, BigFn &&big_fn) {
    if (!std::isinf(r)) {
        return pybind11::float_(r);
    }
    return pybind11::cast(std::forward<BigFn>(big_fn)());
}
