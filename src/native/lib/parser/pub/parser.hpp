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
};

/// Parser token; numbers store raw text in value, ops store op_id.
struct Token {
    /// Token category.
    TokenKind kind;

    /// Operator id for op tokens, Count for non-ops.
    OpId op_id = OpId::Count;

    /// Raw number text for numeric tokens.
    Value value{};

    bool operator==(const Token &) const = default;
};

inline std::ostream &operator<<(std::ostream &os, const Token &tok) {
    os << "Token{kind=" << static_cast<int>(tok.kind) << ", op_id=" << static_cast<int>(tok.op_id)
       << ", value=\"" << tok.value << "\"}";
    return os;
}

// Split an expression string into parser tokens.
std::vector<Token> tokenize(std::string_view expression);

// Convert tokens to RPN using precedence/associativity rules.
std::vector<Token> shunting_yard(const std::vector<Token> &tokens);

} // namespace tcalc::parser
