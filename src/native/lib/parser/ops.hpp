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
    bool needs_angle_unit{false};
    bool big_supported{false};
    std::string_view promo_rule;
};

inline constexpr std::array kOps{
    OpSpec{OpId::Add, "+", 1, Assoc::Left, Arity::Binary, {}, "add", false, true, ""},
    OpSpec{OpId::Sub, "-", 1, Assoc::Left, Arity::Binary, {}, "sub", false, true, ""},
    OpSpec{OpId::Mul, "x", 2, Assoc::Left, Arity::Binary, {"*", ""}, "mul", false, true, ""},
    OpSpec{OpId::Div, "÷", 2, Assoc::Left, Arity::Binary, {"/", ""}, "div", false, true, ""},
    OpSpec{OpId::Pow, "^", 3, Assoc::Right, Arity::Binary, {}, "pow", false, true, ""},
    OpSpec{OpId::Percent, "%", 4, Assoc::Left, Arity::Postfix, {}, "percent", false, false, ""},
    OpSpec{OpId::Negate, "u-", 3, Assoc::Right, Arity::Unary, {}, "negate", false, false, ""},

    OpSpec{
        OpId::Sqrt, "√", 4, Assoc::Right, Arity::Unary, {"sqrt", ""}, "sqrt", false, true, "sqrt"},
    OpSpec{OpId::Sin, "sin", 4, Assoc::Right, Arity::Unary, {}, "sin", true, false, ""},
    OpSpec{OpId::Cos, "cos", 4, Assoc::Right, Arity::Unary, {}, "cos", true, false, ""},
    OpSpec{OpId::Tan, "tan", 4, Assoc::Right, Arity::Unary, {}, "tan", true, false, ""},
    OpSpec{OpId::Sinh, "sinh", 4, Assoc::Right, Arity::Unary, {}, "sinh", false, false, ""},
    OpSpec{OpId::Cosh, "cosh", 4, Assoc::Right, Arity::Unary, {}, "cosh", false, false, ""},
    OpSpec{OpId::Tanh, "tanh", 4, Assoc::Right, Arity::Unary, {}, "tanh", false, false, ""},
    OpSpec{OpId::Asin, "asin", 4, Assoc::Right, Arity::Unary, {}, "asin", true, false, "asin_acos"},
    OpSpec{OpId::Acos, "acos", 4, Assoc::Right, Arity::Unary, {}, "acos", true, false, "asin_acos"},
    OpSpec{OpId::Atan, "atan", 4, Assoc::Right, Arity::Unary, {}, "atan", true, false, ""},
    OpSpec{OpId::Asinh, "asinh", 4, Assoc::Right, Arity::Unary, {}, "asinh", false, false, ""},
    OpSpec{OpId::Acosh, "acosh", 4, Assoc::Right, Arity::Unary, {}, "acosh", false, false, "acosh"},
    OpSpec{OpId::Atanh, "atanh", 4, Assoc::Right, Arity::Unary, {}, "atanh", false, false, "atanh"},
    OpSpec{
        OpId::Polar, "∠", 4, Assoc::Right, Arity::Unary, {"polar", ""}, "polar", true, false, ""},

    OpSpec{OpId::Log,
           "log",
           4,
           Assoc::Right,
           Arity::Unary,
           {"log10", ""},
           "log",
           false,
           true,
           "log_ln"},
    OpSpec{OpId::Ln, "ln", 4, Assoc::Right, Arity::Unary, {}, "ln", false, true, "log_ln"},

    OpSpec{OpId::Recip, "⁻¹", 4, Assoc::Left, Arity::Postfix, {}, "recip", false, false, ""},
    OpSpec{OpId::Fact,
           "!",
           4,
           Assoc::Left,
           Arity::Postfix,
           {"factorial", "fact"},
           "fact",
           false,
           true,
           ""},

    OpSpec{OpId::Mod, "mod", 2, Assoc::Left, Arity::Binary, {}, "mod", false, true, ""},
    OpSpec{
        OpId::IntDiv, "div", 2, Assoc::Left, Arity::Binary, {"//", ""}, "intdiv", false, true, ""},

    OpSpec{OpId::Choose, "nCm", 4, Assoc::Right, Arity::Binary, {}, "choose", false, false, ""},
    OpSpec{OpId::Permute, "nPm", 4, Assoc::Right, Arity::Binary, {}, "permute", false, false, ""},
    OpSpec{
        OpId::Gamma, "Γ", 4, Assoc::Right, Arity::Unary, {"gamma", ""}, "gamma", false, true, ""},
    OpSpec{OpId::Cbrt, "³√", 4, Assoc::Right, Arity::Unary, {}, "cbrt", false, false, ""},

    OpSpec{OpId::Sqr, "²", 4, Assoc::Left, Arity::Postfix, {}, "sqr", false, false, ""},
    OpSpec{OpId::Cube, "³", 4, Assoc::Left, Arity::Postfix, {}, "cube", false, false, ""},
    OpSpec{OpId::Root, "⌄", 3, Assoc::Right, Arity::Binary, {}, "root", false, true, "root"},

    OpSpec{OpId::Exp, "exp", 4, Assoc::Right, Arity::Unary, {}, "exp", false, true, ""},
    OpSpec{OpId::Pow10, "⏨", 4, Assoc::Right, Arity::Unary, {}, "pow10", false, false, ""},
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
