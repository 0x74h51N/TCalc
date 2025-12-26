#pragma once

#include <array>
#include <cstdint>
#include <string_view>

namespace tcalc::ops {

enum class Assoc : std::uint8_t { Left, Right };
enum class Arity : std::uint8_t { Binary, Unary, Postfix };

enum class OpId : std::uint16_t {
    Add,
    Sub,
    Mul,
    Div,
    Pow,
    Percent,
    Negate,

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

    Count,
};

struct OpSpec {
    OpId id;
    std::string_view symbol;
    int precedence;
    Assoc associativity;
    Arity arity;
    std::array<std::string_view, 2> aliases{};
    std::string_view method;
    enum class OpFlags : std::uint8_t {
        None = 0,
        NeedsAngleUnit = 1 << 0,
        BigSupported = 1 << 1,
        BigComplexSupported = 1 << 2,
    };

    OpFlags flags{OpFlags::None};
};

constexpr OpSpec::OpFlags operator|(OpSpec::OpFlags lhs, OpSpec::OpFlags rhs) {
    return static_cast<OpSpec::OpFlags>(static_cast<std::uint8_t>(lhs) |
                                        static_cast<std::uint8_t>(rhs));
}

constexpr bool has_flag(OpSpec::OpFlags flags, OpSpec::OpFlags flag) {
    return (static_cast<std::uint8_t>(flags) & static_cast<std::uint8_t>(flag)) != 0;
}

constexpr bool needs_angle_unit(const OpSpec &op) {
    return has_flag(op.flags, OpSpec::OpFlags::NeedsAngleUnit);
}

constexpr bool big_supported(const OpSpec &op) {
    return has_flag(op.flags, OpSpec::OpFlags::BigSupported);
}

constexpr bool big_complex_supported(const OpSpec &op) {
    return has_flag(op.flags, OpSpec::OpFlags::BigComplexSupported);
}

using Flags = OpSpec::OpFlags;

inline constexpr std::array kOps{
    OpSpec{
        .id = OpId::Add,
        .symbol = "+",
        .precedence = 1,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {},
        .method = "add",
        .flags = Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Sub,
        .symbol = "-",
        .precedence = 1,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {},
        .method = "sub",
        .flags = Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Mul,
        .symbol = "x",
        .precedence = 2,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"*", ""},
        .method = "mul",
        .flags = Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Div,
        .symbol = "÷",
        .precedence = 2,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"/", ""},
        .method = "div",
        .flags = Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Pow,
        .symbol = "^",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {},
        .method = "pow",
        .flags = Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Percent,
        .symbol = "%",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {},
        .method = "percent",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Negate,
        .symbol = "u-",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "negate",
        .flags = Flags::None,
    },

    OpSpec{
        .id = OpId::Sin,
        .symbol = "sin",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "sin",
        .flags = Flags::NeedsAngleUnit | Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Cos,
        .symbol = "cos",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "cos",
        .flags = Flags::NeedsAngleUnit | Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Tan,
        .symbol = "tan",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "tan",
        .flags = Flags::NeedsAngleUnit | Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Sinh,
        .symbol = "sinh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "sinh",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Cosh,
        .symbol = "cosh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "cosh",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Tanh,
        .symbol = "tanh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "tanh",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Asin,
        .symbol = "asin",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "asin",
        .flags = Flags::NeedsAngleUnit,
    },
    OpSpec{
        .id = OpId::Acos,
        .symbol = "acos",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "acos",
        .flags = Flags::NeedsAngleUnit,
    },
    OpSpec{
        .id = OpId::Atan,
        .symbol = "atan",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "atan",
        .flags = Flags::NeedsAngleUnit,
    },
    OpSpec{
        .id = OpId::Asinh,
        .symbol = "asinh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "asinh",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Acosh,
        .symbol = "acosh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "acosh",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Atanh,
        .symbol = "atanh",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "atanh",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Polar,
        .symbol = "∠",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"polar", ""},
        .method = "polar",
        .flags = Flags::NeedsAngleUnit,
    },

    OpSpec{
        .id = OpId::Log,
        .symbol = "log",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"log10", ""},
        .method = "log",
        .flags = Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Ln,
        .symbol = "ln",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "ln",
        .flags = Flags::BigSupported | Flags::BigComplexSupported,
    },

    OpSpec{
        .id = OpId::Recip,
        .symbol = "⁻¹",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {},
        .method = "recip",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Fact,
        .symbol = "!",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {"factorial", "fact"},
        .method = "fact",
        .flags = Flags::BigSupported,
    },

    OpSpec{
        .id = OpId::Mod,
        .symbol = "mod",
        .precedence = 2,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {},
        .method = "mod",
        .flags = Flags::BigSupported,
    },
    OpSpec{
        .id = OpId::IntDiv,
        .symbol = "div",
        .precedence = 2,
        .associativity = Assoc::Left,
        .arity = Arity::Binary,
        .aliases = {"//", ""},
        .method = "intdiv",
        .flags = Flags::BigSupported,
    },

    OpSpec{
        .id = OpId::Choose,
        .symbol = "nCm",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {},
        .method = "choose",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Permute,
        .symbol = "nPm",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {},
        .method = "permute",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Gamma,
        .symbol = "Γ",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"gamma", ""},
        .method = "gamma",
        .flags = Flags::BigSupported,
    },
    OpSpec{
        .id = OpId::Cbrt,
        .symbol = "³√",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "cbrt",
        .flags = Flags::None,
    },

    OpSpec{
        .id = OpId::Sqr,
        .symbol = "²",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {},
        .method = "sqr",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Cube,
        .symbol = "³",
        .precedence = 4,
        .associativity = Assoc::Left,
        .arity = Arity::Postfix,
        .aliases = {},
        .method = "cube",
        .flags = Flags::None,
    },
    OpSpec{
        .id = OpId::Sqrt,
        .symbol = "√",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {"sqrt", ""},
        .method = "sqrt",
        .flags = Flags::BigSupported | Flags::BigComplexSupported,
    },
    OpSpec{
        .id = OpId::Root,
        .symbol = "⌄",
        .precedence = 3,
        .associativity = Assoc::Right,
        .arity = Arity::Binary,
        .aliases = {},
        .method = "root",
        .flags = Flags::BigSupported | Flags::BigComplexSupported,
    },

    OpSpec{
        .id = OpId::Exp,
        .symbol = "exp",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "exp",
        .flags = Flags::BigSupported,
    },
    OpSpec{
        .id = OpId::Pow10,
        .symbol = "⏨",
        .precedence = 4,
        .associativity = Assoc::Right,
        .arity = Arity::Unary,
        .aliases = {},
        .method = "pow10",
        .flags = Flags::None,
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
