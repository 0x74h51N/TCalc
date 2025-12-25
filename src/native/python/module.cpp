#include <pybind11/complex.h>
#include <pybind11/pybind11.h>

#include <boost/math/constants/constants.hpp>

#include "bindings.hpp"
#include "calc/pub/calculator.hpp"

namespace py = pybind11;

PYBIND11_MODULE(calc_native, m) {
    m.doc() = "Calculator core exposed from C++ via pybind11";
    py::register_exception<CalculatorError>(m, "CalculatorError");

    bind_bigreal(m);
    bind_bigcomplex(m);

    using Z = Calculator::Complex;
    using B = BigReal;
    m.attr("pi") = py::cast(boost::math::constants::pi<B>());
    m.attr("e") = py::cast(boost::math::constants::e<B>());
    m.attr("i") = py::cast(Z(0.0, 1.0));

    bind_angle_unit(m);
    bind_calculator(m);
    bind_parser(m);
}
