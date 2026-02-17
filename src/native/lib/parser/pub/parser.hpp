#pragma once

#include <cstdint>
#include <ostream>
#include <string>
#include <string_view>
#include <vector>
#include <variant>
#include "parser/pub/ops.hpp"

namespace tcalc::parser {

struct Token;

using tcalc::ops::OpId;
using Value = std::string;

enum class ParenType : uint8_t { Open, Close };

enum class ParenKind : uint8_t { Paren, Brace, Bracket };

struct Paren {
    std::string_view symbol;
    ParenType type;
    ParenKind kind;
};

constexpr std::array kParens = {
    Paren{"(", ParenType::Open, ParenKind::Paren},
    Paren{")", ParenType::Close, ParenKind::Paren},
    Paren{"{", ParenType::Open, ParenKind::Brace},
    Paren{"}", ParenType::Close, ParenKind::Brace},
    Paren{"[", ParenType::Open, ParenKind::Bracket},
    Paren{"]", ParenType::Close, ParenKind::Bracket}};

enum class TokenKind : std::uint8_t { Number, Op, Paren, Expr };

/// Expression kinds for compound Expr tokens.
enum class ExprKind : std::uint8_t {
    /// Fraction:
    /// \frac{numerator}{denominator}
    Frac,
    /// Power:
    /// \pow{base}{exponent}
    Pow,
    /// Root:
    /// \root{degree}{radicand}
    Root,
    /// Logarithm:
    /// \log{base}{value}
    Log,
};

/// LaTeX expression mapping: symbol -> ExprKind
struct LatexEntry {
    std::string_view symbol;
    ExprKind kind;
    OpId opid;
};

constexpr std::array kLatexExprs = {
    LatexEntry{"\\frac", ExprKind::Frac, tcalc::ops::OpId::Div},
    LatexEntry{"\\pow", ExprKind::Pow, tcalc::ops::OpId::Pow},
    LatexEntry{"\\root", ExprKind::Root, tcalc::ops::OpId::Root},
    LatexEntry{"\\log", ExprKind::Log, tcalc::ops::OpId::Log}};

/// Parser token;
/// numbers store raw text in value, ops store op_id.
struct NumberToken {
    std::string value;
    bool operator==(const NumberToken &) const = default;
};

struct OpToken {
    OpId op_id;
    bool operator==(const OpToken &) const = default;
};

struct ParenToken {
    ParenType type;
    ParenKind kind;
    bool operator==(const ParenToken &) const = default;
};

struct ExprToken {
    ExprKind kind;
    std::vector<Token> left;
    std::vector<Token> right;
    bool operator==(const ExprToken &) const = default;
};

using TokenData = std::variant<NumberToken, OpToken, ParenToken, ExprToken>;

struct Token {
    TokenKind kind;
    TokenData data;
    std::size_t start_pos = 0;
    std::size_t end_pos = 0;
};

struct TokenizeResult {
    std::vector<Token> tokens{};
    std::vector<std::size_t> expr_indices{};
    bool operator==(const TokenizeResult &) const = default;
};

inline std::ostream &operator<<(std::ostream &os, const Token &tok) {
    os << "Token{kind=" << static_cast<int>(tok.kind) << ", ";
    std::visit(
        [&](auto &&t) {
            using T = std::decay_t<decltype(t)>;
            if constexpr (std::is_same_v<T, NumberToken>)
                os << "value=\"" << t.value << "\"";
            else if constexpr (std::is_same_v<T, OpToken>)
                os << "op_id=" << static_cast<int>(t.op_id);
            else if constexpr (std::is_same_v<T, ParenToken>) {
                os << "paren_type=" << static_cast<int>(t.type)
                   << ", paren_kind=" << static_cast<int>(t.kind);
            } else if constexpr (std::is_same_v<T, ExprToken>) {
                os << "expr_kind=" << static_cast<int>(t.kind) << ", left.size=" << t.left.size()
                   << ", right.size=" << t.right.size();
            }
        },
        tok.data);
    os << "}";
    return os;
}

inline bool operator==(const Token &a, const Token &b) {
    if (a.kind != b.kind)
        return false;

    if (a.data.index() != b.data.index())
        return false;

    return std::visit(
        [&](const auto &lhs) -> bool {
            using T = std::decay_t<decltype(lhs)>;
            const auto *rhs = std::get_if<T>(&b.data);
            if (!rhs)
                return false;

            if constexpr (std::is_same_v<T, NumberToken>) {
                return lhs.value == rhs->value;
            } else if constexpr (std::is_same_v<T, OpToken>) {
                return lhs.op_id == rhs->op_id;
            } else if constexpr (std::is_same_v<T, ParenToken>) {
                return lhs.type == rhs->type && lhs.kind == rhs->kind;
            } else if constexpr (std::is_same_v<T, ExprToken>) {
                return lhs.kind == rhs->kind && lhs.left == rhs->left && lhs.right == rhs->right;
            }
            return false;
        },
        a.data);
}

/// High-level tokenizer that understands LaTeX constructs (\frac, \sqrt, ...) and produces a flat
/// token stream suitable for shunting-yard parsing. Returns TokenizeResult with tokens and
/// expr_indices metadata.
TokenizeResult tokenize(std::string_view expression);

// Convert tokens to RPN using precedence/associativity rules.
std::vector<Token> shunting_yard(const std::vector<Token> &tokens);

} // namespace tcalc::parser
