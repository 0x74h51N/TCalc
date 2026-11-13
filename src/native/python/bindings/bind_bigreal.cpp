#include <pybind11/pybind11.h>

#include <string>

#include "bindings.hpp"
#include "calc/pub/calculator.hpp"

namespace py = pybind11;

void bind_bigreal(py::module_ &m) {
    using B = BigReal;

    py::class_<B>(m, "BigReal")
        .def(py::init<double>(), py::arg("value"))
        .def(py::init<const std::string &>(), py::arg("text"))
        .def("__str__", [](const B &v) { return v.str(detail::kPythonPrecision); })
        .def("__repr__", [](const B &v) {
            return "BigReal(\"" + v.str(detail::kPythonPrecision) + "\")";
        });
}
