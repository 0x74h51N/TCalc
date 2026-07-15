/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <string_view>

#include "calc/pub/calculator.hpp"
#include "calc/pub/error_messages.hpp"
#include "parser/internal/helpers.hpp"
#include "parser/pub/consts.hpp"
#include "value.hpp"

namespace tcalc::ops {

/// Operator associativity for precedence resolution.
enum class Assoc : std::uint8_t { Left, Right };
/// Operator arity classification for parser rules.
enum class Arity : std::uint8_t { Binary, Unary, Postfix };

/// Operation identifiers used in tokens and op_table.
enum class OpId : std::uint8_t {
    Add,
    Sub,
    Mul,
    Div,
    Pow,
    Percent,
    Negate,
    UnaryPlus,

    Sqrt,
    Sin,
    Cos,
    Tan,
    Sinh,
    Cosh,
    Tanh,
    Asin,
    Acos,
    Atan,
    Asinh,
    Acosh,
    Atanh,
    Polar,

    Log,
    Ln,

    Recip,
    Fact,

    Mod,
    IntDiv,

    Choose,
    Permute,
    Gamma,
    Cbrt,

    Sqr,
    Cube,
    Root,

    Exp,
    Pow10,

    Trunc,
    Floor,
    Ceil,

    Gcd,
    Lcm,

    Mean,
    Median,
    Min,
    Max,
    Sum,
    Var,
    VarP,
    Std,
    StdP,

    Assign,

    /// Logical ops:
    Equal,

    /// Sentinel: not a real op; used for number tokens.
    Count,
};

/// Operator specification used by the tokenizer/parser.
struct OpSpec {
    OpId id;
    std::string_view symbol;
    int precedence;
    Assoc associativity;
    Arity arity;
    std::array<std::string_view, 2> aliases{};
    std::string_view method;
    /// Bitflags describing extra operator capabilities. Type support (BigReal, Rational,
    /// the angle unit) is no longer a flag: the evaluator derives it from Calculator's own
    /// signatures. What remains is syntax the tokenizer cannot read off the signature.
    enum class OpFlags : std::uint8_t {
        None = 0,
        /// Op is invoked via call syntax: `f(arg0, arg1, …)`.
        CallFunction = 1 << 0,
    };

    /// Extra operator capabilities.
    OpFlags flags{OpFlags::None};

