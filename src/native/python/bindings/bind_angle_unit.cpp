#include <pybind11/pybind11.h>

#include "bindings.hpp"
#include "calc/pub/calculator.hpp"

namespace py = pybind11;

void bind_angle_unit(py::module_ &m) {
    using U = Calculator::AngleUnit;

    py::enum_<U>(m, "AngleUnit")
        .value("DEG", U::DEG)
        .value("RAD", U::RAD)
        .value("GRAD", U::GRAD)
        .export_values();
}
