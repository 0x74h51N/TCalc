/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <pybind11/complex.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cmath>

#include "bindings.hpp"
#include "calc/pub/calculator.hpp"

namespace py = pybind11;

void bind_calculator(py::module_ &m) {
    using C = Calculator;
    using Z = Calculator::Complex;
    using B = BigReal;
    using BC = BigComplex;
    using R = Rational;
    using U = Calculator::AngleUnit;

    py::class_<C> cls(m, "Calculator");
    cls.def(py::init<>());

    cls.def(
        "add", py::overload_cast<double, double>(&C::add, py::const_), py::arg("a"), py::arg("b"));
    cls.def(
        "add",
        py::overload_cast<Z, Z>(&C::add, py::const_),
        py::arg("a").noconvert(),
        py::arg("b").noconvert());
    cls.def(
        "add",
        py::overload_cast<const B &, const B &>(&C::add, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "add",
        py::overload_cast<const BC &, const BC &>(&C::add, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "add",
        py::overload_cast<const R &, const R &>(&C::add, py::const_),
        py::arg("a"),
        py::arg("b"));

    cls.def(
        "sub", py::overload_cast<double, double>(&C::sub, py::const_), py::arg("a"), py::arg("b"));
    cls.def(
        "sub",
        py::overload_cast<Z, Z>(&C::sub, py::const_),
        py::arg("a").noconvert(),
        py::arg("b").noconvert());
    cls.def(
        "sub",
        py::overload_cast<const B &, const B &>(&C::sub, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "sub",
        py::overload_cast<const BC &, const BC &>(&C::sub, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "sub",
        py::overload_cast<const R &, const R &>(&C::sub, py::const_),
        py::arg("a"),
        py::arg("b"));

    cls.def(
        "mul",
        [](const C &calc, double a, double b) -> py::object {
            const double r = calc.mul(a, b);
            return promote_inf_to_big(r, [&] { return calc.mul(B(a), B(b)); });
        },
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "mul",
        py::overload_cast<Z, Z>(&C::mul, py::const_),
        py::arg("a").noconvert(),
        py::arg("b").noconvert());
    cls.def(
        "mul",
        py::overload_cast<const B &, const B &>(&C::mul, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "mul",
        py::overload_cast<const BC &, const BC &>(&C::mul, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "mul",
        py::overload_cast<const R &, const R &>(&C::mul, py::const_),
        py::arg("a"),
        py::arg("b"));

    cls.def(
        "div",
        [](const C &calc, double a, double b) -> py::object {
            const double r = calc.div(a, b);
            return promote_inf_to_big(r, [&] { return calc.div(B(a), B(b)); });
        },
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "div",
        py::overload_cast<Z, Z>(&C::div, py::const_),
        py::arg("a").noconvert(),
        py::arg("b").noconvert());
    cls.def(
        "div",
        py::overload_cast<const B &, const B &>(&C::div, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "div",
        py::overload_cast<const BC &, const BC &>(&C::div, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "div",
        py::overload_cast<const R &, const R &>(&C::div, py::const_),
        py::arg("a"),
        py::arg("b"));

    cls.def(
        "intdiv",
        py::overload_cast<double, double>(&C::intdiv, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "intdiv",
        py::overload_cast<const B &, const B &>(&C::intdiv, py::const_),
        py::arg("a"),
        py::arg("b"));

    cls.def(
        "mod", py::overload_cast<double, double>(&C::mod, py::const_), py::arg("a"), py::arg("b"));
    cls.def(
        "mod",
        py::overload_cast<const B &, const B &>(&C::mod, py::const_),
        py::arg("a"),
        py::arg("b"));

    cls.def(
        "pow",
        [](const C &calc, double a, long long b) -> py::object {
            if (pow_to_big(a, static_cast<double>(b), true)) {
                return py::cast(calc.pow(B(a), B(b)));
            }

            return py::float_(calc.pow(a, b));
        },
        py::arg("a"),
        py::arg("b"));

    cls.def(
        "pow",
        [](const C &calc, double a, double b) -> py::object {
            const bool exp_is_int = std::trunc(b) == b;
            if (pow_to_big(a, b, exp_is_int)) {
                return py::cast(calc.pow(B(a), B(b)));
            }

            return py::float_(calc.pow(a, b));
        },
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "pow",
        py::overload_cast<Z, Z>(&C::pow, py::const_),
        py::arg("a").noconvert(),
        py::arg("b").noconvert());

    cls.def(
        "pow",
        py::overload_cast<const B &, const B &>(&C::pow, py::const_),
        py::arg("a"),
        py::arg("b"));

    cls.def(
        "pow",
        py::overload_cast<const BC &, const BC &>(&C::pow, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "pow",
        [](const C &calc, const R &a, const R &b) -> py::object {
            return rational_pow(calc, a, b);
        },
        py::arg("a"),
        py::arg("b"));

    cls.def("trunc", py::overload_cast<double>(&C::trunc, py::const_), py::arg("a"));
    cls.def("trunc", py::overload_cast<const B &>(&C::trunc, py::const_), py::arg("a"));
    cls.def("floor", py::overload_cast<double>(&C::floor, py::const_), py::arg("a"));
    cls.def("floor", py::overload_cast<const B &>(&C::floor, py::const_), py::arg("a"));
    cls.def("ceil", py::overload_cast<double>(&C::ceil, py::const_), py::arg("a"));
    cls.def("ceil", py::overload_cast<const B &>(&C::ceil, py::const_), py::arg("a"));

    cls.def("sqrt", py::overload_cast<double>(&C::sqrt, py::const_), py::arg("a"));
    cls.def("sqrt", py::overload_cast<Z>(&C::sqrt, py::const_), py::arg("a").noconvert());
    cls.def("sqrt", py::overload_cast<const B &>(&C::sqrt, py::const_), py::arg("a"));
    cls.def("sqrt", py::overload_cast<const BC &>(&C::sqrt, py::const_), py::arg("a"));
    cls.def(
        "sqrt",
        [](const C &calc, const R &a) -> py::object { return rational_root(calc, a, R(2)); },
        py::arg("a"));

    cls.def("cbrt", py::overload_cast<double>(&C::cbrt, py::const_), py::arg("a"));
    cls.def(
        "cbrt",
        [](const C &calc, const R &a) -> py::object { return rational_root(calc, a, R(3)); },
        py::arg("a"));
    cls.def(
        "root",
        py::overload_cast<double, double>(&C::root, py::const_),
        py::arg("a"),
        py::arg("b"));

    cls.def(
        "root",
        py::overload_cast<Z, Z>(&C::root, py::const_),
        py::arg("a").noconvert(),
        py::arg("b").noconvert());
    cls.def(
        "root",
        py::overload_cast<const B &, const B &>(&C::root, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "root",
        py::overload_cast<const BC &, const BC &>(&C::root, py::const_),
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "root",
        [](const C &calc, const R &a, const R &b) -> py::object {
            return rational_root(calc, a, b);
        },
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "sin", py::overload_cast<double, U>(&C::sin, py::const_), py::arg("a"), py::arg("unit"));
    cls.def(
        "sin",
        py::overload_cast<Z, U>(&C::sin, py::const_),
        py::arg("a").noconvert(),
        py::arg("unit"));
    cls.def(
        "sin", py::overload_cast<const B &, U>(&C::sin, py::const_), py::arg("a"), py::arg("unit"));
    cls.def(
        "sin",
        py::overload_cast<const BC &, U>(&C::sin, py::const_),
        py::arg("a"),
        py::arg("unit"));
    cls.def(
        "cos", py::overload_cast<double, U>(&C::cos, py::const_), py::arg("a"), py::arg("unit"));
    cls.def(
        "cos",
        py::overload_cast<Z, U>(&C::cos, py::const_),
        py::arg("a").noconvert(),
        py::arg("unit"));
    cls.def(
        "cos", py::overload_cast<const B &, U>(&C::cos, py::const_), py::arg("a"), py::arg("unit"));
    cls.def(
        "cos",
        py::overload_cast<const BC &, U>(&C::cos, py::const_),
        py::arg("a"),
        py::arg("unit"));
    cls.def(
        "tan", py::overload_cast<double, U>(&C::tan, py::const_), py::arg("a"), py::arg("unit"));
    cls.def(
        "tan",
        py::overload_cast<Z, U>(&C::tan, py::const_),
        py::arg("a").noconvert(),
        py::arg("unit"));
    cls.def(
        "tan", py::overload_cast<const B &, U>(&C::tan, py::const_), py::arg("a"), py::arg("unit"));
    cls.def(
        "tan",
        py::overload_cast<const BC &, U>(&C::tan, py::const_),
        py::arg("a"),
        py::arg("unit"));

    cls.def("sinh", py::overload_cast<double>(&C::sinh, py::const_), py::arg("a"));
    cls.def("sinh", py::overload_cast<Z>(&C::sinh, py::const_), py::arg("a").noconvert());
    cls.def("cosh", py::overload_cast<double>(&C::cosh, py::const_), py::arg("a"));
    cls.def("cosh", py::overload_cast<Z>(&C::cosh, py::const_), py::arg("a").noconvert());
    cls.def("tanh", py::overload_cast<double>(&C::tanh, py::const_), py::arg("a"));
    cls.def("tanh", py::overload_cast<Z>(&C::tanh, py::const_), py::arg("a").noconvert());

    cls.def(
        "asin", py::overload_cast<double, U>(&C::asin, py::const_), py::arg("a"), py::arg("unit"));
    cls.def(
        "asin",
        py::overload_cast<Z, U>(&C::asin, py::const_),
        py::arg("a").noconvert(),
        py::arg("unit"));
    cls.def(
        "acos", py::overload_cast<double, U>(&C::acos, py::const_), py::arg("a"), py::arg("unit"));
    cls.def(
        "acos",
        py::overload_cast<Z, U>(&C::acos, py::const_),
        py::arg("a").noconvert(),
        py::arg("unit"));
    cls.def(
        "atan", py::overload_cast<double, U>(&C::atan, py::const_), py::arg("a"), py::arg("unit"));
    cls.def(
        "atan",
        py::overload_cast<Z, U>(&C::atan, py::const_),
        py::arg("a").noconvert(),
        py::arg("unit"));

    cls.def("asinh", py::overload_cast<double>(&C::asinh, py::const_), py::arg("a"));
    cls.def("asinh", py::overload_cast<Z>(&C::asinh, py::const_), py::arg("a").noconvert());
    cls.def("acosh", py::overload_cast<double>(&C::acosh, py::const_), py::arg("a"));
    cls.def("acosh", py::overload_cast<Z>(&C::acosh, py::const_), py::arg("a").noconvert());
    cls.def("atanh", py::overload_cast<double>(&C::atanh, py::const_), py::arg("a"));
    cls.def("atanh", py::overload_cast<Z>(&C::atanh, py::const_), py::arg("a").noconvert());

    cls.def(
        "polar",
        py::overload_cast<double, U>(&C::polar, py::const_),
        py::arg("a"),
        py::arg("unit"));
    cls.def(
        "polar",
        py::overload_cast<Z, U>(&C::polar, py::const_),
        py::arg("a").noconvert(),
        py::arg("unit"));

    cls.def("log", py::overload_cast<double>(&C::log, py::const_), py::arg("a"));
    cls.def("log", py::overload_cast<Z>(&C::log, py::const_), py::arg("a").noconvert());
    cls.def("log", py::overload_cast<const B &>(&C::log, py::const_), py::arg("a"));
    cls.def("log", py::overload_cast<const BC &>(&C::log, py::const_), py::arg("a"));

    cls.def("ln", py::overload_cast<double>(&C::ln, py::const_), py::arg("a"));
    cls.def("ln", py::overload_cast<Z>(&C::ln, py::const_), py::arg("a").noconvert());
    cls.def("ln", py::overload_cast<const B &>(&C::ln, py::const_), py::arg("a"));
    cls.def("ln", py::overload_cast<const BC &>(&C::ln, py::const_), py::arg("a"));

    cls.def(
        "fact",
        [](const C &calc, double a) -> py::object {
            const double r = calc.fact(a);
            return promote_inf_to_big(r, [&] { return calc.fact(B(a)); });
        },
        py::arg("a"));
    cls.def("fact", py::overload_cast<const B &>(&C::fact, py::const_), py::arg("a"));

    cls.def(
        "gamma",
        [](const C &calc, double a) -> py::object {
            const double r = calc.gamma(a);
            return promote_inf_to_big(r, [&] { return calc.gamma(B(a)); });
        },
        py::arg("a"));
    cls.def("gamma", py::overload_cast<const B &>(&C::gamma, py::const_), py::arg("a"));

    cls.def("permute", &C::permute, py::arg("n"), py::arg("r"));
    cls.def("choose", &C::choose, py::arg("n"), py::arg("r"));

    // GCD / LCM
    cls.def(
        "gcd",
        [](const C &calc, long long a, long long b) { return calc.gcd(a, b); },
        py::arg("a"),
        py::arg("b"));
    cls.def(
        "lcm",
        [](const C &calc, long long a, long long b) { return calc.lcm(a, b); },
        py::arg("a"),
        py::arg("b"));

    // Collection reductions
    cls.def("mean", &C::mean, py::arg("a"));
    cls.def("min", &C::min, py::arg("a"));
    cls.def("max", &C::max, py::arg("a"));
    cls.def("median", &C::median, py::arg("a"));
}
