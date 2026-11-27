/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "eval/internal/exact.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cmath>
#include <cstdint>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

#include <boost/multiprecision/cpp_int.hpp>

#include "calc/internal/helpers.hpp"
#include "calc/pub/error_messages.hpp"
#include "eval/internal/closed_forms.hpp"
#include "eval/pub/eval.hpp"
#include "parser/internal/helpers.hpp"
#include "parser/pub/consts.hpp"

namespace tcalc::eval::exact {
namespace {

using BigInt = boost::multiprecision::cpp_int;
using ops::OpId;
using parser::LatexKind;
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

/// Peel any wrapping single-element parens: `(log(56))` and `((3^{5}))` reach the row inside
/// unchanged. Empty means a paren wrapped something other than exactly one element.
std::span<const Token> unwrap_paren(std::span<const Token> row) {
    while (row.size() == 1 && row[0].kind == TokenKind::Paren) {
        const auto &paren = std::get<parser::ParenToken>(row[0].data);
        if (paren.elements.size() != 1)
            return {};
        row = parser::element_tokens(paren.elements.front());
    }
    return row;
}

/// The argument row of `log_id`'s call, or an empty span when the row is not exactly that call.
/// Rows arrive here unnormalized, so a based log is still its script token followed by the
/// value. The call form, the base-less prefix form, and any of them wrapped in a single-element
/// paren also reach here.
std::span<const Token> log_argument(OpId log_id, std::span<const Token> row) {
    row = unwrap_paren(row);
    if (row.size() == 1 && row[0].kind == TokenKind::Call) {
        const auto &call = std::get<parser::CallToken>(row[0].data);
        if (call.op_id == log_id && call.args.size() == 1)
            return parser::element_tokens(call.args.front());
        return {};
    }
    if (row.size() != 2)
        return {};
    if (row[0].kind == TokenKind::Op && std::get<parser::OpToken>(row[0].data).op_id == log_id)
        return row.subspan(1);
    const auto scripted = parser::scripted_op(row[0]);
    return scripted && scripted->id == log_id ? row.subspan(1) : std::span<const Token>{};
}

/// Structural row equality. Never by value: reducing e to a double is the error these rules
/// exist to avoid, and a base spelled two ways (`4` against `2^{2}`) declines to the numeric
/// path, which still answers.
bool same_row(std::span<const Token> a, std::span<const Token> b) {
    return a.size() == b.size() && std::equal(a.begin(), a.end(), b.begin());
}

/// The base row of a `log_{…} v` row, empty when the row is not one.
std::span<const Token> log_subscript(std::span<const Token> row) {
    if (row.size() != 2)
        return {};
    const auto scripted = parser::scripted_op(row[0]);
    return scripted && scripted->id == OpId::Log ? std::span<const Token>(*scripted->script)
                                                 : std::span<const Token>{};
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

/// Whether `power_base` is the base of a logarithm whose own base row is `log_base`, empty when
/// that logarithm carries no subscript and its base is implicit (ten for `log`, e for `ln`,
/// which `log_of_base` already recognises).
bool base_matches(std::span<const Token> power_base, std::span<const Token> log_base, OpId log_id) {
    return log_base.empty() ? log_of_base(power_base) == log_id : same_row(power_base, log_base);
}

/// A base raised to its own logarithm cancels to the logarithm's argument: e^{ln u} = u,
/// 10^{log u} = u, b^{log_{b} u} = u. The exponent is matched first, structurally, for both
/// candidate logs: most Pow exponents are not a log call at all, so the common case bails there
/// without ever looking at the base. Only once the exponent is known to be a specific log call
/// does the base get checked, and only then does anything get evaluated.
std::optional<Value> pow_of_log(
    std::span<const Token> base,
    std::span<const Token> exponent,
    const Calculator &c,
    Calculator::AngleUnit unit) {
    for (const OpId log_id : {OpId::Ln, OpId::Log}) {
        if (log_argument(log_id, exponent).empty())
            continue;
        if (!base_matches(base, log_subscript(exponent), log_id))
            return std::nullopt;
        return log_inverse_of(log_id, exponent, c, unit);
    }
    return std::nullopt;
}

/// log_b(b^k) = k, read off the tokens. Computing b^k first is what loses the answer: 2^{62}
/// is a float by then, and log_2 of it is 62.00000000000001.
std::optional<Value> log_of_power(
    std::span<const Token> base,
    std::span<const Token> value,
    const Calculator &c,
    Calculator::AngleUnit unit) {
    value = unwrap_paren(value);
    if (value.size() != 1 || value[0].kind != TokenKind::Latex)
        return std::nullopt;
    const auto &lx = std::get<parser::LatexToken>(value[0].data);
    if (lx.kind != LatexKind::Pow || !base_matches(lx.left, base, OpId::Log))
        return std::nullopt;
    // The identity holds only where a logarithm in this base exists, and the kernel is what
    // decides that. log_b(1) runs the base guard against a value that cannot promote on its
    // own, so an invalid base fails the probe exactly where the numeric path's real arm
    // would; the probe's answer itself is discarded. lx.left is the base either way, since
    // base_matches has already tied it to the logarithm's own.
    //
    // A base the probe rejects can still answer through the numeric path once the actual
    // value promotes to complex (a negative base raised to an odd power, say, is itself
    // negative, and the complex kernel never re-checks the base). So the probe's own error
    // is not this rule's to raise: on failure it declines instead, the same as a structural
    // mismatch would, and lets the ordinary evaluation of the whole row decide.
    try {
        apply(
            c,
            OpId::Log,
            std::vector<Value>{Value{std::int64_t{1}}, eval_row(lx.left, c, unit)},
            unit);
    } catch (const CalculatorError &) {
        return std::nullopt;
    }
    return eval_row(lx.right, c, unit);
}

/// The forms gcd and lcm read from their tokens, since past 72 digits their value reaches the
/// kernel rounded (#247).
enum class IntForm : std::uint8_t { Power, Factorial };

/// A power or a factorial argument without its parens and a leading minus, which the
/// magnitude gcd and lcm read drops.
struct IntRow {
    IntForm form;
    std::span<const Token> row;
};

bool is_op(const Token &t, OpId id) {
    return t.kind == TokenKind::Op && std::get<parser::OpToken>(t.data).op_id == id;
}

/// A power with an empty side is not one: its side defaults to 0 (2^{} is 1).
std::optional<IntRow> int_row(std::span<const Token> row) {
    row = unwrap_paren(row);
    if (!row.empty() && is_op(row[0], OpId::Negate))
        row = unwrap_paren(row.subspan(1));
    if (row.size() == 1 && row[0].kind == TokenKind::Latex) {
        const auto &lx = std::get<parser::LatexToken>(row[0].data);
        if (lx.kind == LatexKind::Pow && !lx.left.empty() && !lx.right.empty())
            return IntRow{IntForm::Power, row};
    }
    if (row.size() == 2 && is_op(row[1], OpId::Fact))
        return IntRow{IntForm::Factorial, row};
    return std::nullopt;
}

/// An Int64, or a Rational with denominator 1.
std::optional<std::int64_t> int_value(const Value &v) {
    if (const auto *i = std::get_if<std::int64_t>(&v))
        return *i;
    if (const auto *r = std::get_if<Rational>(&v); r && r->denominator() == 1)
        return r->numerator();
    return std::nullopt;
}

/// n!, when n is a whole number and n! is within kMaxIntBits. A negative n is the kernel's error.
std::optional<BigInt> exact_factorial(const Value &x) {
    const auto n = int_value(x);
    if (!n || *n < 0)
        return std::nullopt;
    BigInt product = 1;
    for (std::int64_t i = 2; i <= *n; ++i) {
        product *= i;
        if (boost::multiprecision::msb(product) > calc_detail::kMaxIntBits)
            return std::nullopt;
    }
    return product;
}

/// A power or a factorial whose base, exponent or n shows it is no integer, at any precision.
struct NotInteger {};

/// m^e past kMaxIntBits, never built: gcd reads it modulo the other arguments.
struct HugePower {
    std::uint64_t base;
    std::uint64_t exponent;
};

/// A gcd or lcm argument: the exact integer its tokens name, or the value it evaluated to.
using Arg = std::variant<BigInt, Value, NotInteger, HugePower>;

/// A power from its evaluated base and exponent.
Arg power_arg(Value base, Value exponent, const Calculator &c, Calculator::AngleUnit unit) {
    auto b = int_value(base);
    auto e = int_value(exponent);
    // (p/q)^e with q > 1 is no integer for e > 0.
    if (const auto *r = std::get_if<Rational>(&base); r && r->denominator() != 1 && e && *e > 0)
        return NotInteger{};
    // m^(p/q) is an integer only when m is a q-th power r, and then it is r^p.
    if (const auto *r = std::get_if<Rational>(&exponent); b && r && r->denominator() != 1) {
        const auto root = calc_detail::exact_int_root(*b, r->denominator());
        if (!root)
            return NotInteger{};
        b = root;
        e = r->numerator();
    }
    if (b && e && *e >= 0) {
        const std::uint64_t m = calc_detail::magnitude(*b);
        // log2 bounds no base under 2, and the exponent cast below would wrap: 0^{4294967296}
        // would become 0^{0}. Their value is exact.
        if (m >= 2) {
            const auto e64 = static_cast<std::uint64_t>(*e);
            // m^e has e*log2(m) bits past its msb, so the msb bound the others read is this.
            if (static_cast<double>(e64) * std::log2(static_cast<double>(m)) >=
                static_cast<double>(calc_detail::kMaxIntBits + 1))
                return HugePower{m, e64};
            return BigInt(boost::multiprecision::pow(BigInt(m), static_cast<unsigned>(e64)));
        }
    }
    return apply(c, OpId::Pow, std::vector<Value>{std::move(base), std::move(exponent)}, unit);
}

/// Each operand row is evaluated once: the exact integer is built from the base and exponent,
/// or n, and the value from them otherwise, in the order eval_latex and eval_op take.
Arg read_int_row(const IntRow &r, const Calculator &c, Calculator::AngleUnit unit) {
    Arg arg;
    switch (r.form) {
    case IntForm::Power: {
        const auto &lx = std::get<parser::LatexToken>(r.row[0].data);
        if (const LatexRule rule = latex_rule(lx.op_id))
            if (auto v = rule(lx.left, lx.right, c, unit)) {
                arg = std::move(*v);
                break;
            }
        arg = power_arg(eval_row(lx.left, c, unit), eval_row(lx.right, c, unit), c, unit);
        break;
    }
    case IntForm::Factorial: {
        Value x = eval_row(r.row.first(1), c, unit);
        // The factorial of a fraction is no integer.
        if (const auto *q = std::get_if<Rational>(&x); q && q->denominator() != 1)
            arg = NotInteger{};
        else if (auto n = exact_factorial(x))
            arg = std::move(*n);
        else
            arg = apply(c, OpId::Fact, std::vector<Value>{std::move(x)}, unit);
        break;
    }
    }
    return arg;
}

/// gcd or lcm with each power or factorial argument read from its tokens. Declines, before
/// evaluating anything, when no argument is one or one is empty: the kernel path then runs as
/// usual and reports the empty one where it reaches it.
template <calc_detail::BigStep Step, calc_detail::PowerStep Power>
std::optional<Value> fold_rule(
    OpId id,
    std::span<const parser::ParenElement> args,
    const Calculator &c,
    Calculator::AngleUnit unit) {
    if (std::ranges::any_of(args, [](const parser::ParenElement &arg) {
            return parser::element_tokens(arg).empty();
        }))
        return std::nullopt;
    std::size_t first = 0;
    std::optional<IntRow> shape;
    while (first < args.size() && !(shape = int_row(parser::element_tokens(args[first]))))
        ++first;
    if (!shape)
        return std::nullopt;

    // Every argument is evaluated before any is folded, as the dataset is before the kernel.
    std::vector<Arg> read;
    read.reserve(args.size());
    for (std::size_t i = 0; i < args.size(); ++i) {
        const auto row = parser::element_tokens(args[i]);
        if (i > first)
            shape = int_row(row);
        if (i >= first && shape) {
            read.push_back(read_int_row(*shape, c, unit));
            continue;
        }
        Value v = eval_row(row, c, unit);
        // A collection beside other arguments is the dataset's error, which the kernel path
        // reports; only the arguments up to it run twice, on the way to that error.
        if (std::holds_alternative<Collection>(v))
            return std::nullopt;
        read.emplace_back(std::move(v));
    }

    const std::string name(ops::op_spec(id)->symbol);
    std::optional<BigInt> acc;
    const auto fold = [&acc](BigInt n) { acc = acc ? Step(*acc, n) : std::move(n); };
    // A power past kMaxIntBits joins last, read against everything else.
    std::vector<const HugePower *> huge;
    for (const Arg &arg : read)
        std::visit(
            [&](const auto &a) {
                using T = std::decay_t<decltype(a)>;
                if constexpr (std::is_same_v<T, BigInt>)
                    fold(a);
                else if constexpr (std::is_same_v<T, Value>)
                    fold(calc_detail::int_operand(a, name.c_str()));
                else if constexpr (std::is_same_v<T, NotInteger>)
                    throw CalculatorError(errmsg::integers_only(name).c_str());
                else {
                    static_assert(std::is_same_v<T, HugePower>);
                    huge.push_back(&a);
                }
            },
            arg);
    for (const HugePower *p : huge)
        acc = Power(acc, p->base, p->exponent);
    return to_value(calc_detail::item_of(acc.value()));
}

struct ExactRow {
    OpId id;
    TokenRule from_tokens;
    ValueRule from_value;
    LatexRule from_latex;
    CallRule from_call;
};

constexpr std::array kExactRows{
    ExactRow{OpId::Sin, trig_from_tokens, trig_from_value, nullptr, nullptr},
    ExactRow{OpId::Cos, trig_from_tokens, trig_from_value, nullptr, nullptr},
    ExactRow{OpId::Tan, trig_from_tokens, trig_from_value, nullptr, nullptr},
    ExactRow{OpId::Exp, exp_of_log, nullptr, nullptr, nullptr},
    ExactRow{OpId::Pow, nullptr, nullptr, pow_of_log, nullptr},
    ExactRow{OpId::Log, nullptr, nullptr, log_of_power, nullptr},
    ExactRow{
        OpId::Gcd,
        nullptr,
        nullptr,
        nullptr,
        fold_rule<calc_detail::gcd_of, calc_detail::gcd_power>},
    ExactRow{
        OpId::Lcm,
        nullptr,
        nullptr,
        nullptr,
        fold_rule<calc_detail::lcm_of, calc_detail::lcm_power>},
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

CallRule call_rule(OpId id) {
    const ExactRow *row = kRowsById[static_cast<std::size_t>(id)];
    return row == nullptr ? nullptr : row->from_call;
}

} // namespace tcalc::eval::exact
