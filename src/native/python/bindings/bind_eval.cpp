/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

// The evaluation surface Python calls. `evaluate` takes a whole row and returns its value,
// so an expression crosses the boundary once. `apply` runs a single operation, for the
// memory keys, which have a value but no row. `clear_vars` empties the native session
// store, which owns every variable an assignment binds.

#include <pybind11/complex.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <utility>
#include <vector>

#include "bindings.hpp"
#include "calc/pub/calculator.hpp"
#include "calc/pub/errors.hpp"
#include "eval/pub/eval.hpp"
#include "eval/pub/varstore.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"
#include "value.hpp"

namespace py = pybind11;

namespace {

// module.cpp's translator can only carry the message. The kind is attached here, at the
// catch site, rather than by a second module-wide translator.
[[noreturn]] void raise_with_kind(const py::module_ &m, const CalculatorError &e) {
    py::object exc_type = m.attr("CalculatorError");
    py::object exc = exc_type(e.what());
    exc.attr("kind") = py::cast(e.kind());
    py::set_error(exc_type, exc);
    throw py::error_already_set();
}

} // namespace

void bind_eval(py::module_ &m) {
    // The calculator is an opaque handle now: it carries no state Python reads and the
    // evaluator does the arithmetic. apply and evaluate take one, the app constructs one.
    py::class_<Calculator>(m, "Calculator").def(py::init<>());

    py::enum_<ErrorKind>(m, "ErrorKind")
        .value("Invalid", ErrorKind::Invalid)
        .value("Malformed", ErrorKind::Malformed)
        .value("MathErr", ErrorKind::MathErr);

    m.def(
        "apply",
        [m](const Calculator &calc,
            tcalc::ops::OpId id,
            std::vector<tcalc::Value> args,
            Calculator::AngleUnit unit) -> tcalc::Value {
            try {
                return tcalc::eval::apply(calc, id, std::move(args), unit);
            } catch (const CalculatorError &e) {
                raise_with_kind(m, e);
            }
        },
        py::arg("calculator"),
        py::arg("op_id"),
        py::arg("args"),
        py::arg("unit"));

    m.def(
        "evaluate",
        [m](const tcalc::parser::TokensBranch &branch,
            const Calculator &calc,
            Calculator::AngleUnit unit) -> tcalc::Value {
            try {
                return tcalc::eval::evaluate(branch, calc, unit);
            } catch (const CalculatorError &e) {
                raise_with_kind(m, e);
            }
        },
        py::arg("branch"),
        py::arg("calculator"),
        py::arg("unit"));

    m.def("clear_vars", [] { tcalc::eval::session_vars().clear(); });
}
