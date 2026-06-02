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
#include <span>
#include <string>
#include <string_view>
#include <vector>
#include <optional>
#include <type_traits>
#include <utility>
#include <variant>
#include "parser/pub/ops.hpp"

namespace tcalc::parser {

struct Token;

using tcalc::ops::OpId;
using Value = std::string;

inline constexpr std::array<std::array<char, 3>, 2> kSymbolTable = {
    {{'(', '{', '['}, {')', '}', ']'}}};

/// Index into a token vector. uint32_t gives 2x cache density over size_t while
/// keeping native-width arithmetic on 64-bit targets (uint16_t forces zero-extends
/// after most ops). Inputs ≤ 4G tokens — practically unbounded for this calculator.
using TokenIndex = std::uint32_t;

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

enum class TokenKind : std::uint8_t { Number, Op, Paren, Latex, Collection };

/// Expression kinds for compound Latex tokens.
enum class LatexKind : std::uint8_t {
    /// Fraction:
    /// \frac{numerator}{denominator}
    Frac,
    /// Power:
    /// \pow{base}{exponent}
    Pow,
    /// Root:
    /// \root{radicand}{degree}
    Root,
    /// Logarithm:
    /// \log{base}{value}
    Log,
};

/// LaTeX expression mapping: symbol -> LatexKind
struct LatexEntry {
    std::string_view symbol;
    LatexKind kind;
    OpId opid;
};

constexpr std::array kLatexExprs = {
    LatexEntry{"\\frac", LatexKind::Frac, tcalc::ops::OpId::Div},
    LatexEntry{"\\pow", LatexKind::Pow, tcalc::ops::OpId::Pow},
    LatexEntry{"\\root", LatexKind::Root, tcalc::ops::OpId::Root},
    LatexEntry{"\\log", LatexKind::Log, tcalc::ops::OpId::Log}};

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
inline constexpr TokenIndex kNoMatch = static_cast<TokenIndex>(-1);

struct ParenToken {
    ParenType type{};
    ParenKind kind{};
    /// Token index of the matching open/close counterpart.
    /// Set by match_parens(); kNoMatch if unmatched.
    TokenIndex pair_idx = kNoMatch;

    /// Semantic equality: type + kind only (pair_idx is metadata).
    bool operator==(const ParenToken &o) const { return type == o.type && kind == o.kind; }
};

struct TokensBranch {
    std::vector<Token> tokens;
    std::vector<TokenIndex> latex_indices{};
    std::vector<TokenIndex> open_paren_indices{};
    std::vector<TokenIndex> close_paren_indices{};
    std::vector<TokenIndex> collection_indices{};
    bool operator==(const TokensBranch &) const = default;
};

struct LatexToken {
    LatexKind kind;
    OpId op_id;
    std::vector<Token> left;
    std::vector<Token> right;
    bool operator==(const LatexToken &) const = default;
};

enum class CollectionKind : std::uint8_t { List, Point };

using CollectionElement = std::variant<Token, std::vector<Token>>;

struct CollectionToken {
    CollectionKind kind;
    std::vector<CollectionElement> elements;
    bool closed;
    // Defined out-of-line below to defer variant<Token, vector<Token>>
    // instantiation until after Token is complete.
    bool operator==(const CollectionToken &) const;
};

using TokenData = std::variant<NumberToken, OpToken, ParenToken, LatexToken, CollectionToken>;

struct Token {
    TokenKind kind{};
    TokenData data{};
    std::size_t start_pos = 0;
    std::size_t end_pos = 0;
};

std::ostream &operator<<(std::ostream &, const Token &);

// ------------------------------------------------------------
// Shared visitor helper
// ------------------------------------------------------------
template <typename F> decltype(auto) visit_token(const TokenData &data, F &&f) {
    return std::visit(std::forward<F>(f), data);
}

// ------------------------------------------------------------
// Equality logic
// ------------------------------------------------------------
struct TokenEqual {
    const TokenData *rhs;

    template <typename T> bool operator()(const T &lhs) const {
        const auto *r = std::get_if<T>(rhs);
        if (!r)
            return false;

        if constexpr (std::is_same_v<T, NumberToken>) {
            return lhs.value == r->value;
        } else if constexpr (std::is_same_v<T, OpToken>) {
            return lhs.op_id == r->op_id;
        } else if constexpr (std::is_same_v<T, ParenToken>) {
            return lhs.type == r->type && lhs.kind == r->kind;
        } else if constexpr (std::is_same_v<T, LatexToken>) {
            return lhs.kind == r->kind && lhs.op_id == r->op_id && lhs.left == r->left &&
                   lhs.right == r->right;
        } else if constexpr (std::is_same_v<T, CollectionToken>) {
            return lhs.kind == r->kind && lhs.closed == r->closed && lhs.elements == r->elements;
        }
    }
};

// ------------------------------------------------------------
// operator==
// ------------------------------------------------------------
inline bool operator==(const Token &a, const Token &b) {
    if (a.kind != b.kind)
        return false;
    if (a.data.index() != b.data.index())
        return false;

    return visit_token(a.data, TokenEqual{&b.data});
}

// CollectionToken::operator== defined out-of-line so variant<Token, vector<Token>>
// special-member instantiation is deferred until Token is complete (above).
inline bool CollectionToken::operator==(const CollectionToken &o) const {
    return kind == o.kind && closed == o.closed && elements == o.elements;
}

/// Structural split payload for an (un)matched open paren appearing before the first latex token.
/// Spans reference tokens inside the source TokensBranch, caller must keep branch alive.
struct ParenSplit {
    std::span<const Token> prefix;
    std::span<const Token> left;
    std::span<const Token> suffix;
    ParenToken open_tok;
    std::optional<ParenToken> close_tok;

