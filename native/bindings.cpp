#include <pybind11/pybind11.h>
#include "calculator.hpp"

namespace py = pybind11;

PYBIND11_MODULE(calc_native, m) {
    m.doc() = "Calculator core exposed from C++ via pybind11";

    py::register_exception<CalculatorError>(m, "CalculatorError");

    py::class_<Calculator>(m, "Calculator")
        .def(py::init<>())
        .def("add", &Calculator::add)
        .def("sub", &Calculator::sub)
        .def("mul", &Calculator::mul)
        .def("div", &Calculator::div);
}
