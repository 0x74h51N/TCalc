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
#include "parser/pub/parser.hpp"
#include "value.hpp"

namespace tcalc::eval {

using CppRat = boost::multiprecision::cpp_rational;

/// Size bound for the var-free product closed form (c^count). Its exponentiation squares a
/// big integer, and one squaring is a single allocation the wall-clock deadline cannot
/// interrupt, so the count needs an a-priori cap. Brute-force loops and Faulhaber sums have
/// no such single-shot blow-up and are bounded by the deadline (or exempt) instead.
inline constexpr std::int64_t kMaxIterations = 1'000'000;

/// Convert an exact big rational to a Value the calc's way: an int64-range numerator and
/// denominator become a Rational, anything larger a double (the calc has no Rational->BigReal
/// promotion; overflowing Rational arithmetic already falls to double).
Value value_from_big_rational(const CppRat &r);

/// Sum_{n=a}^{b} p(n) for polynomial p with coefficients [c0..cd] (low degree first), exact.
CppRat faulhaber_sum(const std::vector<CppRat> &coeffs, std::int64_t a, std::int64_t b);

/// Walk an iterated body's RPN, building the polynomial in `var` as a trimmed coefficient
/// vector, or nullopt when the body is not a polynomial the matcher accepts.
std::optional<std::vector<CppRat>>
canonicalise(std::span<const parser::Token> rpn, std::string_view var);

/// Matcher entry point: the closed-form Value, or nullopt (the caller then brute-forces).
std::optional<Value> try_closed_form(
    parser::LatexKind kind,
    std::span<const parser::Token> rpn,
    std::string_view var,
    std::int64_t first,
    std::int64_t last);

} // namespace tcalc::eval
