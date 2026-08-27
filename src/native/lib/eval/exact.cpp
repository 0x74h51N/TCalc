/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "eval/internal/exact.hpp"

#include <array>
#include <cstddef>

#include "eval/internal/closed_forms.hpp"
#include "eval/pub/eval.hpp"
#include "parser/internal/helpers.hpp"

namespace tcalc::eval::exact {
namespace {

using ops::OpId;
using parser::Token;
using parser::TokenKind;

/// The trig function an op id names. OpId has too many enumerators for a switch to be exhaustive,
/// so a row wrongly added for a fourth op declines here rather than computing some other function.
std::optional<Calculator::TrigFn> trig_fn_of(OpId id) {
    switch (id) {
    case OpId::Sin:
        return Calculator::TrigFn::Sin;
    case OpId::Cos:
        return Calculator::TrigFn::Cos;
    case OpId::Tan:
        return Calculator::TrigFn::Tan;
    default:
        return std::nullopt;
    }
}

/// sin or cos of pi*t: exact where the table has it, the folded numeric value otherwise.
Value at_half_turns(const Calculator &c, Calculator::TrigFn fn, const Rational &t) {
    const auto exact = c.exact_half_turns(fn, t);
    return exact ? Value{*exact} : Value{c.real_half_turns(fn, t)};
}

/// Radians, read from the argument's own tokens: a rational multiple of pi survives here, the
/// collapsed double does not.
std::optional<Value> trig_from_tokens(
    OpId id, std::span<const Token> arg, const Calculator &c, Calculator::AngleUnit unit) {
    if (unit != Calculator::AngleUnit::RAD)
        return std::nullopt;
    const auto fn = trig_fn_of(id);
    if (!fn)
        return std::nullopt;
    // A lone Number or Char holds no constant, and that is what an iterated loop passes a
    // million times, so it must not reach the allocating walk.
    if (arg.size() == 1 && arg[0].kind != TokenKind::Const && arg[0].kind != TokenKind::Paren &&
        arg[0].kind != TokenKind::Latex)
        return std::nullopt;
    const auto s = scalar_of_tokens(shunting_yard(arg));
    if (!s)
        return std::nullopt;
    const auto t = scalar_half_turns(*s, c, Calculator::AngleUnit::RAD);
    if (!t)
        return std::nullopt;
    return at_half_turns(c, *fn, *t);
}

/// Degrees and grads, read from the already-evaluated operand: no token walk needed.
std::optional<Value>
trig_from_value(OpId id, const Value &arg, const Calculator &c, Calculator::AngleUnit unit) {
    if (unit == Calculator::AngleUnit::RAD)
        return std::nullopt;
    const auto fn = trig_fn_of(id);
    const auto a = to_rational(arg);
    if (!fn || !a)
        return std::nullopt;
    const auto t = c.half_turns(*a, unit);
    if (!t)
        return std::nullopt;
    return at_half_turns(c, *fn, *t);
}

struct ExactRow {
    OpId id;
    TokenRule from_tokens;
    ValueRule from_value;
};

constexpr std::array kExactRows{
    ExactRow{OpId::Sin, trig_from_tokens, trig_from_value},
    ExactRow{OpId::Cos, trig_from_tokens, trig_from_value},
    ExactRow{OpId::Tan, trig_from_tokens, trig_from_value},
};

// index_by_id rejects an out-of-range or duplicated id at compile time, so the table cannot
// drift out of line with OpId.
constexpr auto kRowsById =
    parser::index_by_id<ExactRow, static_cast<std::size_t>(OpId::Count)>(kExactRows);

/// The token site hands a rule one operand row, which is only the whole call when the call
/// takes one argument.
consteval bool token_rules_take_one_argument() {
    for (const auto &row : kExactRows) {
        if (row.from_tokens == nullptr)
            continue;
        const ops::OpSpec &spec = *ops::op_spec(row.id);
        if (ops::is_call_function(spec) && spec.call_arity != 1)
            return false;
    }
    return true;
}
static_assert(
    token_rules_take_one_argument(),
    "a call function taking more than one argument cannot carry a token rule");

} // namespace

TokenRule token_rule(OpId id) {
    const ExactRow *row = kRowsById[static_cast<std::size_t>(id)];
    return row == nullptr ? nullptr : row->from_tokens;
}

ValueRule value_rule(OpId id) {
    const ExactRow *row = kRowsById[static_cast<std::size_t>(id)];
    return row == nullptr ? nullptr : row->from_value;
}

} // namespace tcalc::eval::exact
