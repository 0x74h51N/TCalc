#pragma once

#include <cstddef>
#include <string>
#include <utility>
#include <vector>

#include "parser/pub/consts.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"

// Token builders shared by the parser and evaluator test suites. Fully qualified so a
// suite does not have to carry a matching set of using-declarations.
namespace tcalc::test_tokens {

using parser::CharToken;
using parser::ConstToken;
using parser::NumberToken;
using parser::OpToken;
using parser::ParenElement;
using parser::ParenKind;
using parser::ParenToken;
using parser::Token;
using parser::TokenKind;

/// NumberToken with the given literal value.
inline Token N(const char *value, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Number, NumberToken{value}, start, end};
}
/// OpToken for the given op id (binary, unary, or postfix).
inline Token Op_(ops::OpId id, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Op, OpToken{id}, start, end};
}
/// CharToken for the given character value.
inline Token Ch(char c, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Char, CharToken{c}, start, end};
}
/// ConstToken for the given constant id.
inline Token Co(consts::ConstId id, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Const, ConstToken{id}, start, end};
}

/// EN: single-Token number element (variant arm 0). Bare-number shortcut.
inline ParenElement EN(std::string value) {
    return ParenElement{Token{TokenKind::Number, NumberToken{std::move(value)}}};
}
/// EC: single-Token ConstToken element (variant arm 0).
inline ParenElement EC(consts::ConstId id) {
    return ParenElement{Token{TokenKind::Const, ConstToken{id}}};
}
/// EV: multi-Token element (variant arm 1). Expressions, postfix, unary signs.
inline ParenElement EV(std::vector<Token> toks) {
    return toks;
}

/// Unified ParenToken (open + elements + close). Auto-computes has_latex_descendant by
/// scanning elements, matching build_paren_token at tokenize time.
inline Token
Pr(ParenKind kind,
   std::vector<ParenElement> elements,
   bool has_open = true,
   bool has_close = true,
   std::size_t start = 0,
   std::size_t end = 0) {
    bool has_latex_descendant = false;
    auto contains_latex = [](const std::vector<Token> &toks) -> bool {
        for (const auto &t : toks) {
            if (t.kind == TokenKind::Latex)
                return true;
            if (t.kind == TokenKind::Paren && std::get<ParenToken>(t.data).has_latex_descendant)
                return true;
        }
        return false;
    };
    for (const auto &e : elements) {
        if (e.index() == 0) {
            const auto &t = std::get<Token>(e);
            if (t.kind == TokenKind::Latex) {
                has_latex_descendant = true;
                break;
            }
            if (t.kind == TokenKind::Paren && std::get<ParenToken>(t.data).has_latex_descendant) {
                has_latex_descendant = true;
                break;
            }
        } else if (contains_latex(std::get<std::vector<Token>>(e))) {
            has_latex_descendant = true;
            break;
        }
    }
    return Token{
        TokenKind::Paren,
        ParenToken{kind, std::move(elements), has_open, has_close, has_latex_descendant},
        start,
        end};
}

/// Round Paren wrapper, closed.
inline Token Pp(std::vector<ParenElement> elements, bool has_close = true) {
    return Pr(ParenKind::Paren, std::move(elements), true, has_close);
}
/// Square Bracket wrapper, closed.
inline Token Br(std::vector<ParenElement> elements, bool has_close = true) {
    return Pr(ParenKind::Bracket, std::move(elements), true, has_close);
}
/// Curly Brace wrapper, closed.
inline Token Bc(std::vector<ParenElement> elements, bool has_close = true) {
    return Pr(ParenKind::Brace, std::move(elements), true, has_close);
}

} // namespace tcalc::test_tokens
