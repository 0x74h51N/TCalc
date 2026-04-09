/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <pybind11/pybind11.h>

#include <sstream>

#include "bindings.hpp"
#include "types.hpp"

namespace py = pybind11;

void bind_rational(py::module_ &m) {
    py::class_<Rational>(m, "Rational", "Exact rational number (numerator / denominator).")
        .def(py::init<std::int64_t>(), py::arg("n"), "Construct from integer n/1.")
        .def(
            py::init<std::int64_t, std::int64_t>(),
            py::arg("num"),
            py::arg("den"),
            "Construct from numerator/denominator (auto-normalizes via GCD).")
        .def_property_readonly("numerator", &Rational::numerator)
        .def_property_readonly("denominator", &Rational::denominator)
        .def("to_double", &Rational::to_double)
        .def("__neg__", [](const Rational &a) -> Rational { return Rational(-a.frac); })
        .def("__abs__", [](const Rational &a) -> Rational { return Rational(boost::abs(a.frac)); })

        // Display
        .def(
            "__repr__",
            [](const Rational &r) {
                std::ostringstream os;
                os << "Rational(" << r.numerator() << ", " << r.denominator() << ")";
                return os.str();
            })
        .def(
            "__str__",
            [](const Rational &r) {
                std::ostringstream os;
                if (r.denominator() == 1)
                    os << r.numerator();
                else
                    os << r.numerator() << "/" << r.denominator();
                return os.str();
            })
        .def(
            "__hash__",
            [](const Rational &r) {
                auto h1 = std::hash<std::int64_t>{}(r.numerator());
                auto h2 = std::hash<std::int64_t>{}(r.denominator());
                return h1 ^ (h2 << 1);
            })
        .def(
            py::pickle(
                [](const Rational &r) { return py::make_tuple(r.numerator(), r.denominator()); },
                [](const py::tuple &t) -> Rational {
                    if (t.size() != 2)
                        throw std::runtime_error("Invalid Rational state");
                    return Rational(t[0].cast<std::int64_t>(), t[1].cast<std::int64_t>());
                }));
}