    /// Number of call arguments; kVariadicArity = aggregate over a dataset.
    std::uint8_t call_arity = 1;
};

/// Bitwise OR for OpFlags.
constexpr OpSpec::OpFlags operator|(OpSpec::OpFlags lhs, OpSpec::OpFlags rhs) {
    return static_cast<OpSpec::OpFlags>(
        static_cast<std::uint8_t>(lhs) | static_cast<std::uint8_t>(rhs));
}

/// Check whether a flag is present.
constexpr bool has_flag(OpSpec::OpFlags flags, OpSpec::OpFlags flag) {
    return (static_cast<std::uint8_t>(flags) & static_cast<std::uint8_t>(flag)) != 0;
}

/// Sentinel for OpSpec::call_arity: function folds its args into a dataset.
inline constexpr std::uint8_t kVariadicArity = 0xFF;

/// True when the op is invoked via call syntax: `f(arg0, arg1, …)`.
inline constexpr bool is_call_function(const OpSpec &op) {
    return has_flag(op.flags, OpSpec::OpFlags::CallFunction);
}

/// True when the call function folds its args into a single dataset.
inline constexpr bool is_variadic(const OpSpec &op) {
    return op.call_arity == kVariadicArity;
}

/// Short alias for OpFlags.
using Flags = OpSpec::OpFlags;

/// Operation table used by tokenizer/normalizer and parser.
inline constexpr std::array kOps{
    OpSpec{
        .id = OpId::Add,
        .symbol = "+",
        .precedence = 1,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"add"},
        .method = "add",
    },
    OpSpec{
        .id = OpId::Sub,
        .symbol = "-",
        .precedence = 1,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"sub"},
        .method = "sub",
    },
    OpSpec{
        .id = OpId::Mul,
        .symbol = "·",
        .precedence = 2,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"*", "mul"},
        .method = "mul",
    },
    OpSpec{
        .id = OpId::Div,
        .symbol = "÷",
        .precedence = 2,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"/", "div"},
        .method = "div",
    },
    OpSpec{
        .id = OpId::Pow,
        .symbol = "^",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {"pow"},
        .method = "pow",
    },
    OpSpec{
        .id = OpId::Percent,
        .symbol = "%",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {"percent"},
        .method = "percent",
    },
    OpSpec{
        .id = OpId::Negate,
        .symbol = "u-",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"negate"},
        .method = "negate",
    },
    OpSpec{
        .id = OpId::UnaryPlus,
        .symbol = "u+",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"plus"},
        .method = "unaryplus",
    },

    OpSpec{
        .id = OpId::Sin,
        .symbol = "sin",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "sin",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Cos,
        .symbol = "cos",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "cos",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Tan,
        .symbol = "tan",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "tan",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Sinh,
        .symbol = "sinh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "sinh",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Cosh,
        .symbol = "cosh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "cosh",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Tanh,
        .symbol = "tanh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "tanh",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Asin,
        .symbol = "asin",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "asin",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Acos,
        .symbol = "acos",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "acos",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Atan,
        .symbol = "atan",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "atan",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Asinh,
        .symbol = "asinh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "asinh",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Acosh,
        .symbol = "acosh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "acosh",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Atanh,
        .symbol = "atanh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "atanh",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Polar,
        .symbol = "∠",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"polar", ""},
        .method = "polar",
        .flags = Flags::CallFunction,
    },

    OpSpec{
        .id = OpId::Log,
        .symbol = "log",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"log10", ""},
        .method = "log",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Ln,
        .symbol = "ln",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "ln",
        .flags = Flags::CallFunction,
    },

    OpSpec{
        .id = OpId::Recip,
        .symbol = "⁻¹",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {},
        .method = "recip",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Fact,
        .symbol = "!",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {"factorial", "fact"},
        .method = "fact",
        .flags = Flags::CallFunction,
    },

    OpSpec{
        .id = OpId::Mod,
        .symbol = "mod",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "mod",
        .flags = Flags::CallFunction,
        .call_arity = 2,
    },
    OpSpec{
        .id = OpId::IntDiv,
        .symbol = "intdiv",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "intdiv",
        .flags = Flags::CallFunction,
        .call_arity = 2,
    },

    OpSpec{
        .id = OpId::Choose,
        .symbol = "nCr",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"choose"},
        .method = "choose",
        .flags = Flags::CallFunction,
        .call_arity = 2,
    },
    OpSpec{
        .id = OpId::Permute,
        .symbol = "nPr",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"permute"},
        .method = "permute",
        .flags = Flags::CallFunction,
        .call_arity = 2,
    },
    OpSpec{
        .id = OpId::Gamma,
        .symbol = "Γ",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"gamma", ""},
        .method = "gamma",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Cbrt,
        .symbol = "³√",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"cbrt"},
        .method = "cbrt",
        .flags = Flags::CallFunction,
    },

    OpSpec{
        .id = OpId::Sqr,
        .symbol = "²",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {"sqr"},
        .method = "sqr",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Cube,
        .symbol = "³",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {"cube"},
        .method = "cube",
        .flags = Flags::CallFunction,

    },
    OpSpec{
        .id = OpId::Sqrt,
        .symbol = "√",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"sqrt", ""},
        .method = "sqrt",
        .flags = Flags::CallFunction,

    },
    OpSpec{
        .id = OpId::Root,
        .symbol = "⌄",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {"root"},
        .method = "root",
    },

    OpSpec{
        .id = OpId::Exp,
        .symbol = "exp",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "exp",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Pow10,
        .symbol = "⏨",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "pow10",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Trunc,
        .symbol = "trunc",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"int"},
        .method = "trunc",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Floor,
        .symbol = "⌊",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"floor"},
        .method = "floor",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Ceil,
        .symbol = "⌈",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"ceil"},
        .method = "ceil",
        .flags = Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Gcd,
        .symbol = "gcd",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "gcd",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::Lcm,
        .symbol = "lcm",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "lcm",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::Mean,
        .symbol = "x̄",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"mean"},
        .method = "mean",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::Median,
        .symbol = "x̃",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"median"},
        .method = "median",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::Min,
        .symbol = "min",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "min",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::Max,
        .symbol = "max",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "max",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::Sum,
        .symbol = "Σ",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"sum"},
        .method = "sum",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::Var,
        .symbol = "s²",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"var"},
        .method = "variance",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::VarP,
        .symbol = "σ²",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"varp"},
        .method = "variance_pop",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::Std,
        .symbol = "s",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"std"},
        .method = "stddev",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::StdP,
        .symbol = "σ",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"stdp"},
        .method = "stddev_pop",
        .flags = Flags::CallFunction,
        .call_arity = kVariadicArity,
    },
    OpSpec{
        .id = OpId::Assign,
        .symbol = "=",
        .precedence = 0,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {},
        .method = "",
    },
    OpSpec{
        .id = OpId::Equal,
        .symbol = "==",
        .precedence = 0,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {},
        .method = "",
    },
};

