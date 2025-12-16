#include <pybind11/pybind11.h>
#include <pybind11/complex.h>

#include "calculator.hpp"

namespace py = pybind11;


PYBIND11_MODULE(calc_native, m) {
    m.doc() = "Calculator core exposed from C++ via pybind11";
    py::register_exception<CalculatorError>(m, "CalculatorError");

    using C = Calculator;
    using Z = Calculator::Complex;
    using U = Calculator::AngleUnit;

    py::enum_<U>(m, "AngleUnit")
        .value("DEG", U::DEG)
        .value("RAD", U::RAD)
        .value("GRAD", U::GRAD)
        .export_values();

    py::class_<C>(m, "Calculator")
        .def(py::init<>())

        .def("add", py::overload_cast<double, double>(&C::add, py::const_))
        .def("add", py::overload_cast<Z, Z>(&C::add, py::const_))

        .def("sub", py::overload_cast<double, double>(&C::sub, py::const_))
        .def("sub", py::overload_cast<Z, Z>(&C::sub, py::const_))

        .def("mul", py::overload_cast<double, double>(&C::mul, py::const_))
        .def("mul", py::overload_cast<Z, Z>(&C::mul, py::const_))

        .def("div", py::overload_cast<double, double>(&C::div, py::const_))
        .def("div", py::overload_cast<Z, Z>(&C::div, py::const_))

        .def("pow", py::overload_cast<double, long long>(&C::pow, py::const_))
        .def("pow", py::overload_cast<double, double>(&C::pow, py::const_))
        .def("pow", py::overload_cast<Z, Z>(&C::pow, py::const_))

        .def("sqrt", py::overload_cast<double>(&C::sqrt, py::const_))
        .def("sqrt", py::overload_cast<Z>(&C::sqrt, py::const_))

         .def("sin", py::overload_cast<double, U>(&C::sin, py::const_), py::arg("a"), py::arg("unit"))
        .def("sin", py::overload_cast<Z, U>(&C::sin, py::const_), py::arg("a"), py::arg("unit"))

        .def("cos", py::overload_cast<double, U>(&C::cos, py::const_), py::arg("a"), py::arg("unit"))
        .def("cos", py::overload_cast<Z, U>(&C::cos, py::const_), py::arg("a"), py::arg("unit"))

        .def("tan", py::overload_cast<double, U>(&C::tan, py::const_), py::arg("a"), py::arg("unit"))
        .def("tan", py::overload_cast<Z, U>(&C::tan, py::const_), py::arg("a"), py::arg("unit"))

        .def("sinh", py::overload_cast<double>(&C::sinh, py::const_), py::arg("a"))
        .def("sinh", py::overload_cast<Z>(&C::sinh, py::const_), py::arg("a"))

        .def("cosh", py::overload_cast<double>(&C::cosh, py::const_), py::arg("a"))
        .def("cosh", py::overload_cast<Z>(&C::cosh, py::const_), py::arg("a"))

        .def("tanh", py::overload_cast<double>(&C::tanh, py::const_), py::arg("a"))
        .def("tanh", py::overload_cast<Z>(&C::tanh, py::const_), py::arg("a"));
}
