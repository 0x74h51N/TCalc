/*
 *
 *  TCalc is a native-powered scientific desktop calculator designed
 *  for high-performance, precision, and a superior user experience.
 *  Copyright (C) 2025 Tahsin Önemli
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#pragma once

#include <cstdint>
#include <ostream>
#include <string>
#include <string_view>
#include <vector>
#include <optional>
#include <variant>
#include "parser/pub/ops.hpp"

namespace tcalc::parser {

struct Token;

using tcalc::ops::OpId;
using Value = std::string;

inline constexpr std::array<std::array<char, 3>, 2> kSymbolTable = {
    {{'(', '{', '['}, {')', '}', ']'}}};

enum class ParenType : std::uint8_t { Open = 0, Close = 1 };

enum class ParenKind : std::uint8_t { Paren = 0, Brace = 1, Bracket = 2 };

struct Paren {
    ParenType type;
    ParenKind kind;
};
inline constexpr std::size_t kAsciiTableSize = 256;

inline constexpr std::array<std::optional<Paren>, kAsciiTableSize> make_paren_table() {
    std::array<std::optional<Paren>, kAsciiTableSize> table{};

    table['('] = Paren{ParenType::Open, ParenKind::Paren};
    table[')'] = Paren{ParenType::Close, ParenKind::Paren};

    table['{'] = Paren{ParenType::Open, ParenKind::Brace};
    table['}'] = Paren{ParenType::Close, ParenKind::Brace};

    table['['] = Paren{ParenType::Open, ParenKind::Bracket};
    table[']'] = Paren{ParenType::Close, ParenKind::Bracket};

    return table;
}

inline constexpr auto kParenTable = make_paren_table();

/// Lookup paren by character from kParens table.
inline constexpr std::optional<Paren> match_paren(char c) {
    return kParenTable[static_cast<unsigned char>(c)];
}

/// Return the symbol character for a paren type+kind pair.
inline constexpr char paren_symbol(ParenType type, ParenKind kind) {
    return kSymbolTable[static_cast<int>(type)][static_cast<int>(kind)];
}

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

/// npos sentinel for unmatched parentheses.
inline constexpr std::size_t kNoMatch = static_cast<std::size_t>(-1);

struct ParenToken {
    ParenType type;
    ParenKind kind;
    /// Token index of the matching open/close counterpart.
    /// Set by match_parens(); kNoMatch if unmatched.
    std::size_t pair_idx = kNoMatch;

    /// Semantic equality: type + kind only (pair_idx is metadata).
    bool operator==(const ParenToken &o) const { return type == o.type && kind == o.kind; }
};

struct ExprToken {
    ExprKind kind;
    std::vector<Token> left;
    std::vector<Token> right;
    bool operator==(const ExprToken &) const = default;
};

using TokenData = std::variant<NumberToken, OpToken, ParenToken, ExprToken>;

struct Token {
    TokenKind kind{};
    TokenData data{};
    std::size_t start_pos = 0;
    std::size_t end_pos = 0;
};

struct TokenizeResult {
    std::vector<Token> tokens{};
    std::vector<std::size_t> expr_indices{};
    std::vector<std::size_t> open_paren_indices{};
    std::vector<std::size_t> close_paren_indices{};
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

/// Compile-time lookup table: ExprKind -> LaTeX symbol.
consteval auto build_latex_symbols() {
    constexpr auto count = static_cast<std::size_t>(ExprKind::Log) + 1;
    std::array<std::string_view, count> table{};
    for (const auto &entry : kLatexExprs) {
        table[static_cast<std::size_t>(entry.kind)] = entry.symbol;
    }
    return table;
}

inline constexpr auto kLatexSymbols = build_latex_symbols();

/// Format a LaTeX expression string: \symbol{left}{right}.
std::string format_expr_str(ExprKind kind, std::string_view left, std::string_view right);

/// Convert a single token to its display text representation.
std::string token_text(const Token &tok);

/// Convert a token list to display text in a single pass.
/// Binary operators get spaces around them.
std::string tokens_to_text(const std::vector<Token> &tokens, const bool &after_node = false);

/// Convert a single token to flat display text.
/// ExprTokens are flattened using op symbols (e.g. \frac{2}{3} → 2 ÷ 3);
/// all other token kinds delegate to token_text().
std::string token_flat_text(const Token &tok);

/// Convert a token list to flat display text in a single pass.
/// LaTeX expressions are flattened to infix notation with op symbols;
/// all other tokens are rendered identically to tokens_to_text().
std::string tokens_to_flat_text(const std::vector<Token> &tokens);

/// Format a single (op_id, text) pair with binary-op spacing if applicable.
std::string space_binary_op(ops::OpId op_id, const std::string &text, const bool &after_node);

} // namespace tcalc::parser
