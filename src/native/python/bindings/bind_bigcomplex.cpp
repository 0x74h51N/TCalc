#include <pybind11/pybind11.h>

#include <iomanip>
#include <sstream>

#include "bindings.hpp"
#include "calc/pub/calculator.hpp"

namespace py = pybind11;

void bind_bigcomplex(py::module_ &m) {
    using BC = BigComplex;
    using BF = boost::multiprecision::cpp_bin_float_50;

    py::class_<BC>(m, "BigComplex")
        .def(py::init<>())
        .def(py::init<double>(), py::arg("real"))
        .def(py::init<double, double>(), py::arg("real"), py::arg("imag"))
        .def(py::init<const std::string &>(), py::arg("real"))
        .def(py::init<const std::string &, const std::string &>(), py::arg("real"), py::arg("imag"))
        .def("__str__",
             [](const BC &v) {
                 std::ostringstream oss;
                 BF re(v.backend().real_data());
                 BF im(v.backend().imag_data());
                 oss << std::setprecision(16) << re;
                 if (im >= 0) {
                     oss << "+";
                 }
                 oss << std::setprecision(16) << im << "i";
                 return oss.str();
             })
        .def("__repr__", [](const BC &v) {
            std::ostringstream oss;
            BF re(v.backend().real_data());
            BF im(v.backend().imag_data());
            oss << std::setprecision(16) << re;
            if (im >= 0) {
                oss << "+";
            }
            oss << std::setprecision(16) << im << "i";
            return std::string("BigComplex(\"") + oss.str() + "\")";
        });
}