struct TokenToSpec {
    std::string_view token;
    const OpSpec *spec;
};

consteval std::size_t token_table_size() {
    std::size_t n = 0;
    for (const auto &op : kOps) {
        n += 1; // primary symbol
        for (const auto alias : op.aliases) {
            if (!alias.empty()) {
                n += 1;
            }
        }
    }
    return n;
}

consteval auto build_token_table() {
    std::array<TokenToSpec, token_table_size()> out{};
    std::size_t i = 0;
    for (const auto &op : kOps) {
        out[i++] = TokenToSpec{op.symbol, &op};
        for (const auto alias : op.aliases) {
            if (!alias.empty()) {
                out[i++] = TokenToSpec{alias, &op};
            }
        }
    }
    return out;
}

inline constexpr auto kTokenTable = build_token_table();

// First-byte filter: kOpCanStart[b] is true iff some op token starts with byte b.
// Lets match_op skip the longest-match scan at positions that begin no token.
consteval parser::FirstByteTable build_op_can_start() {
    parser::FirstByteTable out{};
    for (const auto &entry : kTokenTable) {
        parser::mark_first_byte(out, entry.token);
    }
    return out;
}
inline constexpr auto kOpCanStart = build_op_can_start();

inline constexpr auto kOpsById =
    parser::index_by_id<OpSpec, static_cast<std::size_t>(OpId::Count)>(kOps);

inline constexpr const OpSpec *op_spec(OpId id) {
    return kOpsById[static_cast<std::size_t>(id)];
}

inline constexpr const OpSpec *find_op(std::string_view token) {
    for (const auto &entry : kTokenTable) {
        if (entry.token == token) {
            return entry.spec;
        }
    }
    return nullptr;
}

// ============================================================================
//
// Operations table: OpId -> kernel.
//
// The syntax table above (kOps) is read by tokenize / normalize / shunting_yard.
// This one is read only by eval. They share OpId as their key and duplicate no
// data: eval never needs precedence or associativity, because the shunting yard
// has already fixed the order by the time an RPN reaches it.
//
// A row is just the call. The trailing return type is load-bearing: without it a
// failing body sits outside the immediate context and `requires` hard-errors
// instead of reporting false.
//
// ============================================================================

using tcalc::Arm;
using tcalc::ArmMask;
using tcalc::Value;
using AngleUnit = Calculator::AngleUnit;

/// The OpId is passed through so a kernel can name the op in its error message.
using Kernel = Value (*)(OpId, const Calculator &, std::span<const Value>, AngleUnit);

/// A row is the Calculator call itself, wrapped in a lambda: `TCALC_CALL(sqrt)` is
/// `c.sqrt(a)`, `TCALC_CALL(add)` is `c.add(a, b)`, `TCALC_CALL(sin)` is `c.sin(a, unit)`.
/// One macro covers all three because the row builder (unary / binary / unary_angle)
/// already says how many operands there are.
///
/// It is a macro, not a template, because `m` is an overloaded member *name*, which is
/// not something a template can take as an argument. And the call has to appear twice:
/// once in the body and once in the trailing return type. That second one is what lets
/// the arm probe ask "does Calculator have this overload?" and get an answer instead of
/// a compile error. The macro writes it once.

#define TCALC_CALL(m)                                                                              \
    [](const Calculator &c, auto &&...args) -> decltype(c.m(args...)) { return c.m(args...); }

/// How a kernel is called. Not an operand count: Unary and UnaryAngle both pop one
/// operand; they differ in whether the angle unit is passed through.
enum class Shape : std::uint8_t { Unary, UnaryAngle, Binary };

