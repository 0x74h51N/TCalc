#include <string>
#include <string_view>
#include <vector>

#include "internal/parser_internal.hpp"
#include "internal/test_helpers.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"

namespace p = tcalc::parser;
namespace o = tcalc::ops;
namespace d = p::detail;

using o::OpId;
using p::LatexKind;
using p::LatexToken;
using p::NumberToken;
using p::OpToken;
using p::ParenKind;
using p::ParenToken;
using p::ParenType;
using p::Token;
using p::TokenKind;
using p::TokensBranch;

namespace {

template <typename InputT, typename ExpectedT> struct Case {
    const char *id;
    InputT input;
    ExpectedT expected;
};

struct ScanInput {
    std::string_view text;
    std::size_t start;
};

struct ScanExpected {
    std::string_view view;
    std::size_t next;
};

using TokCase = Case<const char *, std::vector<tcalc::parser::Token>>;
using ScanCase = Case<ScanInput, ScanExpected>;
using NormCase = Case<std::vector<Token>, std::vector<Token>>;
using ShuntCase = Case<std::vector<Token>, std::vector<Token>>;

inline constexpr ParenToken kPOP{ParenType::Open, ParenKind::Paren};
inline constexpr ParenToken kPCL{ParenType::Close, ParenKind::Paren};
inline const Token kOPN{TokenKind::Paren, kPOP};
inline const Token kCPN{TokenKind::Paren, kPCL};

// Token factories. start/end default to 0
// pass them only when the test actually checks span info
inline Token N(const char *value, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Number, NumberToken{value}, start, end};
}
inline Token Op_(OpId id, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Op, OpToken{id}, start, end};
}
inline Token OpenP(ParenKind kind = ParenKind::Paren, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Paren, ParenToken{ParenType::Open, kind}, start, end};
}
inline Token CloseP(ParenKind kind = ParenKind::Paren, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Paren, ParenToken{ParenType::Close, kind}, start, end};
}
inline Token
Lx(p::LatexKind kind,
   OpId op,
   std::vector<Token> left,
   std::vector<Token> right,
   std::size_t start = 0,
   std::size_t end = 0) {
    return Token{
        TokenKind::Latex, LatexToken{kind, op, std::move(left), std::move(right)}, start, end};
}
inline Token Frac(
    std::vector<Token> numerator,
    std::vector<Token> denominator,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(
        p::LatexKind::Frac, OpId::Div, std::move(numerator), std::move(denominator), start, end);
}
inline Token
Pow(std::vector<Token> base,
    std::vector<Token> exponent,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(p::LatexKind::Pow, OpId::Pow, std::move(base), std::move(exponent), start, end);
}
inline Token Root(
    std::vector<Token> degree,
    std::vector<Token> radicand,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(p::LatexKind::Root, OpId::Root, std::move(degree), std::move(radicand), start, end);
}

} // namespace

/// TODO: Add math_node tests

