#include <pybind11/pybind11.h>
#include <pybind11/complex.h>

#include <iomanip>
#include <ios>
#include <limits>
#include <sstream>
#include <string>

#include <boost/math/constants/constants.hpp>

#include "calculator.hpp"

namespace py = pybind11;


PYBIND11_MODULE(calc_native, m) {
    m.doc() = "Calculator core exposed from C++ via pybind11";
    py::register_exception<CalculatorError>(m, "CalculatorError");

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

#define DEF_POW_OP() \
    .def("pow", py::overload_cast<double, long long>(&C::pow, py::const_), py::arg("a"), py::arg("b")) \
    .def("pow", py::overload_cast<double, double>(&C::pow, py::const_), py::arg("a"), py::arg("b")) \
    .def("pow", py::overload_cast<Z, Z>(&C::pow, py::const_), py::arg("a"), py::arg("b")) \
    .def("pow", py::overload_cast<const B&, const B&>(&C::pow, py::const_), py::arg("a"), py::arg("b"))

    py::class_<B>(m, "BigReal")
        .def(py::init<double>())
        .def(py::init<const std::string&>())
        .def(
            "__str__",
            [](const B& v) {
                std::ostringstream oss;
                oss << std::setprecision(16) << v;
                return oss.str();
            }
        )
        .def(
            "__repr__",
            [](const B& v) {
                std::ostringstream oss;
                oss << std::setprecision(16) << v;
                return oss.str();
            }
        );

    m.attr("pi") = py::cast(boost::math::constants::pi<B>());
    m.attr("e") = py::cast(boost::math::constants::e<B>());
    m.attr("i") = py::cast(Z(0.0, 1.0));

    py::enum_<U>(m, "AngleUnit")
        .value("DEG", U::DEG)
        .value("RAD", U::RAD)
        .value("GRAD", U::GRAD)
        .export_values();

    py::class_<C>(m, "Calculator")
        .def(py::init<>())
        DEF_BIN_OP(add)
        DEF_BIG_BIN_OP(add)
        DEF_BIN_OP(sub)
        DEF_BIG_BIN_OP(sub)
        DEF_BIN_OP(mul)
        DEF_BIG_BIN_OP(mul)
        DEF_BIN_OP(div)
        DEF_BIG_BIN_OP(div)
        DEF_REAL_BIN_OP(intdiv)
        DEF_BIG_BIN_OP(intdiv)
        DEF_REAL_BIN_OP(mod)
        DEF_BIG_BIN_OP(mod)
        DEF_POW_OP()
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
        DEF_REAL_UNARY_OP(fact)
        DEF_REAL_UNARY_OP(gamma)
        .def("permute", py::overload_cast<long long, long long>(&C::permute, py::const_), py::arg("n"), py::arg("r"))
        .def("choose", py::overload_cast<long long, long long>(&C::choose, py::const_), py::arg("n"), py::arg("r"));

#undef DEF_POW_OP
#undef DEF_UNARY_UNIT_OP
#undef DEF_UNARY_OP
#undef DEF_BIG_UNARY_OP
#undef DEF_BIN_OP
#undef DEF_REAL_BIN_OP
#undef DEF_REAL_UNARY_OP
#undef DEF_BIG_BIN_OP
}
