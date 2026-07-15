/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <pybind11/pybind11.h>

#include <cmath>
#include <utility>
#include "calc/internal/helpers.hpp"
#include "parser/pub/parser.hpp"
#include "types.hpp"
#include "calc/pub/calculator.hpp"

namespace py = pybind11;
namespace p = tcalc::parser;

// Python binding declarations for calculator native extension
void bind_bigreal(pybind11::module_ &m);
void bind_bigcomplex(pybind11::module_ &m);
void bind_rational(pybind11::module_ &m);
void bind_angle_unit(pybind11::module_ &m);
void bind_parser(pybind11::module_ &m);
void bind_collection(pybind11::module_ &m);
void bind_eval(pybind11::module_ &m);

namespace detail {
inline constexpr int kPythonPrecision = 16;
} // namespace detail

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
