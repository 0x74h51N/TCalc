#pragma once

#include <vector>

#include "calc/pub/calculator.hpp"
#include "calc/pub/errors.hpp"
#include "parser/pub/ops.hpp"
#include "value.hpp"

namespace tcalc::eval {

/// Widen args[0] to Complex when a real operand leaves the op's real domain
/// (sqrt of a negative, log of a non-positive). The rule comes from the op's row.
/// Only args[0] is ever promoted; a Root's degree is left alone.
void promote_complex(ops::OpId id, std::vector<Value> &args);

/// Pick the arm the op will be called on and widen every argument to it, using the arms
/// the op actually has. Widening only: a complex or a BigReal meeting an op that cannot
/// take it is an error, never a narrowing.
std::vector<Value> coerce(ops::OpId id, std::vector<Value> args);

/// Evaluate one operation: domain promotion, the lattice, dispatch, a double retry when
/// exact arithmetic cannot represent its result, then range promotion.
Value apply(const Calculator &c, ops::OpId id, std::vector<Value> args, Calculator::AngleUnit unit);

} // namespace tcalc::eval