void unit_parser(TestContext &ctx) {

    // Tokenizations
    const std::vector<TokCase> tok_cases = {
        {.id = "basic add",
         .input = "1+2",
         .expected = {N("1", 0, 1), Op_(OpId::Add, 1, 2), N("2", 2, 3)}},

        {.id = "leading negate decimal",
         .input = "-3.5",
         .expected = {Op_(OpId::Negate, 0, 1), N("3.5", 1, 4)}},

        {.id = "negate then plus",
         .input = "-+2",
         .expected = {Op_(OpId::Negate, 0, 1), Op_(OpId::UnaryPlus, 1, 2), N("2", 2, 3)}},

        {.id = "func parens imag",
         .input = "sin(2i)",
         .expected =
             {Op_(OpId::Sin, 0, 3),
              OpenP(ParenKind::Paren, 3, 4),
              N("2i", 4, 6),
              CloseP(ParenKind::Paren, 6, 7)}},

        {.id = "spacing and unicode",
         .input = "-2 ³√( 3 ( π ",
         .expected =
             {Op_(OpId::Negate, 0, 1),
              N("2", 1, 2),
              Op_(OpId::Cbrt, 3, 4),
              OpenP(ParenKind::Paren, 4, 5),
              N("3", 6, 7),
              OpenP(ParenKind::Paren, 8, 9),
              N("π", 10, 11)}},

        {.id = "sci notation imag", .input = "1.2e-3i", .expected = {N("1.2e-3i", 0, 7)}},

        {.id = "binary plus unary minus",
         .input = "1+-2",
         .expected = {N("1", 0, 1), Op_(OpId::Add, 1, 2), Op_(OpId::Negate, 2, 3), N("2", 3, 4)}},

        {.id = "negate in parens",
         .input = "(-2)",
         .expected =
             {OpenP(ParenKind::Paren, 0, 1),
              Op_(OpId::Negate, 1, 2),
              N("2", 2, 3),
              CloseP(ParenKind::Paren, 3, 4)}},

        {.id = "asinh parens",
         .input = "asinh(2)",
         .expected =
             {Op_(OpId::Asinh, 0, 5),
              OpenP(ParenKind::Paren, 5, 6),
              N("2", 6, 7),
              CloseP(ParenKind::Paren, 7, 8)}},

        {.id = "sqrt parens",
         .input = "sqrt(2)",
         .expected =
             {Op_(OpId::Sqrt, 0, 4),
              OpenP(ParenKind::Paren, 4, 5),
              N("2", 5, 6),
              CloseP(ParenKind::Paren, 6, 7)}},

        {.id = "postfix unicode", .input = "2³", .expected = {N("2", 0, 1), Op_(OpId::Cube, 1, 2)}},

        // == Paren types ==============================================

        {.id = "curly braces",
         .input = "{1+2}",
         .expected =
             {OpenP(ParenKind::Brace, 0, 1),
              N("1", 1, 2),
              Op_(OpId::Add, 2, 3),
              N("2", 3, 4),
              CloseP(ParenKind::Brace, 4, 5)}},

        {.id = "square brackets",
         .input = "[3+4]",
         .expected =
             {OpenP(ParenKind::Bracket, 0, 1),
              N("3", 1, 2),
              Op_(OpId::Add, 2, 3),
              N("4", 3, 4),
              CloseP(ParenKind::Bracket, 4, 5)}},

        {.id = "mixed paren kinds",
         .input = "({[1]})",
         .expected =
             {OpenP(ParenKind::Paren, 0, 1),
              OpenP(ParenKind::Brace, 1, 2),
              OpenP(ParenKind::Bracket, 2, 3),
              N("1", 3, 4),
              CloseP(ParenKind::Bracket, 4, 5),
              CloseP(ParenKind::Brace, 5, 6),
              CloseP(ParenKind::Paren, 6, 7)}},

        {.id = "negate inside curly",
         .input = "{-2}",
         .expected =
             {OpenP(ParenKind::Brace, 0, 1),
              Op_(OpId::Negate, 1, 2),
              N("2", 2, 3),
              CloseP(ParenKind::Brace, 3, 4)}},

        // == LatexToken (LaTeX) ========================================

        {.id = "frac simple",
         .input = "\\frac{2}{3}",
         .expected = {Frac({N("2")}, {N("3")}, 0, 11)}},

        {.id = "pow simple", .input = "\\pow{5}{2}", .expected = {Pow({N("5")}, {N("2")}, 0, 10)}},

        {.id = "root simple",
         .input = "\\root{8}{3}",
         .expected = {Root({N("8")}, {N("3")}, 0, 11)}},

        {.id = "frac with inner expr",
         .input = "\\frac{2+3}{4}",
         .expected = {Frac({N("2"), Op_(OpId::Add), N("3")}, {N("4")}, 0, 13)}},

        {.id = "frac nested in frac",
         .input = "\\frac{\\frac{1}{2}}{3}",
         .expected = {Frac({Frac({N("1")}, {N("2")})}, {N("3")}, 0, 21)}},

        {.id = "frac with pow inside",
         .input = "\\frac{\\pow{4}{2}}{3}",
         .expected = {Frac({Pow({N("4")}, {N("2")})}, {N("3")}, 0, 20)}},

        // == Mixed: plain tokens + LatexToken ==========================

        {.id = "number then frac",
         .input = "1+\\frac{2}{3}",
         .expected = {N("1", 0, 1), Op_(OpId::Add, 1, 2), Frac({N("2")}, {N("3")}, 2, 13)}},

        {.id = "frac between numbers",
         .input = "1+\\frac{2}{3}+4",
         .expected =
             {N("1", 0, 1),
              Op_(OpId::Add, 1, 2),
              Frac({N("2")}, {N("3")}, 2, 13),
              Op_(OpId::Add, 13, 14),
              N("4", 14, 15)}},

        // == User curly braces inside LaTeX args ======================

        {.id = "user brace inside frac numerator",
         .input = "\\frac{{1+2}}{3}",
         .expected = {Frac(
             {OpenP(ParenKind::Brace), N("1"), Op_(OpId::Add), N("2"), CloseP(ParenKind::Brace)},
             {N("3")},
             0,
             15)}},

        {.id = "user brace around frac",
         .input = "{\\frac{1}{2}}",
         .expected =
             {OpenP(ParenKind::Brace, 0, 1),
              Frac({N("1")}, {N("2")}, 1, 12),
              CloseP(ParenKind::Brace, 12, 13)}},

        {.id = "complex nested: frac with user brace and inner pow",
         .input = "\\frac{{\\pow{4}{2}}}{3}",
         .expected = {Frac(
             {OpenP(ParenKind::Brace), Pow({N("4")}, {N("2")}), CloseP(ParenKind::Brace)},
             {N("3")},
             0,
             22)}},

        {.id = "curly brace then number plain",
         .input = "2{3+4}+5",
         .expected =
             {N("2", 0, 1),
              OpenP(ParenKind::Brace, 1, 2),
              N("3", 2, 3),
              Op_(OpId::Add, 3, 4),
              N("4", 4, 5),
              CloseP(ParenKind::Brace, 5, 6),
              Op_(OpId::Add, 6, 7),
              N("5", 7, 8)}},

        /// TODO: Add more latex and paren tokenize edge cases
    };

    // Normalizations
    // Token::operator== ignores positions, so we drop them here to keep cases
    // dense — only kind/data semantics matter for normalize().
    const std::vector<NormCase> norm_cases = {

        {.id = "double sub to add",
         .input = {N("1"), Op_(OpId::Sub), Op_(OpId::Sub), N("2")},
         .expected = {N("1"), Op_(OpId::Add), N("2")}},

        {.id = "add sub to sub",
         .input = {N("1"), Op_(OpId::Add), Op_(OpId::Sub), N("2")},
         .expected = {N("1"), Op_(OpId::Sub), N("2")}},

        {.id = "mixed sign collapse",
         .input =
             {N("1"),
              Op_(OpId::Add),
              Op_(OpId::Sub),
              Op_(OpId::Sub),
              Op_(OpId::Sub),
              Op_(OpId::Add),
              Op_(OpId::Add),
              Op_(OpId::Sub),
              Op_(OpId::Sub),
              Op_(OpId::Add),
              Op_(OpId::Add),
              N("2")},
         .expected = {N("1"), Op_(OpId::Sub), N("2")}},

        {.id = "add then negate kept",
         .input = {N("1"), Op_(OpId::Add), Op_(OpId::Negate), N("2")},
         .expected = {N("1"), Op_(OpId::Add), Op_(OpId::Negate), N("2")}},

        // Implicit multiplications
        {.id = "implicit mul before lparen",
         .input = {N("2"), kOPN, N("3")},
         .expected = {N("2"), Op_(OpId::Mul), kOPN, N("3")}},

        {.id = "implicit mul after postfix",
         .input = {N("3"), Op_(OpId::Fact), N("2")},
         .expected = {N("3"), Op_(OpId::Fact), Op_(OpId::Mul), N("2")}}};

    // Scanifications
    const std::vector<ScanCase> scan_cases = {
        {.id = "integer",
         .input = {.text = "123", .start = 0},
         .expected = {.view = "123", .next = 3}},
        {.id = "decimal",
         .input = {.text = "12.34", .start = 0},
         .expected = {.view = "12.34", .next = 5}},
        {.id = "leading dot",
         .input = {.text = ".5", .start = 0},
         .expected = {.view = ".5", .next = 2}},
        {.id = "trailing dot",
         .input = {.text = "5.", .start = 0},
         .expected = {.view = "5.", .next = 2}},
        {.id = "sci basic",
         .input = {.text = "1e10", .start = 0},
         .expected = {.view = "1e10", .next = 4}},
        {.id = "sci negative exp",
         .input = {.text = "1e-3", .start = 0},
         .expected = {.view = "1e-3", .next = 4}},
        {.id = "sci positive exp",
         .input = {.text = "1e+0", .start = 0},
         .expected = {.view = "1e+0", .next = 4}},
        {.id = "sci incomplete",
         .input = {.text = "1e+", .start = 0},
         .expected = {.view = "1", .next = 1}},
        {.id = "sci imag prefix",
         .input = {.text = "1e-3i", .start = 0},
         .expected = {.view = "1e-3", .next = 4}},
        {.id = "scan mid string",
         .input = {.text = "xx12.3", .start = 2},
         .expected = {.view = "12.3", .next = 6}},
        {.id = "no number",
         .input = {.text = "abc", .start = 0},
         .expected = {.view = "", .next = 0}},
        {.id = "dot only", .input = {.text = ".", .start = 0}, .expected = {.view = "", .next = 0}},
    };

    // Shuntifications
    const std::vector<ShuntCase> shunt_cases = {

        {.id = "basic precedence",
         .input =
             {
                 N("1"),
                 Op_(OpId::Add),
                 N("2"),
                 Op_(OpId::Mul),
                 N("3"),
                 Op_(OpId::Pow),
                 N("4"),
             },
         .expected =
             {
                 N("1"),
                 N("2"),
                 N("3"),
                 N("4"),
                 Op_(OpId::Pow),
                 Op_(OpId::Mul),
                 Op_(OpId::Add),
             }},

        {.id = "pow right assoc",
         .input =
             {
                 N("2"),
                 Op_(OpId::Pow),
                 N("3"),
                 Op_(OpId::Pow),
                 N("4"),
             },
         .expected =
             {
                 N("2"),
                 N("3"),
                 N("4"),
                 Op_(OpId::Pow),
                 Op_(OpId::Pow),
             }},

        {.id = "unary before func",
         .input =
             {
                 Op_(OpId::Sin),
                 Op_(OpId::Negate),
                 N("2"),
             },
         .expected =
             {
                 N("2"),
                 Op_(OpId::Negate),
                 Op_(OpId::Sin),
             }},

        {.id = "implicit mul after rparen",
         .input =
             {
                 N("2"),
                 kOPN,
                 N("3"),
                 Op_(OpId::Add),
                 N("4"),
                 kCPN,
             },
         .expected =
             {
                 N("2"),
                 N("3"),
                 N("4"),
                 Op_(OpId::Add),
                 Op_(OpId::Mul),
             }},

        {.id = "postfix percent precedence",
         .input =
             {
                 N("2"),
                 Op_(OpId::Pow),
                 N("3"),
                 Op_(OpId::Percent),
                 Op_(OpId::Add),
                 N("4"),
             },
         .expected =
             {
                 N("2"),
                 N("3"),
                 Op_(OpId::Percent),
                 Op_(OpId::Pow),
                 N("4"),
                 Op_(OpId::Add),
             }},
    };

    for (std::size_t i = 0; i < tok_cases.size(); ++i) {
        const auto &tc = tok_cases[i];
        test_detail::with_case(ctx, std::string("tokenize :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, p::tokenize(tc.input).tokens, tc.expected);
        });
    }

    // Token position tests
    test_detail::with_case(ctx, "positions :: simple expr", [&] {
        const auto result = p::tokenize("3 + 5");
        EXPECT_EQ(ctx, result.tokens.size(), 3UL);
        // "3" at pos 0
        EXPECT_EQ(ctx, result.tokens[0].start_pos, 0UL);
        EXPECT_EQ(ctx, result.tokens[0].end_pos, 1UL);
        // "+" at pos 2
        EXPECT_EQ(ctx, result.tokens[1].start_pos, 2UL);
        EXPECT_EQ(ctx, result.tokens[1].end_pos, 3UL);
        // "5" at pos 4
        EXPECT_EQ(ctx, result.tokens[2].start_pos, 4UL);
        EXPECT_EQ(ctx, result.tokens[2].end_pos, 5UL);
    });

    test_detail::with_case(ctx, "positions :: frac expr", [&] {
        const auto result = p::tokenize("\\frac{2}{3}");
        EXPECT_EQ(ctx, result.tokens.size(), 1UL);
        EXPECT_EQ(ctx, result.latex_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.latex_indices[0], 0UL);
        // \frac{2}{3} spans 0-11
        EXPECT_EQ(ctx, result.tokens[0].start_pos, 0UL);
        EXPECT_EQ(ctx, result.tokens[0].end_pos, 11UL);
    });

    test_detail::with_case(ctx, "positions :: mixed", [&] {
        const auto result = p::tokenize("1 + \\frac{2}{3} + 4");
        EXPECT_EQ(ctx, result.tokens.size(), 5UL);
        EXPECT_EQ(ctx, result.latex_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.latex_indices[0], 2UL);
        // "1" at 0-1
        EXPECT_EQ(ctx, result.tokens[0].start_pos, 0UL);
        EXPECT_EQ(ctx, result.tokens[0].end_pos, 1UL);
        // "+" at 2-3
        EXPECT_EQ(ctx, result.tokens[1].start_pos, 2UL);
        EXPECT_EQ(ctx, result.tokens[1].end_pos, 3UL);
        // \frac{2}{3} at 4-15
        EXPECT_EQ(ctx, result.tokens[2].start_pos, 4UL);
        EXPECT_EQ(ctx, result.tokens[2].end_pos, 15UL);
        // "+" at 16-17
        EXPECT_EQ(ctx, result.tokens[3].start_pos, 16UL);
        EXPECT_EQ(ctx, result.tokens[3].end_pos, 17UL);
        // "4" at 18-19
        EXPECT_EQ(ctx, result.tokens[4].start_pos, 18UL);
        EXPECT_EQ(ctx, result.tokens[4].end_pos, 19UL);
    });

    test_detail::with_case(ctx, "positions :: multiple expr", [&] {
        const auto result = p::tokenize("\\frac{1}{2} + \\pow{3}{4}");
        EXPECT_EQ(ctx, result.tokens.size(), 3UL);
        EXPECT_EQ(ctx, result.latex_indices.size(), 2UL);
        EXPECT_EQ(ctx, result.latex_indices[0], 0UL);
        EXPECT_EQ(ctx, result.latex_indices[1], 2UL);
        // \frac{1}{2} at 0-11
        EXPECT_EQ(ctx, result.tokens[0].start_pos, 0UL);
        EXPECT_EQ(ctx, result.tokens[0].end_pos, 11UL);
        // \pow{3}{4} at 14-24
        EXPECT_EQ(ctx, result.tokens[2].start_pos, 14UL);
        EXPECT_EQ(ctx, result.tokens[2].end_pos, 24UL);
    });

    for (std::size_t i = 0; i < norm_cases.size(); ++i) {
        const auto &tc = norm_cases[i];
        test_detail::with_case(ctx, std::string("normalize :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, d::normalize(tc.input), tc.expected);
        });
    }

    for (std::size_t i = 0; i < scan_cases.size(); ++i) {
        const auto &tc = scan_cases[i];
        test_detail::with_case(ctx, std::string("scan number :: ") + tc.id, [&] {
            std::size_t next = tc.input.start;
            const std::string_view view = d::scan_number(tc.input.text, tc.input.start, next);
            EXPECT_EQ(ctx, view, tc.expected.view);
            EXPECT_EQ(ctx, next, tc.expected.next);
        });
    }

    for (std::size_t i = 0; i < shunt_cases.size(); ++i) {
        const auto &tc = shunt_cases[i];
        test_detail::with_case(ctx, std::string("shunting yard :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, p::shunting_yard(tc.input), tc.expected);
        });
    }

    //  match_parens

    const auto pair_of = [](const std::vector<Token> &toks, std::size_t idx) -> std::size_t {
        return std::get<ParenToken>(toks[idx].data).pair_idx;
    };

    test_detail::with_case(ctx, "match_parens :: simple parens", [&] {
        // (1+2) -> tokens: ( 1 + 2 )   indices: 0 1 2 3 4
        auto result = p::tokenize("(1+2)");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), 4UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 4), 0UL);
    });

    test_detail::with_case(ctx, "match_parens :: nested same kind", [&] {
        // ((1)) -> ( ( 1 ) )   indices: 0 1 2 3 4
        auto result = p::tokenize("((1))");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), 4UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 1), 3UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 3), 1UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 4), 0UL);
    });

    test_detail::with_case(ctx, "match_parens :: mixed kinds nested", [&] {
        // ({[1]}) -> ( { [ 1 ] } )   indices: 0 1 2 3 4 5 6
        auto result = p::tokenize("({[1]})");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), 6UL); // ( <-> )
        EXPECT_EQ(ctx, pair_of(result.tokens, 1), 5UL); // { <-> }
        EXPECT_EQ(ctx, pair_of(result.tokens, 2), 4UL); // [ <-> ]
        EXPECT_EQ(ctx, pair_of(result.tokens, 4), 2UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 5), 1UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 6), 0UL);
    });

    test_detail::with_case(ctx, "match_parens :: sequential groups", [&] {
        // (1)+(2) -> ( 1 ) + ( 2 )   indices: 0 1 2 3 4 5 6
        auto result = p::tokenize("(1)+(2)");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), 2UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 2), 0UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 4), 6UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 6), 4UL);
    });

    test_detail::with_case(ctx, "match_parens :: unmatched open", [&] {
        // (1+2 -> ( 1 + 2
        auto result = p::tokenize("(1+2");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), p::kNoMatch);
    });

    test_detail::with_case(ctx, "match_parens :: unmatched close", [&] {
        // 1+2) -> 1 + 2 )
        auto result = p::tokenize("1+2)");
        EXPECT_EQ(ctx, pair_of(result.tokens, 3), p::kNoMatch);
    });

    test_detail::with_case(ctx, "match_parens :: complex expression", [&] {
        // [(34+5)*(4*{3+5})+4]
        // [  (  34 +  5  )  *  (  4  *  {  3  +  5  }  )  +  4  ]
        // 0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18
        auto result = p::tokenize("[(34+5)*(4*{3+5})+4]");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), 18UL); // [ <-> ]
        EXPECT_EQ(ctx, pair_of(result.tokens, 1), 5UL);  // ( <-> )
        EXPECT_EQ(ctx, pair_of(result.tokens, 5), 1UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 7), 15UL);  // ( <-> )
        EXPECT_EQ(ctx, pair_of(result.tokens, 10), 14UL); // { <-> }
        EXPECT_EQ(ctx, pair_of(result.tokens, 14), 10UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 15), 7UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 18), 0UL);
    });

    test_detail::with_case(ctx, "match_parens :: no parens", [&] {
        auto result = p::tokenize("1+2");
        // No paren tokens, nothing to check, ensure no crash.
        EXPECT_EQ(ctx, result.tokens.size(), 3UL);
    });

    test_detail::with_case(ctx, "classify_tokens :: rebase nested slice pairs", [&] {
        auto result = p::tokenize("(1)+{2+[\\pow{2}{3}]+4}");
        std::vector<Token> slice(result.tokens.begin() + 5, result.tokens.begin() + 12);

        auto classified = p::classify_tokens(std::move(slice));
        EXPECT_EQ(ctx, classified.open_paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, classified.open_paren_indices[0], 2UL);
        EXPECT_EQ(ctx, classified.close_paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, classified.close_paren_indices[0], 4UL);
        EXPECT_EQ(ctx, pair_of(classified.tokens, 2), 4UL);
        EXPECT_EQ(ctx, pair_of(classified.tokens, 4), 2UL);
    });

    test_detail::with_case(ctx, "classify_tokens :: unmatched outer pair stays open", [&] {
        auto result = p::tokenize("({[1]})");
        std::vector<Token> slice(result.tokens.begin() + 1, result.tokens.begin() + 5);

        auto classified = p::classify_tokens(std::move(slice));
        EXPECT_EQ(ctx, classified.open_paren_indices.size(), 2UL);
        EXPECT_EQ(ctx, classified.open_paren_indices[0], 0UL);
        EXPECT_EQ(ctx, classified.open_paren_indices[1], 1UL);
        EXPECT_EQ(ctx, classified.close_paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, classified.close_paren_indices[0], 3UL);
        EXPECT_EQ(ctx, pair_of(classified.tokens, 0), p::kNoMatch);
        EXPECT_EQ(ctx, pair_of(classified.tokens, 1), 3UL);
        EXPECT_EQ(ctx, pair_of(classified.tokens, 3), 1UL);
    });

    // paren_indices

    test_detail::with_case(ctx, "paren_indices :: no parens", [&] {
        auto result = p::tokenize("1+2");
        EXPECT_EQ(ctx, result.open_paren_indices.size(), 0UL);
        EXPECT_EQ(ctx, result.close_paren_indices.size(), 0UL);
    });

    test_detail::with_case(ctx, "paren_indices :: simple parens", [&] {
        // (1+2) -> ( 1 + 2 )
        // Only open paren at index 0
        auto result = p::tokenize("(1+2)");
        EXPECT_EQ(ctx, result.open_paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.open_paren_indices[0], 0UL);
        EXPECT_EQ(ctx, result.close_paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.close_paren_indices[0], 4UL);
    });

    test_detail::with_case(ctx, "paren_indices :: nested", [&] {
        // ((1)) -> ( ( 1 ) )
        // Open parens at 0 and 1
        auto result = p::tokenize("((1");
        EXPECT_EQ(ctx, result.open_paren_indices.size(), 2UL);
        EXPECT_EQ(ctx, result.open_paren_indices[0], 0UL);
        EXPECT_EQ(ctx, result.open_paren_indices[1], 1UL);
        EXPECT_EQ(ctx, result.close_paren_indices.size(), 0UL);
    });

    test_detail::with_case(ctx, "paren_indices :: mixed kinds", [&] {
        // ({[1]}) -> ( { [ 1 ] } )
        // Open parens at 0, 1, 2
        auto result = p::tokenize("({[1]})");
        EXPECT_EQ(ctx, result.open_paren_indices.size(), 3UL);
        EXPECT_EQ(ctx, result.open_paren_indices[0], 0UL);
        EXPECT_EQ(ctx, result.open_paren_indices[1], 1UL);
        EXPECT_EQ(ctx, result.open_paren_indices[2], 2UL);
    });

    test_detail::with_case(ctx, "paren_indices :: sequential groups", [&] {
        // (1)+(2) -> ( 1 ) + ( 2 )
        // Open parens at 0 and 4
        auto result = p::tokenize("(1+(2)");
        EXPECT_EQ(ctx, result.open_paren_indices.size(), 2UL);
        EXPECT_EQ(ctx, result.open_paren_indices[0], 0UL);
        EXPECT_EQ(ctx, result.open_paren_indices[1], 3UL);
        EXPECT_EQ(ctx, result.close_paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.close_paren_indices[0], 5UL);
    });

    test_detail::with_case(ctx, "paren_indices :: with expr", [&] {
        // {\\frac{1}{2}} -> { \frac{1}{2} }   tokens: { Expr }
        // Open brace at 0
        auto result = p::tokenize("{\\frac{1}{2}}");
        EXPECT_EQ(ctx, result.open_paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.open_paren_indices[0], 0UL);
        EXPECT_EQ(ctx, result.close_paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.close_paren_indices[0], 2UL);
        EXPECT_EQ(ctx, result.latex_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.latex_indices[0], 1UL);
    });

    test_detail::with_case(ctx, "paren_indices :: expr only no parens", [&] {
        auto result = p::tokenize("\\frac{1}{2}");
        EXPECT_EQ(ctx, result.open_paren_indices.size(), 0UL);
        EXPECT_EQ(ctx, result.close_paren_indices.size(), 0UL);
        EXPECT_EQ(ctx, result.latex_indices.size(), 1UL);
    });

    // =========================================================================
    // tokens_to_text
    // =========================================================================

    test_detail::with_case(ctx, "tokens_to_text :: simple binary", [&] {
        std::vector<Token> toks = {
            N("2"),
            Op_(OpId::Add),
            N("3"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("2 + 3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: leading negate", [&] {
        std::vector<Token> toks = {
            Op_(OpId::Negate),
            N("5"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("-5"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: binary then negate", [&] {
        std::vector<Token> toks = {
            N("1"),
            Op_(OpId::Add),
            Op_(OpId::Negate),
            N("2"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("1 + -2"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: unary plus no after_node", [&] {
        std::vector<Token> toks = {
            Op_(OpId::UnaryPlus),
            N("3"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("+3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: unary plus with after_node", [&] {
        std::vector<Token> toks = {
            Op_(OpId::UnaryPlus),
            N("3"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string(" + 3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: negate with after_node", [&] {
        std::vector<Token> toks = {
            Op_(OpId::Negate),
            N("3"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string(" - 3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: after_node only affects first token", [&] {
        std::vector<Token> toks = {
            N("3"),
            Op_(OpId::Add),
            N("5"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string("3 + 5"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: parens preserved", [&] {
        std::vector<Token> toks = {
            kOPN,
            N("1"),
            Op_(OpId::Add),
            N("2"),
            kCPN,
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("(1 + 2)"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: frac round-trip", [&] {
        std::vector<Token> toks = {Frac({N("2")}, {N("3")})};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("\\frac{2}{3}"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: postfix no spacing", [&] {
        std::vector<Token> toks = {
            N("5"),
            Op_(OpId::Fact),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("5!"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: empty", [&] {
        std::vector<Token> empty;
        EXPECT_EQ(ctx, p::tokens_to_text(empty), std::string(""));
    });
}
