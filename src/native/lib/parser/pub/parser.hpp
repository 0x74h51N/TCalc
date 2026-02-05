#pragma once

#include <cstdint>
#include <ostream>
#include <string>
#include <string_view>
#include <vector>

#include "parser/pub/ops.hpp"

namespace tcalc::parser {

using tcalc::ops::OpId;
using Value = std::string;

/// Token categories produced by the tokenizer.
enum class TokenKind : std::uint8_t {
    /// Numeric literal or constant token.
    Number,
    /// Operator token (OpId is set).
    Op,
    /// Left parenthesis.
    LParen,
    /// Right parenthesis.
    RParen,
    /// Compound expression (e.g., \frac{}{}, ^{}).
    Expr,
};

/// Expression kinds for compound Expr tokens.
enum class ExprKind : std::uint8_t {
    /// Fraction: \frac{numerator}{denominator}
    Frac,
    /// Power: \pow{base}{exponent}
    Pow,
    /// Root: \root{degree}{radicand}
    Root,
    /// Logarithm: \log{base}{value}
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
    LatexEntry{"\\log", ExprKind::Log, tcalc::ops::OpId::Log},
};

/// Parser token; numbers store raw text in value, ops store op_id.
struct Token {
    /// Token category.
    TokenKind kind;

    /// Operator id for op tokens, Count for non-ops.
    OpId op_id = OpId::Count;

    /// Raw number text for numeric tokens.
    Value value{};

    /// Expression kind for Expr tokens.
    ExprKind expr_kind = ExprKind::Frac;

    /// Left operand tokens for Expr (numerator/base).
    std::vector<Token> left_tokens{};

    /// Right operand tokens for Expr (denominator/exponent).
    std::vector<Token> right_tokens{};

    /// Start position in original string (metadata, not compared in ==).
    std::size_t start_pos = 0;

    /// End position in original string (metadata, not compared in ==).
    std::size_t end_pos = 0;

    /// Semantic equality - ignores position metadata.
    bool operator==(const Token &other) const {
        return kind == other.kind && op_id == other.op_id && value == other.value &&
               expr_kind == other.expr_kind && left_tokens == other.left_tokens &&
               right_tokens == other.right_tokens;
    }
};

/// Result of tokenization with metadata.
struct TokenizeResult {
    /// Token list.
    std::vector<Token> tokens{};

    /// Indices of Expr tokens in the token list.
    std::vector<std::size_t> expr_indices{};

    bool operator==(const TokenizeResult &) const = default;
};

inline std::ostream &operator<<(std::ostream &os, const Token &tok) {
    os << "Token{kind=" << static_cast<int>(tok.kind) << ", op_id=" << static_cast<int>(tok.op_id)
       << ", value=\"" << tok.value << "\"}";
    return os;
}

/// High-level tokenizer that understands LaTeX constructs (\frac, \sqrt, ...)
/// and produces a flat token stream suitable for shunting-yard parsing.
/// Returns TokenizeResult with tokens and expr_indices metadata.
TokenizeResult tokenize(std::string_view expression);

// Convert tokens to RPN using precedence/associativity rules.
std::vector<Token> shunting_yard(const std::vector<Token> &tokens);

} // namespace tcalc::parser
