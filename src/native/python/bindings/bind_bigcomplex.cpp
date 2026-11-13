#include <pybind11/pybind11.h>

#include <string>

#include "bindings.hpp"
#include "calc/pub/calculator.hpp"

namespace py = pybind11;

void bind_bigcomplex(py::module_ &m) {
    using BC = BigComplex;
    using BF = boost::multiprecision::cpp_bin_float_50;
    using B = BigReal;

    const auto text = [](const BC &v) {
        const BF re(v.backend().real_data());
        const BF im(v.backend().imag_data());
        return re.str(detail::kPythonPrecision) + (im >= 0 ? "+" : "") +
               im.str(detail::kPythonPrecision) + "i";
    };

    py::class_<BC>(m, "BigComplex")
        .def(py::init<>())
        .def(py::init<double>(), py::arg("real"))
        .def(py::init<double, double>(), py::arg("real"), py::arg("imag"))
        .def(py::init<const std::string &>(), py::arg("real"))
        .def(py::init<const std::string &, const std::string &>(), py::arg("real"), py::arg("imag"))
        .def(py::init([](const B &re) { return BC(BF(re), BF(0)); }), py::arg("real"))
        .def(
            py::init([](const B &re, const B &im) { return BC(BF(re), BF(im)); }),
            py::arg("real"),
            py::arg("imag"))
        .def("__str__", text)
        .def("__repr__", [text](const BC &v) { return "BigComplex(\"" + text(v) + "\")"; });
}
