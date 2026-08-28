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
#include "parser/pub/consts.hpp"

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

/// The argument row of `log_id`'s call, or an empty span when the row is not exactly that call.
/// Three spellings reach here: the call form, the bare prefix form, and either wrapped in a
/// single-element paren.
std::span<const Token> log_argument(OpId log_id, std::span<const Token> row) {
    while (row.size() == 1 && row[0].kind == TokenKind::Paren) {
        const auto &paren = std::get<parser::ParenToken>(row[0].data);
        if (paren.elements.size() != 1)
            return {};
        row = parser::element_tokens(paren.elements.front());
    }
    if (row.size() == 1 && row[0].kind == TokenKind::Call) {
        const auto &call = std::get<parser::CallToken>(row[0].data);
        if (call.op_id == log_id && call.args.size() == 1)
            return parser::element_tokens(call.args.front());
        return {};
    }
    if (row.size() == 2 && row[0].kind == TokenKind::Op &&
        std::get<parser::OpToken>(row[0].data).op_id == log_id)
        return row.subspan(1);
    return {};
}

/// u, when base^log_base(u) is exact. The identity holds wherever the logarithm is defined, so
/// the row is walked normally first and its value discarded: arm selection, promotion and every
/// error stay where they already live, and nothing about them is restated here.
std::optional<Value> log_inverse_of(
    OpId log_id, std::span<const Token> row, const Calculator &c, Calculator::AngleUnit unit) {
    const std::span<const Token> arg = log_argument(log_id, row);
    if (arg.empty())
        return std::nullopt;
    eval_row(row, c, unit);
    return eval_row(arg, c, unit);
}

std::optional<Value>
exp_of_log(OpId, std::span<const Token> arg, const Calculator &c, Calculator::AngleUnit unit) {
    return log_inverse_of(OpId::Ln, arg, c, unit);
}

/// The logarithm whose base this row is: e -> Ln, 10 -> Log. A single Const or Number token,
/// checked structurally, so it costs nothing until an exponent has already matched a log call.
std::optional<OpId> log_of_base(std::span<const Token> row) {
    if (row.size() != 1)
        return std::nullopt;
    if (row[0].kind == TokenKind::Const &&
        std::get<parser::ConstToken>(row[0].data).id == consts::ConstId::EulerNumber)
        return OpId::Ln;
    if (row[0].kind == TokenKind::Number &&
        std::get<parser::NumberToken>(row[0].data).value == "10")
        return OpId::Log;
    return std::nullopt;
}

/// A base raised to its own logarithm cancels to the logarithm's argument: e^{ln u} = u,
/// 10^{log u} = u. The exponent is matched first, structurally, for both candidate logs: most
/// Pow exponents are not a log call at all, so the common case bails there without ever looking
/// at the base. Only once the exponent is known to be a specific log call does the base get
/// checked, and only then does anything get evaluated.
std::optional<Value> pow_of_log(
    std::span<const Token> base,
    std::span<const Token> exponent,
    const Calculator &c,
    Calculator::AngleUnit unit) {
    for (const OpId log_id : {OpId::Ln, OpId::Log}) {
        if (log_argument(log_id, exponent).empty())
            continue;
        if (log_of_base(base) != log_id)
            return std::nullopt;
        return log_inverse_of(log_id, exponent, c, unit);
    }
    return std::nullopt;
}

struct ExactRow {
    OpId id;
    TokenRule from_tokens;
    ValueRule from_value;
    LatexRule from_latex;
};

constexpr std::array kExactRows{
    ExactRow{OpId::Sin, trig_from_tokens, trig_from_value, nullptr},
    ExactRow{OpId::Cos, trig_from_tokens, trig_from_value, nullptr},
    ExactRow{OpId::Tan, trig_from_tokens, trig_from_value, nullptr},
    ExactRow{OpId::Exp, exp_of_log, nullptr, nullptr},
    ExactRow{OpId::Pow, nullptr, nullptr, pow_of_log},
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

LatexRule latex_rule(OpId id) {
    const ExactRow *row = kRowsById[static_cast<std::size_t>(id)];
    return row == nullptr ? nullptr : row->from_latex;
}

} // namespace tcalc::eval::exact