    bool has_close() const { return close_tok.has_value(); }
};

/// Structural split payload for a Frac/Pow/Root/Log latex token.
/// Spans reference tokens inside the source TokensBranch, caller must keep branch alive.
struct LatexSplit {
    std::span<const Token> prefix;
    std::span<const Token> left;
    std::span<const Token> right;
    std::span<const Token> suffix;
    LatexKind kind{};
};

/// Structural split payload for a CollectionToken (List or Point).
struct CollectionSplit {
    std::span<const Token> prefix;
    std::span<const CollectionElement> elements;
    std::span<const Token> suffix;
    CollectionKind kind{};
    bool has_close{};
};

using StructuralSplit = std::variant<ParenSplit, LatexSplit, CollectionSplit>;

/// Pair of token spans [begin, split_at) and [split_at, end) returned by split_operand.
/// Trailing (lead=false): (prefix, operand). Leading (lead=true): (operand, suffix).
using OperandSplit = std::pair<std::span<const Token>, std::span<const Token>>;

/// Extract leading/trailing operand from [begin, end) inside tokens.
OperandSplit
split_operand(std::span<const Token> tokens, TokenIndex begin, TokenIndex end, bool lead = false);

/// Find the next structural split point in branch: ParenSplit for an (un)matched open paren
/// before the first latex token, LatexSplit for Frac/Pow/Root/Log, nullopt when no latex tokens.
std::optional<StructuralSplit> structural_split(const TokensBranch &branch);

struct TextNode;
struct ParenNode;
struct LatexNode;
struct MathNode;

/// Discriminator for MathNode's payload; values match variant index order.
enum class MathNodeKind : std::uint8_t { Text = 0, Paren = 1, Latex = 2 };

/// Pre-formatted text run.
struct TextNode {
    std::string text;
    bool operator==(const TextNode &) const = default;
};

/// Paren group carrying its inner row.
struct ParenNode {
    ParenKind kind;
    bool has_close;
    std::vector<MathNode> children;
    bool operator==(const ParenNode &) const = default;
};

/// Latex expression (frac/pow/root/log) with left and right rows.
struct LatexNode {
    LatexKind kind;
    std::vector<MathNode> left;
    std::vector<MathNode> right;
    bool operator==(const LatexNode &) const = default;
};

/// Render-tree element: text run, paren group, or latex expression.
struct MathNode {
    std::variant<TextNode, ParenNode, LatexNode> data;

    MathNode() = default;
    template <typename T, typename = std::enable_if_t<!std::is_same_v<std::decay_t<T>, MathNode>>>
    MathNode(T &&v)
        : data(std::forward<T>(v)) {}

    MathNodeKind kind() const { return static_cast<MathNodeKind>(data.index()); }

    bool operator==(const MathNode &) const = default;
};

/// Build a flat row of MathNode descriptors ready for widget/paint construction.
/// Internally walks the token tree via structural_split, emits TextNode for runs between
/// structural nodes (tokens_to_text'd), and recurses into paren inner / expr left+right.
/// after_node: whether the row's first text is positioned right after a prior widget
/// (affects leading +/- spacing, matches tokens_to_text's after_node semantics).
std::vector<MathNode> build_math_nodes(const TokensBranch &branch, bool after_node = false);

/// High-level tokenizer that understands LaTeX constructs (\frac, \sqrt, ...) and produces a flat
/// token stream suitable for shunting-yard parsing. Returns TokensBranch with tokens and
/// latex_indices metadata.
TokensBranch tokenize(std::string_view expression);

/// Classify an existing token list: recompute local paren pair_idx metadata, then scan for
/// Expr / Open-Paren / Close-Paren tokens and populate the index vectors.
TokensBranch classify_tokens(std::vector<Token> tokens);

// Convert tokens to RPN using precedence/associativity rules.
std::vector<Token> shunting_yard(const std::vector<Token> &tokens);

/// Compile-time lookup table: LatexKind -> LaTeX symbol.
consteval auto build_latex_symbols() {
    constexpr auto count = static_cast<std::size_t>(LatexKind::Log) + 1;
    std::array<std::string_view, count> table{};
    for (const auto &entry : kLatexExprs) {
        table[static_cast<std::size_t>(entry.kind)] = entry.symbol;
    }
    return table;
}

inline constexpr auto kLatexSymbols = build_latex_symbols();

/// Format a LaTeX expression string: \symbol{left}{right}.
std::string format_expr_str(LatexKind kind, std::string_view left, std::string_view right);

/// Convert a single token to its display text representation.
std::string token_text(const Token &tok);

/// Convert a token list to display text in a single pass.
/// Binary operators get spaces around them.
std::string tokens_to_text(std::span<const Token> tokens, const bool &after_node = false);

/// Convert a single token to flat display text.
/// LatexTokens are flattened using op symbols (e.g. \frac{2}{3} → 2 ÷ 3);
/// all other token kinds delegate to token_text().
std::string token_flat_text(const Token &tok);

/// Convert a token list to flat display text in a single pass.
/// LaTeX expressions are flattened to infix notation with op symbols;
/// all other tokens are rendered identically to tokens_to_text().
std::string tokens_to_flat_text(const std::vector<Token> &tokens);

/// Format a single (op_id, text) pair with binary-op spacing if applicable.
std::string space_binary_op(ops::OpId op_id, const std::string &text, const bool &after_node);

} // namespace tcalc::parser
