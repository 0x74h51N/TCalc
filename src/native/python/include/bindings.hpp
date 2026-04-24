/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <pybind11/pybind11.h>

#include <cmath>
#include <utility>
#include "calc/internal/helpers.hpp"
#include "parser/pub/parser.hpp"
#include "types.hpp"
#include "calc/pub/calculator.hpp"

namespace py = pybind11;
namespace p = tcalc::parser;

// Python binding declarations for calculator native extension
void bind_bigreal(pybind11::module_ &m);
void bind_bigcomplex(pybind11::module_ &m);
void bind_rational(pybind11::module_ &m);
void bind_angle_unit(pybind11::module_ &m);
void bind_calculator(pybind11::module_ &m);
void bind_parser(pybind11::module_ &m);

namespace detail {
inline constexpr int kPythonPrecision = 16;
inline constexpr double kPowToBigUp = 308.0;
inline constexpr double kPowToBigLow = -324.0;
inline constexpr double kBaseTen = 10.0;
} // namespace detail

inline bool pow_to_big(double base, double exp, bool exp_is_int) {
    const double base_mag = std::fabs(base);

    if (base_mag == detail::kBaseTen && exp_is_int && std::fabs(exp) >= detail::kPowToBigUp) {
        return true;
    }

    const double log10_mag = exp * std::log10(base_mag);
    if (log10_mag > detail::kPowToBigUp || log10_mag < detail::kPowToBigLow) {
        return true;
    }
    return false;
}

template <typename BigFn> inline pybind11::object promote_inf_to_big(double r, BigFn &&big_fn) {
    if (!std::isinf(r)) {
        return pybind11::float_(r);
    }
    return pybind11::cast(std::forward<BigFn>(big_fn)());
}

template <typename Class, typename Member>
py::class_<Class> &def_readonly_ref(py::class_<Class> &c, const char *name, Member Class::*member) {
    c.def_property_readonly(
        name,
        [member](Class &self) -> const Member & { return self.*member; },
        py::return_value_policy::reference_internal);

    return c;
}
template <typename Class, typename T>
py::class_<Class> &
def_readonly_ref(py::class_<Class> &c, const char *name, std::vector<T> Class::*member) {
    c.def_property_readonly(
        name,
        [member](Class &self) -> const std::vector<T> & { return self.*member; },
        py::return_value_policy::reference_internal);

    return c;
}

template <typename T> const T *token_as(const p::Token &tok) {
    return std::get_if<T>(&tok.data);
}

template <typename T> const T *math_as(const p::MathNode &n) {
    return std::get_if<T>(&n.data);
}

/// Rational^Rational with promotion
inline py::object rational_pow(const Calculator &calc, const Rational &a, const Rational &b) {
    const double da = a.to_double();
    const double db = b.to_double();
    const bool exp_is_int = b.denominator() == 1;

    if (pow_to_big(da, db, exp_is_int)) {
        return py::cast(calc.pow(BigReal(da), BigReal(db)));
    }
    if (auto r = calc_detail::try_rational_pow(calc, a, b)) {
        return py::cast(*r);
    }
    if (exp_is_int) {
        return promote_inf_to_big(calc.pow(da, static_cast<double>(b.numerator())), [&] {
            return calc.pow(BigReal(da), BigReal(db));
        });
    }
    return py::float_(calc.pow(da, db));
}

/// Rational root: root(a, b) = a^(1/b).
inline py::object rational_root(const Calculator &calc, const Rational &a, const Rational &b) {
    calc_detail::require_nonzero(b.frac);
    long long p = b.numerator();
    long long q = b.denominator();
    // Normalize sign onto numerator (boost::rational keeps den > 0, but after
    // swapping num/den we must re-normalize manually).
    if (p < 0) {
        p = -p;
        q = -q;
    }
    const Rational inv(q, p); // exp = 1/b = q/p

    const double da = a.to_double();
    const double db = b.to_double();
    const double d_inv = static_cast<double>(q) / static_cast<double>(p);
    const bool exp_is_int = inv.denominator() == 1;

    if (pow_to_big(da, d_inv, exp_is_int)) {
        return py::cast(calc.root(BigReal(da), BigReal(db)));
    }
    if (auto r = calc_detail::try_rational_pow(calc, a, inv)) {
        return py::cast(*r);
    }
    if (exp_is_int) {
        return promote_inf_to_big(calc.pow(da, static_cast<double>(inv.numerator())), [&] {
            return calc.root(BigReal(da), BigReal(db));
        });
    }
    return py::float_(calc.root(da, db));
}
