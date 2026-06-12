/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <pybind11/complex.h>
#include <pybind11/pybind11.h>

#include <boost/math/constants/constants.hpp>

#include "bindings.hpp"
#include "calc/pub/calculator.hpp"

namespace py = pybind11;

PYBIND11_MODULE(calc_native, m) {
    m.doc() = "Calculator core exposed from C++ via pybind11";
    py::register_exception<CalculatorError>(m, "CalculatorError");

    bind_bigreal(m);
    bind_bigcomplex(m);
    bind_rational(m);

    using Z = Calculator::Complex;
    using D = double;
    m.attr("pi") = py::float_(boost::math::constants::pi<D>());
    m.attr("e") = py::float_(boost::math::constants::e<D>());
    m.attr("φ") = py::float_(boost::math::constants::phi<D>());
    m.attr("i") = py::cast(Z(0.0, 1.0));

    bind_angle_unit(m);
    // Collection must register before Calculator: the reduction methods
    // (mean/min/max/median) take/return Collection, so its py type must exist
    // when those signatures are bound (else stubgen emits raw C++ types).
    bind_collection(m);
    bind_calculator(m);
    bind_parser(m);
}
