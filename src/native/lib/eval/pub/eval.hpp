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

#include <span>
#include <vector>

#include "calc/pub/calculator.hpp"
#include "calc/pub/errors.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"
#include "value.hpp"

namespace tcalc::eval {

/// Widen args[0] to Complex when a real operand leaves the op's real domain
/// (sqrt of a negative, log of a non-positive). The rule comes from the op's row.
/// Only args[0] is ever promoted; a Root's degree is left alone.
bool promote_complex(ops::OpId id, std::vector<Value> &args);

/// Widen a power's operands to BigReal when the op's range rule says a double could not
/// carry the result. Returns whether it fired.
bool promote_big(ops::OpId id, std::vector<Value> &args);

/// Pick the arm the op will be called on and widen every argument to it, using the arms
/// the op actually has. Widening only: a complex or a BigReal meeting an op that cannot
/// take it is an error, never a narrowing.
std::vector<Value> coerce(ops::OpId id, std::vector<Value> args);

/// Evaluate one operation: domain promotion, the lattice, dispatch, a double retry when
/// exact arithmetic cannot represent its result, then range promotion.
Value apply(const Calculator &c, ops::OpId id, std::vector<Value> args, Calculator::AngleUnit unit);

/// A constant's value, which is a double for all but the imaginary unit.
Value const_value(const consts::ConstSpec &spec);

/// Insert implicit multiplication and fold runs of + and - into one sign. The step the
/// shunt runs first; exposed because it is worth pinning on its own.
std::vector<parser::Token> normalize(std::span<const parser::Token> tokens);

/// Normalize a row and convert it to RPN.
std::vector<parser::Token> shunting_yard(std::span<const parser::Token> tokens);

/// Walk an RPN list.
Value eval_rpn(std::span<const parser::Token> rpn, const Calculator &c, Calculator::AngleUnit unit);

/// Shunt a row, then walk it. A Latex side, a paren element and a call argument each go
/// through this when the evaluator reaches them, so it is called recursively.
Value eval_row(
    std::span<const parser::Token> tokens, const Calculator &c, Calculator::AngleUnit unit);

/// Evaluate one row of input. An `=` in second position makes the row an assignment: the
/// name on its left is bound in the session store to the value of everything on its right.
/// Any other row is evaluated as it stands.
Value evaluate(const parser::TokensBranch &branch, const Calculator &c, Calculator::AngleUnit unit);

/// Toggle the iterated-op closed-form matcher (Faulhaber / var-free product). On by default;
/// a benchmark turns it off to measure the brute-force path on the same expression. The flag is
/// read once per iterate() call, before the loop, so it adds no per-iteration cost.
void set_closed_forms_enabled(bool on);
bool closed_forms_enabled();

/// Test-only flag for whether a closed form ran since the last reset, so a test can assert the
/// closed path actually ran rather than merely that the loop would have produced the same value.
void reset_closed_form_taken();
bool closed_form_taken();

/// Wall-clock budget for one top-level evaluate(), in milliseconds. 0 (default) is unlimited,
/// which the benchmark and the whole test suite keep so their timings stay deterministic.
/// The app sets ~500ms so a runaway expression returns a "timed out" error instead of freezing
/// the UI. Read once when a deadline is armed, so it costs nothing while unlimited.
void set_eval_time_budget_ms(long ms);
long eval_time_budget_ms();

} // namespace tcalc::eval