/// Does kernel F accept arm T when called in shape S? The three call shapes are the
/// only difference between the probes, so they collapse into this one predicate, keyed
/// by the same Shape the dispatcher uses.
template <class F, Shape S, class T> constexpr bool arm_ok() {
    if constexpr (S == Shape::Unary)
        return requires(const Calculator &c, const T &a) { F{}(c, a); };
    else if constexpr (S == Shape::UnaryAngle)
        return requires(const Calculator &c, const T &a, AngleUnit u) { F{}(c, a, u); };
    else
        return requires(const Calculator &c, const T &a, const T &b) { F{}(c, a, b); };
}

/// The class arms a kernel accepts, read off Calculator's own signatures.
///
/// Int64 is NEVER probed: int64 -> double is a standard conversion, so a probe cannot
/// tell a real overload from an implicit one: `add(int64)` probes true although no such
/// overload exists, and `permute(double)` probes true although it would truncate 1.2 to
/// 1. Int64 is set only by int_binary.
///
/// One probe list serves every shape: Collection probes false for anything that is not
/// a reducer, and reduce() states its arm outright.
template <class F, Shape S> constexpr ArmMask kernel_arms() {
    ArmMask m = 0;
    if constexpr (arm_ok<F, S, double>())
        m |= arm_bit(Arm::Double);
    if constexpr (arm_ok<F, S, Rational>())
        m |= arm_bit(Arm::Rat);
    if constexpr (arm_ok<F, S, BigReal>())
        m |= arm_bit(Arm::Big);
    if constexpr (arm_ok<F, S, Complex>())
        m |= arm_bit(Arm::Cx);
    if constexpr (arm_ok<F, S, BigComplex>())
        m |= arm_bit(Arm::BigCx);
    if constexpr (arm_ok<F, S, Collection>())
        m |= arm_bit(Arm::Coll);
    return m;
}

/// Defensive: after coerce the arguments are homogeneous and the op is known to have
/// that arm, so this cannot fire in practice. It exists so a lattice bug surfaces as an
/// error instead of a wrong answer.
[[noreturn]] inline void throw_unsupported_arm(OpId id) {
    const OpSpec *sp = op_spec(id);
    throw CalculatorError(
        errmsg::unsupported_operand(sp != nullptr ? sp->symbol : "?"), ErrorKind::MathErr);
}

/// Dispatch on the (already homogeneous) first argument: one instantiation per arm,
/// not a 7x7 grid. to_value wraps the result, since the reducers return CollectionItem
/// rather than a Value arm.
template <class F, Shape S>
Value dispatch(OpId id, const Calculator &c, std::span<const Value> args, AngleUnit u) {
    return std::visit(
        [&](const auto &x) -> Value {
            using T = std::decay_t<decltype(x)>;
            if constexpr (S == Shape::Unary) {
                if constexpr (requires { F{}(c, x); })
                    return tcalc::to_value(F{}(c, x));
            } else if constexpr (S == Shape::UnaryAngle) {
                if constexpr (requires { F{}(c, x, u); })
                    return tcalc::to_value(F{}(c, x, u));
            } else {
                // The evaluator pops by arity, so a short argument list can only come from
                // a caller of the binding. Reading args[1] anyway would be out of bounds.
                if (args.size() < 2)
                    throw_unsupported_arm(id);
                const T *y = std::get_if<T>(&args[1]);
                if (y == nullptr)
                    throw_unsupported_arm(id);
                if constexpr (requires { F{}(c, x, *y); })
                    return tcalc::to_value(F{}(c, x, *y));
            }
            throw_unsupported_arm(id);
        },
        args[0]);
}

/// When a real argument leaves an op's real domain, the result is complex and the
/// operand has to be widened before dispatch (sqrt of a negative, log of a
/// non-positive, …). `x` is the first operand; `y` is the second for the ops that need
/// it (Root's degree) and 0 otherwise.
namespace detail {
/// Tolerance for reading a double degree as a whole number.
inline constexpr double kDomainEpsilon = 1e-12;

/// The decades a double can still carry. Past these a power is computed in BigReal.
inline constexpr double kPowToBigUp = 308.0;
inline constexpr double kPowToBigLow = -324.0;
inline constexpr double kBaseTen = 10.0;
} // namespace detail

using DomainRule = bool (*)(double x, double y);

