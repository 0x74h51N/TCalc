#include <pybind11/pybind11.h>

#include <iomanip>
#include <ios>
#include <limits>
#include <sstream>
#include <string>

#include "bindings.hpp"
#include "calc/internal/calculator.hpp"

namespace py = pybind11;

void bind_bigreal(py::module_ &m) {
    using B = BigReal;

    py::class_<B>(m, "BigReal")
        .def(py::init<double>())
        .def(py::init<const std::string &>())
        .def("__str__",
             [](const B &v) {
                 std::ostringstream oss;
                 oss << std::setprecision(16) << v;
                 return oss.str();
             })
        .def("__repr__", [](const B &v) {
            std::ostringstream oss;
            oss << std::setprecision(16) << v;
            return oss.str();
        });
}
