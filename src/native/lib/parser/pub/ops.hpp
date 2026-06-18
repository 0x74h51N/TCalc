/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <array>
#include <cstdint>
#include <string_view>

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
    /// Bitflags describing extra operator capabilities.
    enum class OpFlags : std::uint8_t {
        None = 0,
        /// Trig uses the angle unit setting.
        NeedsAngleUnit = 1 << 0,
        /// BigReal supported.
        BigSupported = 1 << 1,
        /// BigComplex supported.
        BigComplexSupported = 1 << 2,
        /// Rational (exact fraction) supported.
        RationalSupported = 1 << 3,
        /// Op is invoked via call syntax: `f(arg0, arg1, …)`.
        CallFunction = 1 << 4,
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

/// True when the op depends on the angle unit setting.
constexpr bool needs_angle_unit(const OpSpec &op) {
    return has_flag(op.flags, OpSpec::OpFlags::NeedsAngleUnit);
}

/// True when BigReal is supported for the op.
constexpr bool big_supported(const OpSpec &op) {
    return has_flag(op.flags, OpSpec::OpFlags::BigSupported);
}

/// True when BigComplex is supported for the op.
constexpr bool big_complex_supported(const OpSpec &op) {
    return has_flag(op.flags, OpSpec::OpFlags::BigComplexSupported);
}

/// True when Rational is supported for the op.
constexpr bool rational_supported(const OpSpec &op) {
    return has_flag(op.flags, OpSpec::OpFlags::RationalSupported);
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
        .flags = Flags::BigSupported | Flags::BigComplexSupported | Flags::RationalSupported,
    },
    OpSpec{
        .id = OpId::Sub,
        .symbol = "-",
        .precedence = 1,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"sub"},
        .method = "sub",
        .flags = Flags::BigSupported | Flags::BigComplexSupported | Flags::RationalSupported,
    },
    OpSpec{
        .id = OpId::Mul,
        .symbol = "x",
        .precedence = 2,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"*", "mul"},
        .method = "mul",
        .flags = Flags::BigSupported | Flags::BigComplexSupported | Flags::RationalSupported,
    },
    OpSpec{
        .id = OpId::Div,
        .symbol = "÷",
        .precedence = 2,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"/", "div"},
        .method = "div",
        .flags = Flags::BigSupported | Flags::BigComplexSupported | Flags::RationalSupported,
    },
    OpSpec{
        .id = OpId::Pow,
        .symbol = "^",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {"pow"},
        .method = "pow",
        .flags = Flags::BigSupported | Flags::BigComplexSupported | Flags::RationalSupported,
    },
    OpSpec{
        .id = OpId::Percent,
        .symbol = "%",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {"percent"},
        .method = "percent",
        .flags = Flags::RationalSupported,
    },
    OpSpec{
        .id = OpId::Negate,
        .symbol = "u-",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"negate"},
        .method = "negate",
        .flags = Flags::RationalSupported,
    },
    OpSpec{
        .id = OpId::UnaryPlus,
        .symbol = "u+",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"plus"},
        .method = "unaryplus",
        .flags = Flags::RationalSupported,
    },

    OpSpec{
        .id = OpId::Sin,
        .symbol = "sin",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "sin",
        .flags = Flags::NeedsAngleUnit | Flags::BigSupported | Flags::BigComplexSupported |
                 Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Cos,
        .symbol = "cos",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "cos",
        .flags = Flags::NeedsAngleUnit | Flags::BigSupported | Flags::BigComplexSupported |
                 Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Tan,
        .symbol = "tan",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "tan",
        .flags = Flags::NeedsAngleUnit | Flags::BigSupported | Flags::BigComplexSupported |
                 Flags::CallFunction,
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
        .flags = Flags::NeedsAngleUnit | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Acos,
        .symbol = "acos",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "acos",
        .flags = Flags::NeedsAngleUnit | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Atan,
        .symbol = "atan",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "atan",
        .flags = Flags::NeedsAngleUnit | Flags::CallFunction,
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
        .flags = Flags::NeedsAngleUnit | Flags::CallFunction,
    },

    OpSpec{
        .id = OpId::Log,
        .symbol = "log",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"log10", ""},
        .method = "log",
        .flags = Flags::BigSupported | Flags::BigComplexSupported | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Ln,
        .symbol = "ln",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "ln",
        .flags = Flags::BigSupported | Flags::BigComplexSupported | Flags::CallFunction,
    },

    OpSpec{
        .id = OpId::Recip,
        .symbol = "⁻¹",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {},
        .method = "recip",
        .flags = Flags::RationalSupported | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Fact,
        .symbol = "!",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {"factorial", "fact"},
        .method = "fact",
        .flags = Flags::BigSupported | Flags::CallFunction,
    },

    OpSpec{
        .id = OpId::Mod,
        .symbol = "mod",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "mod",
        .flags = Flags::BigSupported | Flags::CallFunction,
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
        .flags = Flags::BigSupported | Flags::CallFunction,
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
        .flags = Flags::BigSupported | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Cbrt,
        .symbol = "³√",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"cbrt"},
        .method = "cbrt",
        .flags = Flags::RationalSupported | Flags::CallFunction,
    },

    OpSpec{
        .id = OpId::Sqr,
        .symbol = "²",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {"sqr"},
        .method = "sqr",
        .flags = Flags::RationalSupported | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Cube,
        .symbol = "³",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {"cube"},
        .method = "cube",
        .flags = Flags::RationalSupported | Flags::CallFunction,

    },
    OpSpec{
        .id = OpId::Sqrt,
        .symbol = "√",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"sqrt", ""},
        .method = "sqrt",
        .flags = Flags::BigSupported | Flags::BigComplexSupported | Flags::RationalSupported |
                 Flags::CallFunction,

    },
    OpSpec{
        .id = OpId::Root,
        .symbol = "⌄",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {"root"},
        .method = "root",
        .flags = Flags::BigSupported | Flags::BigComplexSupported | Flags::RationalSupported,
    },

    OpSpec{
        .id = OpId::Exp,
        .symbol = "exp",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "exp",
        .flags = Flags::BigSupported | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Pow10,
        .symbol = "⏨",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "pow10",
        .flags = Flags::RationalSupported | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Trunc,
        .symbol = "trunc",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"int"},
        .method = "trunc",
        .flags = Flags::BigSupported | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Floor,
        .symbol = "⌊",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"floor"},
        .method = "floor",
        .flags = Flags::BigSupported | Flags::CallFunction,
    },
    OpSpec{
        .id = OpId::Ceil,
        .symbol = "⌈",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"ceil"},
        .method = "ceil",
        .flags = Flags::BigSupported | Flags::CallFunction,
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

consteval auto build_ops_by_id() {
    std::array<const OpSpec *, static_cast<std::size_t>(OpId::Count)> out{};
    for (auto &p : out) {
        p = nullptr;
    }

    for (const auto &op : kOps) {
        const std::size_t idx = static_cast<std::size_t>(op.id);
        if (idx >= out.size()) {
            throw "ops.hpp: OpId out of range";
        }
        if (out[idx] != nullptr) {
            throw "ops.hpp: duplicate OpId";
        }
        out[idx] = &op;
    }

    return out;
}

inline constexpr auto kOpsById = build_ops_by_id();

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

} // namespace tcalc::ops