/// True when the operands predict a result double cannot carry, so the op runs in BigReal
/// instead. Unlike the range check above the kernel, which reads an already-rounded
/// result, this one reads the operands: 10^308 is finite and normal, and no amount of
/// looking at the double it produced can recover the digits the rounding dropped.
using RangeRule = bool (*)(double x, double y);

struct OpRow {
    OpId id{};
    Kernel fn{};
    ArmMask arms{};
    DomainRule domain{}; // most ops have no domain boundary
    RangeRule range{};   // and only powers can predict their own range
};

/// Attach the domain rule to an op's own row, next to its kernel and its arms.
constexpr OpRow with_domain(OpRow r, DomainRule d) {
    return OpRow{r.id, r.fn, r.arms, d, r.range};
}

constexpr OpRow with_range(OpRow r, RangeRule g) {
    return OpRow{r.id, r.fn, r.arms, r.domain, g};
}

template <class F> constexpr OpRow unary(OpId id, F) {
    return OpRow{id, &dispatch<F, Shape::Unary>, kernel_arms<F, Shape::Unary>()};
}
template <class F> constexpr OpRow unary_angle(OpId id, F) {
    return OpRow{id, &dispatch<F, Shape::UnaryAngle>, kernel_arms<F, Shape::UnaryAngle>()};
}
template <class F> constexpr OpRow binary(OpId id, F) {
    return OpRow{id, &dispatch<F, Shape::Binary>, kernel_arms<F, Shape::Binary>()};
}
/// permute / choose take `long long`. A probe reports a double arm (double -> long long
/// is a standard conversion) and would silently truncate permute(1.2, 4.4) to (1, 4).
/// So these declare Int64 and are never probed.
template <class F> constexpr OpRow int_binary(OpId id, F) {
    return OpRow{id, &dispatch<F, Shape::Binary>, arm_bit(Arm::Int64)};
}
template <class F> constexpr OpRow reduce(OpId id, F) {
    return OpRow{id, &dispatch<F, Shape::Unary>, arm_bit(Arm::Coll)};
}
/// Exp is pow(e, a) and `e` is irrational, so it can have no exact Rational arm.
constexpr OpRow without_rational(OpRow r) {
    return OpRow{r.id, r.fn, static_cast<ArmMask>(r.arms & ~arm_bit(Arm::Rat))};
}

/// The ops defined through another one: Sqr is `c.pow(a, 2)`, Pow10 is `c.pow(10, a)`.
/// TCALC_CALL_WITH puts the literal on the right, TCALC_CALL_ONTO on the left. The
/// literal is built in the operand's own type (Rational(2), BigReal(2), ...), which is
/// what keeps sqr of a fraction exact.
#define TCALC_CALL_WITH(m, n)                                                                      \
    [](const Calculator &c, auto &&a) -> decltype(c.m(a, std::decay_t<decltype(a)>(n))) {          \
        return c.m(a, std::decay_t<decltype(a)>(n));                                               \
    }
#define TCALC_CALL_ONTO(m, n)                                                                      \
    [](const Calculator &c, auto &&a) -> decltype(c.m(std::decay_t<decltype(a)>(n), a)) {          \
        return c.m(std::decay_t<decltype(a)>(n), a);                                               \
    }

namespace detail {

/// A power leaves double behind when its result no longer fits, and the estimate has to be
/// made on the operands: base^exp has log10 magnitude exp*log10(|base|). Base ten with a
/// whole exponent is called out on its own because 10^308 is the one power that lands
/// inside double's range yet cannot be held exactly by it.
inline bool power_needs_big(double base, double exp) {
    const double base_mag = std::fabs(base);
    const bool exp_is_int = std::abs(exp - std::round(exp)) <= kDomainEpsilon;
    if (base_mag == kBaseTen && exp_is_int && std::fabs(exp) >= kPowToBigUp)
        return true;
    const double log10_mag = exp * std::log10(base_mag);
    return log10_mag > kPowToBigUp || log10_mag < kPowToBigLow;
}

} // namespace detail

