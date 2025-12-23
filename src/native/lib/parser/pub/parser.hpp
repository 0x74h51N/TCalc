#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "parser/ops.hpp"

namespace tcalc::ops {

using Value = std::string;

enum class TokenKind : std::uint8_t { Number, Op, LParen, RParen };

struct Token {
    TokenKind kind;
    OpId op_id = OpId::Count;
    Value value{};
};

std::vector<Token> tokenize(std::string_view expression);
std::vector<Token> normalize(const std::vector<Token> &raw);
std::vector<Token> shunting_yard(const std::vector<Token> &tokens);

} // namespace tcalc::ops
