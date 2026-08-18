/*
 *
 *  TCalc is a native-powered scientific desktop calculator designed
 *  for high-performance, precision, and a superior user experience.
 *  Copyright (C) 2026 Tahsin Önemli
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#pragma once
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>
#include <vector>
#include <boost/multiprecision/cpp_int.hpp>
#include "calc/pub/calculator.hpp"
#include "eval/internal/scalar.hpp"
#include "parser/pub/parser.hpp"
#include "eval/internal/scalar.hpp"
#include "value.hpp"

namespace tcalc::eval {

/// Size bound for the var-free product closed form (c^count). Its exponentiation squares a
/// big integer, and one squaring is a single allocation the wall-clock deadline cannot
/// interrupt, so the count needs an a-priori cap. Brute-force loops and Faulhaber sums have
/// no such single-shot blow-up and are bounded by the deadline (or exempt) instead.
inline constexpr std::int64_t kMaxIterations = 1'000'000;

/// Convert an exact big rational to a Value the calc's way: an int64-range numerator and
/// denominator become a Rational, anything larger a double (the calc has no Rational->BigReal
/// promotion; overflowing Rational arithmetic already falls to double).
Value value_from_big_rational(const CppRat &r);

/// Sum_{n=a}^{b} p(n) for polynomial p with coefficients [c0..cd] (low degree first).
std::optional<Scalar>
faulhaber_sum(const std::vector<Scalar> &coeffs, std::int64_t a, std::int64_t b);

/// The same sum for rational-only coefficients, which stay exact and cannot decline.
CppRat faulhaber_sum(const std::vector<CppRat> &coeffs, std::int64_t a, std::int64_t b);

/// The span's value as a Scalar (coefficient, symbols, residual) when it is variable-free, or
/// nullopt when it does not classify. Runs the closed forms' own walk with an empty bound
/// variable, so no Char is the loop variable and every token folds into the var-free arm. The
/// trig path uses it to recover a pi-carrying coefficient the evaluated Value has lost.
std::optional<Scalar> scalar_of_tokens(std::span<const parser::Token> rpn);

/// The scalar as t half turns, so the angle is pi*t, or nullopt when it is not one. Radians
/// accept only a rational multiple of pi, since a rational number of radians is an irrational
/// number of half turns; degrees and grads accept only a plain rational and convert through the
/// Calculator, which is where the 180 and 200 live.
std::optional<Rational>
scalar_half_turns(const Scalar &s, const Calculator &c, Calculator::AngleUnit unit);

/// Matcher entry point: the closed-form Value, or nullopt (the caller then brute-forces).
std::optional<Value> try_closed_form(
    parser::LatexKind kind,
    std::span<const parser::Token> rpn,
    std::string_view var,
    std::int64_t first,
    std::int64_t last,
    const Calculator &calc,
    Calculator::AngleUnit unit);

} // namespace tcalc::eval