inline constexpr std::array kOpRows = {
    // arithmetic
    binary(OpId::Add, TCALC_CALL(add)),
    binary(OpId::Sub, TCALC_CALL(sub)),
    binary(OpId::Mul, TCALC_CALL(mul)),
    binary(OpId::Div, TCALC_CALL(div)),
    with_range(
        binary(OpId::Pow, TCALC_CALL(pow)),
        [](double x, double y) { return detail::power_needs_big(x, y); }),
    with_range(
        with_domain(
            binary(OpId::Root, TCALC_CALL(root)),
            [](double x, double y) {
                // a negative radicand is real only for an odd integer degree
                const bool y_is_int = std::abs(y - std::round(y)) <= detail::kDomainEpsilon;
                const bool y_is_even = std::llround(y) % 2 == 0;
                return x < 0.0 && (!y_is_int || y_is_even);
            }),
        // the degree is an inverse exponent: root(x, y) is x^(1/y)
        [](double x, double y) { return y != 0.0 && detail::power_needs_big(x, 1.0 / y); }),
    binary(OpId::Mod, TCALC_CALL(mod)),
    binary(OpId::IntDiv, TCALC_CALL(intdiv)),

    // trig, angle-taking
    unary_angle(OpId::Sin, TCALC_CALL(sin)),
    unary_angle(OpId::Cos, TCALC_CALL(cos)),
    unary_angle(OpId::Tan, TCALC_CALL(tan)),
    with_domain(
        unary_angle(OpId::Asin, TCALC_CALL(asin)),
        [](double x, double) { return std::abs(x) > 1.0; }),
    with_domain(
        unary_angle(OpId::Acos, TCALC_CALL(acos)),
        [](double x, double) { return std::abs(x) > 1.0; }),
    unary_angle(OpId::Atan, TCALC_CALL(atan)),
    unary_angle(OpId::Polar, TCALC_CALL(polar)),

    // hyperbolic / transcendental
    unary(OpId::Sinh, TCALC_CALL(sinh)),
    unary(OpId::Cosh, TCALC_CALL(cosh)),
    unary(OpId::Tanh, TCALC_CALL(tanh)),
    unary(OpId::Asinh, TCALC_CALL(asinh)),
    with_domain(unary(OpId::Acosh, TCALC_CALL(acosh)), [](double x, double) { return x < 1.0; }),
    with_domain(
        unary(OpId::Atanh, TCALC_CALL(atanh)), [](double x, double) { return std::abs(x) >= 1.0; }),
    with_domain(unary(OpId::Sqrt, TCALC_CALL(sqrt)), [](double x, double) { return x < 0.0; }),
    unary(OpId::Cbrt, TCALC_CALL(cbrt)),
    with_domain(unary(OpId::Log, TCALC_CALL(log)), [](double x, double) { return x <= 0.0; }),
    with_domain(unary(OpId::Ln, TCALC_CALL(ln)), [](double x, double) { return x <= 0.0; }),
    unary(OpId::Fact, TCALC_CALL(fact)),
    unary(OpId::Gamma, TCALC_CALL(gamma)),
    unary(OpId::Trunc, TCALC_CALL(trunc)),
    unary(OpId::Floor, TCALC_CALL(floor)),
    unary(OpId::Ceil, TCALC_CALL(ceil)),

    // integer-only (Calculator takes long long)
    int_binary(OpId::Choose, TCALC_CALL(choose)),
    int_binary(OpId::Permute, TCALC_CALL(permute)),

    // derived: expressed through a real Calculator call, so each inherits that call's
    // arms. That is what keeps sqr of a fraction exact.
    unary(
        OpId::Negate,
        [](const Calculator &c, auto &&a) -> decltype(c.sub(std::decay_t<decltype(a)>{}, a)) {
            return c.sub(std::decay_t<decltype(a)>{}, a); // zero of the arm's own type
        }),
    unary(
        OpId::UnaryPlus,
        [](const Calculator &c, auto &&a) -> std::decay_t<decltype(a)> { return a; }),
    unary(OpId::Percent, TCALC_CALL_WITH(div, 100)),
    unary(OpId::Sqr, TCALC_CALL_WITH(pow, 2)),
    unary(OpId::Cube, TCALC_CALL_WITH(pow, 3)),
    unary(OpId::Recip, TCALC_CALL_WITH(pow, -1)),
    unary(OpId::Pow10, TCALC_CALL_ONTO(pow, 10)),
    without_rational(unary(
        OpId::Exp,
        [](const Calculator &c, auto &&a) -> decltype(c.pow(std::decay_t<decltype(a)>{}, a)) {
            using T = std::decay_t<decltype(a)>;
            return c.pow(T(consts::euler_number()), a);
        })),

    // collection reducers (calculator.hpp). Note the OpId and the method name differ
    // for the last four; read the mapping off OpSpec.method.
    reduce(OpId::Gcd, TCALC_CALL(gcd)),
    reduce(OpId::Lcm, TCALC_CALL(lcm)),
    reduce(OpId::Mean, TCALC_CALL(mean)),
    reduce(OpId::Median, TCALC_CALL(median)),
    reduce(OpId::Min, TCALC_CALL(min)),
    reduce(OpId::Max, TCALC_CALL(max)),
    reduce(OpId::Sum, TCALC_CALL(sum)),
    reduce(OpId::Var, TCALC_CALL(variance)),
    reduce(OpId::VarP, TCALC_CALL(variance_pop)),
    reduce(OpId::Std, TCALC_CALL(stddev)),
    reduce(OpId::StdP, TCALC_CALL(stddev_pop)),
};

