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

} // namespace tcalc::eval
