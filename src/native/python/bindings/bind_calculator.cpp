#include <pybind11/complex.h>
#include <pybind11/pybind11.h>

#include <cmath>

#include "bindings.hpp"
#include "calculator.hpp"

namespace py = pybind11;

void bind_calculator(py::module_& m) {
    using C = Calculator;
    using Z = Calculator::Complex;
    using B = BigReal;
    using U = Calculator::AngleUnit;

// Bind helpers
#define DEF_BIN_OP(name) \
    .def(#name, py::overload_cast<double, double>(&C::name, py::const_), py::arg("a"), py::arg("b")) \
    .def(#name, py::overload_cast<Z, Z>(&C::name, py::const_), py::arg("a"), py::arg("b"))

#define DEF_REAL_BIN_OP(name) \
    .def(#name, py::overload_cast<double, double>(&C::name, py::const_), py::arg("a"), py::arg("b"))

#define DEF_BIG_BIN_OP(name) \
    .def(#name, py::overload_cast<const B&, const B&>(&C::name, py::const_), py::arg("a"), py::arg("b"))

#define DEF_REAL_UNARY_OP(name) \
    .def(#name, py::overload_cast<double>(&C::name, py::const_), py::arg("a"))

#define DEF_BIG_UNARY_OP(name) \
    .def(#name, py::overload_cast<const B&>(&C::name, py::const_), py::arg("a"))

#define DEF_UNARY_OP(name) \
    .def(#name, py::overload_cast<double>(&C::name, py::const_), py::arg("a")) \
    .def(#name, py::overload_cast<Z>(&C::name, py::const_), py::arg("a"))

#define DEF_UNARY_UNIT_OP(name) \
    .def(#name, py::overload_cast<double, U>(&C::name, py::const_), py::arg("a"), py::arg("unit")) \
    .def(#name, py::overload_cast<Z, U>(&C::name, py::const_), py::arg("a"), py::arg("unit"))

    py::class_<C>(m, "Calculator")
        .def(py::init<>())
        DEF_BIN_OP(add)
        DEF_BIG_BIN_OP(add)
        DEF_BIN_OP(sub)
        DEF_BIG_BIN_OP(sub)
        .def(
            "mul",
            [](const C& calc, double a, double b) -> py::object {
                const double r = calc.mul(a, b);
                return promote_inf_to_big(r, [&] { return calc.mul(B(a), B(b)); });
            },
            py::arg("a"),
            py::arg("b")
        )
        .def("mul", py::overload_cast<Z, Z>(&C::mul, py::const_), py::arg("a"), py::arg("b"))
        .def("mul", py::overload_cast<const B&, const B&>(&C::mul, py::const_), py::arg("a"), py::arg("b"))
        .def(
            "div",
            [](const C& calc, double a, double b) -> py::object {
                const double r = calc.div(a, b);
                return promote_inf_to_big(r, [&] { return calc.div(B(a), B(b)); });
            },
            py::arg("a"),
            py::arg("b")
        )
        .def("div", py::overload_cast<Z, Z>(&C::div, py::const_), py::arg("a"), py::arg("b"))
        .def("div", py::overload_cast<const B&, const B&>(&C::div, py::const_), py::arg("a"), py::arg("b"))
        DEF_REAL_BIN_OP(intdiv)
        DEF_BIG_BIN_OP(intdiv)
        DEF_REAL_BIN_OP(mod)
        DEF_BIG_BIN_OP(mod)
        .def(
            "pow",
            [](const C& calc, double a, long long b) -> py::object {
                const double r = calc.pow(a, b);
                return promote_inf_to_big(r, [&] { return calc.pow(B(a), B(b)); });
            },
            py::arg("a"),
            py::arg("b")
        )
        .def(
            "pow",
            [](const C& calc, double a, double b) -> py::object {
                const double r = calc.pow(a, b);
                return promote_inf_to_big(r, [&] { return calc.pow(B(a), B(b)); });
            },
            py::arg("a"),
            py::arg("b")
        )
        .def("pow", py::overload_cast<Z, Z>(&C::pow, py::const_), py::arg("a"), py::arg("b"))
        .def("pow", py::overload_cast<const B&, const B&>(&C::pow, py::const_), py::arg("a"), py::arg("b"))
        DEF_UNARY_OP(sqrt)
        DEF_BIG_UNARY_OP(sqrt)
        DEF_REAL_UNARY_OP(cbrt)
        DEF_BIN_OP(root)
        DEF_BIG_BIN_OP(root)
        DEF_UNARY_UNIT_OP(sin)
        DEF_UNARY_UNIT_OP(cos)
        DEF_UNARY_UNIT_OP(tan)
        DEF_UNARY_OP(sinh)
        DEF_UNARY_OP(cosh)
        DEF_UNARY_OP(tanh)
        DEF_UNARY_UNIT_OP(asin)
        DEF_UNARY_UNIT_OP(acos)
        DEF_UNARY_UNIT_OP(atan)
        DEF_UNARY_OP(asinh)
        DEF_UNARY_OP(acosh)
        DEF_UNARY_OP(atanh)
        DEF_UNARY_UNIT_OP(polar)
        DEF_UNARY_OP(log)
        DEF_BIG_UNARY_OP(log)
        DEF_UNARY_OP(ln)
        DEF_BIG_UNARY_OP(ln)
        .def(
            "fact",
            [](const C& calc, double a) -> py::object {
                const double r = calc.fact(a);
                return promote_inf_to_big(r, [&] { return calc.fact(B(a)); });
            },
            py::arg("a")
        )
        DEF_BIG_UNARY_OP(fact)
        .def(
            "gamma",
            [](const C& calc, double a) -> py::object {
                const double r = calc.gamma(a);
                return promote_inf_to_big(r, [&] { return calc.gamma(B(a)); });
            },
            py::arg("a")
        )
        DEF_BIG_UNARY_OP(gamma)
        .def("permute", &C::permute, py::arg("n"), py::arg("r"))
        .def("choose", &C::choose, py::arg("n"), py::arg("r"));

#undef DEF_UNARY_UNIT_OP
#undef DEF_UNARY_OP
#undef DEF_BIG_UNARY_OP
#undef DEF_BIN_OP
#undef DEF_REAL_BIN_OP
#undef DEF_REAL_UNARY_OP
#undef DEF_BIG_BIN_OP
}
