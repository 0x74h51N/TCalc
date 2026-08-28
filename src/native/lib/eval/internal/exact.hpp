/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once
#include <optional>
#include <span>

#include "calc/pub/calculator.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"
#include "value.hpp"

namespace tcalc::eval::exact {

/// Exact as opposed to the double the numeric kernel would produce: sin(pi) is 0, not
/// 1.2246e-16. The kernel cannot know that, because by the time it runs pi is a double like any
/// other. A rule runs before it and answers from structure the kernel can no longer see (a named
/// constant still intact in the tokens) or from an exact table, returning the exact value or
/// declining so the kernel runs as usual.
///
/// An op may have one rule per phase. Every rule:
///   1. runs its cheapest structural check first, and allocates nothing until it passes
///   2. leaves the caller free to continue untouched when it returns nullopt
///   3. keeps its own preconditions (angle unit and such) here, not at the call site

/// Answers from the operand's tokens, before it is evaluated.
using TokenRule = std::optional<Value> (*)(
    ops::OpId, std::span<const parser::Token>, const Calculator &, Calculator::AngleUnit);

/// Answers from the evaluated operand.
using ValueRule =
    std::optional<Value> (*)(ops::OpId, const Value &, const Calculator &, Calculator::AngleUnit);

/// Answers from a latex token's two operand rows, before either is evaluated.
using LatexRule = std::optional<Value> (*)(
    std::span<const parser::Token>,
    std::span<const parser::Token>,
    const Calculator &,
    Calculator::AngleUnit);

/// nullptr when the op has no rule for that phase.
TokenRule token_rule(ops::OpId id);
ValueRule value_rule(ops::OpId id);
LatexRule latex_rule(ops::OpId id);

} // namespace tcalc::eval::exact