inline constexpr std::size_t kOpCount = static_cast<std::size_t>(OpId::Count);

constexpr std::array<Kernel, kOpCount> build_kernels() {
    std::array<Kernel, kOpCount> t{};
    for (const auto &row : kOpRows)
        t[static_cast<std::size_t>(row.id)] = row.fn;
    return t;
}
constexpr std::array<ArmMask, kOpCount> build_arms() {
    std::array<ArmMask, kOpCount> t{};
    for (const auto &row : kOpRows)
        t[static_cast<std::size_t>(row.id)] = row.arms;
    return t;
}

inline constexpr auto kKernels = build_kernels();
inline constexpr auto kArms = build_arms();

constexpr std::array<DomainRule, kOpCount> build_domains() {
    std::array<DomainRule, kOpCount> t{};
    for (const auto &row : kOpRows)
        t[static_cast<std::size_t>(row.id)] = row.domain;
    return t;
}
inline constexpr auto kDomains = build_domains();

/// The op's complex-domain rule, or nullptr when it has no domain boundary.
constexpr DomainRule domain_of(OpId id) {
    return kDomains[static_cast<std::size_t>(id)];
}

constexpr std::array<RangeRule, kOpCount> build_ranges() {
    std::array<RangeRule, kOpCount> t{};
    for (const auto &row : kOpRows)
        t[static_cast<std::size_t>(row.id)] = row.range;
    return t;
}
inline constexpr auto kRanges = build_ranges();

/// The op's range rule, or nullptr when its result cannot be predicted from its operands.
constexpr RangeRule range_of(OpId id) {
    return kRanges[static_cast<std::size_t>(id)];
}

inline Kernel kernel_of(OpId id) {
    return kKernels[static_cast<std::size_t>(id)];
}

constexpr ArmMask arms_of(OpId id) {
    return kArms[static_cast<std::size_t>(id)];
}

/// Drift guard: an op that OpSpec says is evaluated by a call (non-empty .method)
/// must have a kernel row. Adding an OpId without one fails the build. Compile-time
/// only; the kernel table reads no OpSpec field at run time.
constexpr bool every_evaluable_op_has_a_kernel() {
    for (const auto &spec : kOps) {
        if (spec.method.empty())
            continue;
        if (kKernels[static_cast<std::size_t>(spec.id)] == nullptr)
            return false;
    }
    return true;
}
static_assert(every_evaluable_op_has_a_kernel(), "an OpId with a method has no kernel row");

// The arm derivation, asserted rather than tested: it is compile-time data.
static_assert(
    !tcalc::has_arm(arms_of(OpId::Add), Arm::Int64),
    "Int64 must never be derived: it probes true via the double overload");
static_assert(tcalc::has_arm(arms_of(OpId::Add), Arm::Rat));
static_assert(
    tcalc::has_arm(arms_of(OpId::Sqrt), Arm::Rat),
    "sqrt is exact on rationals: Calculator::sqrt(const Rational &) provides the arm");
static_assert(
    !tcalc::has_arm(arms_of(OpId::Cbrt), Arm::Big),
    "Calculator has no cbrt(BigReal); a BigReal argument must error, not demote");
static_assert(
    tcalc::has_arm(arms_of(OpId::Permute), Arm::Int64) &&
        !tcalc::has_arm(arms_of(OpId::Permute), Arm::Double),
    "permute is integer-only; a double arm would silently truncate 1.2 to 1");
static_assert(!tcalc::has_arm(arms_of(OpId::Exp), Arm::Rat));

} // namespace tcalc::ops
