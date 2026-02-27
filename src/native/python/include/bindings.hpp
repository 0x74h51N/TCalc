/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <pybind11/pybind11.h>

#include <cmath>
#include <utility>
#include "parser/pub/parser.hpp"

namespace py = pybind11;
namespace p = tcalc::parser;

// Python binding declarations for calculator native extension
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

template <typename Class, typename Member>
py::class_<Class> &def_readonly_ref(py::class_<Class> &c, const char *name, Member Class::*member) {
    c.def_property_readonly(
        name,
        [member](Class &self) -> const Member & { return self.*member; },
        py::return_value_policy::reference_internal);

    return c;
}
template <typename Class, typename T>
py::class_<Class> &
def_readonly_ref(py::class_<Class> &c, const char *name, std::vector<T> Class::*member) {
    c.def_property_readonly(
        name,
        [member](Class &self) -> const std::vector<T> & { return self.*member; },
        py::return_value_policy::reference_internal);

    return c;
}

template <typename T> const T *token_as(const p::Token &tok) {
    return std::get_if<T>(&tok.data);
}
