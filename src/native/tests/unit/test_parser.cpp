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
using p::StructuralSplit;
using p::Token;
using p::TokenKind;
using p::TokensBranch;

namespace {

/// Generic test-row template: id label, input value, expected value.
template <typename InputT, typename ExpectedT> struct Case {
    const char *id;
    InputT input;
    ExpectedT expected;
};

/// scan_number input pair: source text and start offset.
struct ScanInput {
    std::string_view text;
    std::size_t start;
};

/// scan_number expected output: matched view and post-scan cursor position.
struct ScanExpected {
    std::string_view view;
    std::size_t next;
};

/// structural_split expected output: the split variant kind plus the four
/// token spans (prefix/left/right/suffix) and paren/latex metadata.
struct SplitExpected {
    enum class Kind { None, Paren, Latex };
    Kind kind = Kind::None;
    std::vector<Token> prefix;
    std::vector<Token> left;
    std::vector<Token> right;
    std::vector<Token> suffix;
    ParenToken open_tok{};
    std::optional<ParenToken> close_tok{};
    p::LatexKind latex_kind{};
};

/// Case row for tokenize: raw source string -> expected token vector.
using TokCase = Case<const char *, std::vector<tcalc::parser::Token>>;
/// Case row for scan_number: ScanInput -> ScanExpected.
using ScanCase = Case<ScanInput, ScanExpected>;
/// Case row for normalize: input tokens -> normalized tokens.
using NormCase = Case<std::vector<Token>, std::vector<Token>>;
/// Case row for shunting_yard: infix tokens -> RPN tokens.
using ShuntCase = Case<std::vector<Token>, std::vector<Token>>;
/// Case row for structural_split: classified TokensBranch -> SplitExpected.
using SplitCase = Case<TokensBranch, SplitExpected>;

/// classify_tokens expected output: re-derived index vectors plus pair_idx
/// values for every paren token (open and close) we want to assert on.
struct ClassifyExpected {
    std::vector<p::TokenIndex> latex_indices;
    std::vector<p::TokenIndex> open_paren_indices;
    std::vector<p::TokenIndex> close_paren_indices;
    /// Each entry: (token index in `input`, expected pair_idx). Use kNoMatch
    /// for unmatched parens. List both endpoints of a matched pair.
    std::vector<std::pair<p::TokenIndex, p::TokenIndex>> pairs;
};

/// Case row for classify_tokens: raw token list -> ClassifyExpected.
using ClassifyCase = Case<std::vector<Token>, ClassifyExpected>;

/// tokenize position-tracking expected output: token count, latex indices, and
/// (token_idx, start_pos, end_pos) tuples for the indices we want to assert.
struct PositionExpected {
    std::size_t token_count;
    std::vector<p::TokenIndex> latex_indices;
    std::vector<std::tuple<p::TokenIndex, std::size_t, std::size_t>> positions;
};

/// Case row for tokenize position tests: source string -> PositionExpected.
using PositionCase = Case<const char *, PositionExpected>;

/// match_parens expected output: tokenize result token count plus the
/// (token_idx, expected pair_idx) checks. Use kNoMatch for unmatched.
struct MatchParensExpected {
    std::size_t token_count;
    std::vector<std::pair<p::TokenIndex, p::TokenIndex>> pairs;
};

/// Case row for match_parens (via tokenize): source string -> MatchParensExpected.
using MatchParensCase = Case<const char *, MatchParensExpected>;

/// Open round-paren ParenToken constant.
inline constexpr ParenToken kPOP{ParenType::Open, ParenKind::Paren};
/// Close round-paren ParenToken constant.
inline constexpr ParenToken kPCL{ParenType::Close, ParenKind::Paren};
/// Open round-paren Token constant (wraps kPOP).
inline const Token kOPN{TokenKind::Paren, kPOP};
/// Close round-paren Token constant (wraps kPCL).
inline const Token kCPN{TokenKind::Paren, kPCL};

// Token factories. start/end default to 0
// pass them only when the test actually checks span info

/// Token factory: NumberToken with the given literal value.
inline Token N(const char *value, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Number, NumberToken{value}, start, end};
}
/// Token factory: OpToken for the given op id (binary, unary, or postfix).
inline Token Op_(OpId id, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Op, OpToken{id}, start, end};
}
/// Token factory: open ParenToken of the given kind (Paren/Brace/Bracket).
inline Token OpenP(ParenKind kind = ParenKind::Paren, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Paren, ParenToken{ParenType::Open, kind}, start, end};
}
/// Token factory: close ParenToken of the given kind (Paren/Brace/Bracket).
inline Token CloseP(ParenKind kind = ParenKind::Paren, std::size_t start = 0, std::size_t end = 0) {
    return Token{TokenKind::Paren, ParenToken{ParenType::Close, kind}, start, end};
}
/// Token factory: LatexToken of arbitrary kind/op with explicit left/right token rows.
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
/// Token factory shorthand: \frac LatexToken (numerator, denominator).
inline Token Frac(
    std::vector<Token> numerator,
    std::vector<Token> denominator,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(
        p::LatexKind::Frac, OpId::Div, std::move(numerator), std::move(denominator), start, end);
}
/// Token factory shorthand: \pow LatexToken (base, exponent).
inline Token
Pow(std::vector<Token> base,
    std::vector<Token> exponent,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(p::LatexKind::Pow, OpId::Pow, std::move(base), std::move(exponent), start, end);
}
/// Token factory shorthand: \root LatexToken (radicand, degree).
inline Token Root(
    std::vector<Token> degree,
    std::vector<Token> radicand,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(p::LatexKind::Root, OpId::Root, std::move(degree), std::move(radicand), start, end);
}

/// Shorthand for tcalc::parser::ParenKind.
using PK = p::ParenKind;
/// Shorthand for tcalc::parser::LatexKind.
using LK = p::LatexKind;

} // namespace

void unit_parser(TestContext &ctx) {

    // =========================================================================
    // Tokenizations
    // =========================================================================
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

    for (std::size_t i = 0; i < tok_cases.size(); ++i) {
        const auto &tc = tok_cases[i];
        test_detail::with_case(ctx, std::string("tokenize :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, p::tokenize(tc.input).tokens, tc.expected);
        });
    }

    // =========================================================================
    // Normalizations
    // =========================================================================
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

    for (std::size_t i = 0; i < norm_cases.size(); ++i) {
        const auto &tc = norm_cases[i];
        test_detail::with_case(ctx, std::string("normalize :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, d::normalize(tc.input), tc.expected);
        });
    }

    // =========================================================================
    // Scanifications
    // =========================================================================
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

    for (std::size_t i = 0; i < shunt_cases.size(); ++i) {
        const auto &tc = shunt_cases[i];
        test_detail::with_case(ctx, std::string("shunting yard :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, p::shunting_yard(tc.input), tc.expected);
        });
    }

    // =========================================================================
    // tokenize position tests
    // =========================================================================
    {
        const std::vector<PositionCase> position_cases = {
            {.id = "simple expr",
             .input = "3 + 5",
             .expected = {.token_count = 3, .positions = {{0, 0, 1}, {1, 2, 3}, {2, 4, 5}}}},

            {.id = "frac expr",
             .input = "\\frac{2}{3}",
             .expected = {.token_count = 1, .latex_indices = {0}, .positions = {{0, 0, 11}}}},

            {.id = "mixed",
             .input = "1 + \\frac{2}{3} + 4",
             .expected =
                 {.token_count = 5,
                  .latex_indices = {2},
                  .positions = {{0, 0, 1}, {1, 2, 3}, {2, 4, 15}, {3, 16, 17}, {4, 18, 19}}}},

            {.id = "multiple expr",
             .input = "\\frac{1}{2} + \\pow{3}{4}",
             .expected =
                 {.token_count = 3,
                  .latex_indices = {0, 2},
                  .positions = {{0, 0, 11}, {2, 14, 24}}}},
        };

        for (const auto &tc : position_cases) {
            test_detail::with_case(ctx, std::string("positions :: ") + tc.id, [&] {
                const auto result = p::tokenize(tc.input);
                const auto &exp = tc.expected;

                EXPECT_EQ(ctx, result.tokens.size(), exp.token_count);
                EXPECT_EQ(ctx, result.latex_indices, exp.latex_indices);
                for (const auto &[idx, start, end] : exp.positions) {
                    EXPECT_EQ(ctx, result.tokens[idx].start_pos, start);
                    EXPECT_EQ(ctx, result.tokens[idx].end_pos, end);
                }
            });
        }
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

    // =========================================================================
    // match_parens
    // =========================================================================
    const auto pair_of = [](const std::vector<Token> &toks, std::size_t idx) -> std::size_t {
        return std::get<ParenToken>(toks[idx].data).pair_idx;
    };

    {
        const std::vector<MatchParensCase> match_parens_cases = {
            {.id = "simple parens",
             // (1+2) -> ( 1 + 2 )   indices: 0 1 2 3 4
             .input = "(1+2)",
             .expected = {.token_count = 5, .pairs = {{0, 4}, {4, 0}}}},

            {.id = "nested same kind",
             // ((1)) -> ( ( 1 ) )   indices: 0 1 2 3 4
             .input = "((1))",
             .expected = {.token_count = 5, .pairs = {{0, 4}, {1, 3}, {3, 1}, {4, 0}}}},

            {.id = "mixed kinds nested",
             // ({[1]}) -> ( { [ 1 ] } )   indices: 0 1 2 3 4 5 6
             .input = "({[1]})",
             .expected =
                 {.token_count = 7, .pairs = {{0, 6}, {1, 5}, {2, 4}, {4, 2}, {5, 1}, {6, 0}}}},

            {.id = "sequential groups",
             // (1)+(2) -> ( 1 ) + ( 2 )   indices: 0 1 2 3 4 5 6
             .input = "(1)+(2)",
             .expected = {.token_count = 7, .pairs = {{0, 2}, {2, 0}, {4, 6}, {6, 4}}}},

            {.id = "unmatched open",
             // (1+2 -> ( 1 + 2
             .input = "(1+2",
             .expected = {.token_count = 4, .pairs = {{0, p::kNoMatch}}}},

            {.id = "unmatched close",
             // 1+2) -> 1 + 2 )
             .input = "1+2)",
             .expected = {.token_count = 4, .pairs = {{3, p::kNoMatch}}}},

            {.id = "complex expression",
             // [(34+5)*(4*{3+5})+4]
             // [ ( 34 + 5 ) * ( 4 * { 3 + 5 } ) + 4 ]
             // 0 1 2  3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18
             .input = "[(34+5)*(4*{3+5})+4]",
             .expected =
                 {.token_count = 19,
                  .pairs =
                      {{0, 18}, {1, 5}, {5, 1}, {7, 15}, {10, 14}, {14, 10}, {15, 7}, {18, 0}}}},

            {.id = "no parens", .input = "1+2", .expected = {.token_count = 3}},
        };

        for (const auto &tc : match_parens_cases) {
            test_detail::with_case(ctx, std::string("match_parens :: ") + tc.id, [&] {
                const auto result = p::tokenize(tc.input);
                const auto &exp = tc.expected;

                EXPECT_EQ(ctx, result.tokens.size(), exp.token_count);
                for (const auto &[idx, expected_pair] : exp.pairs) {
                    EXPECT_EQ(ctx, pair_of(result.tokens, idx), expected_pair);
                }
            });
        }
    }

    // =========================================================================
    // classify_tokens
    // =========================================================================
    {
        const std::vector<ClassifyCase> classify_cases = {
            {.id = "empty", .input = {}, .expected = {}},

            // "1+2"
            {.id = "plain expr no parens no latex",
             .input = {N("1"), Op_(OpId::Add), N("2")},
             .expected = {}},

            // "\frac{1}{2}"
            {.id = "frac alone populates latex_indices",
             .input = {Frac({N("1")}, {N("2")})},
             .expected = {.latex_indices = {0}}},

            // "(\frac{2}{3})" -> ( frac )   indices: 0 1 2
            {.id = "matched paren wraps frac",
             .input = {kOPN, Frac({N("2")}, {N("3")}), kCPN},
             .expected =
                 {.latex_indices = {1},
                  .open_paren_indices = {0},
                  .close_paren_indices = {2},
                  .pairs = {{0, 2}, {2, 0}}}},

            // "(1)+(2)" -> ( 1 ) + ( 2 )   indices: 0 1 2 3 4 5 6
            {.id = "two sibling paren groups",
             .input = {kOPN, N("1"), kCPN, Op_(OpId::Add), kOPN, N("2"), kCPN},
             .expected =
                 {.open_paren_indices = {0, 4},
                  .close_paren_indices = {2, 6},
                  .pairs = {{0, 2}, {2, 0}, {4, 6}, {6, 4}}}},

            // "(1)+\frac{2}{3})" -> ( 1 ) + frac )   indices: 0 1 2 3 4 5
            {.id = "trailing unmatched close after frac",
             .input = {kOPN, N("1"), kCPN, Op_(OpId::Add), Frac({N("2")}, {N("3")}), kCPN},
             .expected =
                 {.latex_indices = {4},
                  .open_paren_indices = {0},
                  .close_paren_indices = {2, 5},
                  .pairs = {{0, 2}, {2, 0}, {5, p::kNoMatch}}}},

            // "{+\frac{2}{3}" -> { + frac   indices: 0 1 2  (no closing })
            {.id = "unmatched brace open before frac",
             .input = {OpenP(PK::Brace), Op_(OpId::UnaryPlus), Frac({N("2")}, {N("3")})},
             .expected =
                 {.latex_indices = {2}, .open_paren_indices = {0}, .pairs = {{0, p::kNoMatch}}}},

            // "{\frac{2}{3})" -> { frac )   indices: 0 1 2  (kinds don't match)
            {.id = "mixed kinds neither matches",
             .input = {OpenP(PK::Brace), Frac({N("2")}, {N("3")}), kCPN},
             .expected =
                 {.latex_indices = {1},
                  .open_paren_indices = {0},
                  .close_paren_indices = {2},
                  .pairs = {{0, p::kNoMatch}, {2, p::kNoMatch}}}},

            // "(1)+{2+[\pow{2}{3}]+4}"
            // -> ( 1 ) + { 2 + [ pow ] + 4 }
            //    0 1 2 3 4 5 6 7 8   9 10 11 12
            {.id = "three nested mixed kinds all matched",
             .input =
                 {kOPN,
                  N("1"),
                  kCPN,
                  Op_(OpId::Add),
                  OpenP(PK::Brace),
                  N("2"),
                  Op_(OpId::Add),
                  OpenP(PK::Bracket),
                  Pow({N("2")}, {N("3")}),
                  CloseP(PK::Bracket),
                  Op_(OpId::Add),
                  N("4"),
                  CloseP(PK::Brace)},
             .expected =
                 {.latex_indices = {8},
                  .open_paren_indices = {0, 4, 7},
                  .close_paren_indices = {2, 9, 12},
                  .pairs = {{0, 2}, {2, 0}, {4, 12}, {12, 4}, {7, 9}, {9, 7}}}},

            // Slice [5..12) of "(1)+{2+[\pow{2}{3}]+4}" re-classified standalone
            // -> 2 + [ pow ] + 4   indices: 0 1 2 3 4 5 6
            {.id = "rebase nested slice pairs",
             .input =
                 {N("2"),
                  Op_(OpId::Add),
                  OpenP(PK::Bracket),
                  Pow({N("2")}, {N("3")}),
                  CloseP(PK::Bracket),
                  Op_(OpId::Add),
                  N("4")},
             .expected =
                 {.latex_indices = {3},
                  .open_paren_indices = {2},
                  .close_paren_indices = {4},
                  .pairs = {{2, 4}, {4, 2}}}},

            // Slice [1..5) of "({[1]})" -> { [ 1 ]   indices: 0 1 2 3
            // Outer { lost its }; inner [ ] still pairs locally.
            {.id = "unmatched outer pair stays open",
             .input = {OpenP(PK::Brace), OpenP(PK::Bracket), N("1"), CloseP(PK::Bracket)},
             .expected =
                 {.open_paren_indices = {0, 1},
                  .close_paren_indices = {3},
                  .pairs = {{0, p::kNoMatch}, {1, 3}, {3, 1}}}},

            // Brace contents of "(1)+{2+[\frac{2}{3}+4+(\pow{2}{3}" (build_nodes
            // edge case): three different unmatched opens stacked, two latex.
            // -> { 2 + [ frac + 4 + ( pow   indices: 0 1 2 3 4    5 6 7 8 9
            {.id = "all unmatched nested opens with latex",
             .input =
                 {OpenP(PK::Brace),
                  N("2"),
                  Op_(OpId::Add),
                  OpenP(PK::Bracket),
                  Frac({N("2")}, {N("3")}),
                  Op_(OpId::Add),
                  N("4"),
                  Op_(OpId::Add),
                  kOPN,
                  Pow({N("2")}, {N("3")})},
             .expected =
                 {.latex_indices = {4, 9},
                  .open_paren_indices = {0, 3, 8},
                  .pairs = {{0, p::kNoMatch}, {3, p::kNoMatch}, {8, p::kNoMatch}}}},
        };

        for (const auto &tc : classify_cases) {
            test_detail::with_case(ctx, std::string("classify_tokens :: ") + tc.id, [&] {
                auto got = p::classify_tokens(tc.input);
                const auto &exp = tc.expected;

                EXPECT_EQ(ctx, got.latex_indices, exp.latex_indices);
                EXPECT_EQ(ctx, got.open_paren_indices, exp.open_paren_indices);
                EXPECT_EQ(ctx, got.close_paren_indices, exp.close_paren_indices);
                for (const auto &[idx, expected_pair] : exp.pairs) {
                    EXPECT_EQ(ctx, pair_of(got.tokens, idx), expected_pair);
                }
            });
        }
    }

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

    // =========================================================================
    // structural_split
    // =========================================================================
    {
        using K = SplitExpected::Kind;

        const auto branch = [](std::vector<Token> toks) {
            return p::classify_tokens(std::move(toks));
        };

        const std::vector<SplitCase> split_cases = {
            // -- nullopt: no latex tokens at all
            {.id = "nullopt :: empty branch", .input = branch({}), .expected = {.kind = K::None}},

            {.id = "nullopt :: plain expr no latex",
             .input = branch({N("1"), Op_(OpId::Add), N("2")}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: paren only no latex",
             .input = branch({kOPN, N("1"), Op_(OpId::Add), N("2"), kCPN}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: division op only",
             .input = branch({N("4"), Op_(OpId::Div), N("5")}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: paren mixed ops",
             .input = branch(
                 {kOPN,
                  N("2"),
                  Op_(OpId::Add),
                  N("5"),
                  Op_(OpId::Div),
                  N("5"),
                  Op_(OpId::Mul),
                  N("4"),
                  kCPN}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: nested parens no latex",
             .input = branch({kOPN, kOPN, N("1"), kCPN, kCPN}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: two paren groups no latex",
             .input = branch(
                 {kOPN,
                  N("1"),
                  Op_(OpId::Add),
                  N("2"),
                  kCPN,
                  Op_(OpId::Mul),
                  kOPN,
                  N("3"),
                  Op_(OpId::Add),
                  N("4"),
                  kCPN}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: unmatched paren no latex",
             .input = branch({kOPN, N("1"), Op_(OpId::Add), N("2")}),
             .expected = {.kind = K::None}},

            // -- LatexSplit: filled latex with no surrounding
            {.id = "latex :: filled frac alone",
             .input = branch({Frac({N("2")}, {N("3")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("2")},
                  .right = {N("3")},
                  .latex_kind = p::LatexKind::Frac}},

            {.id = "latex :: empty frac alone",
             .input = branch({Frac({}, {})}),
             .expected = {.kind = K::Latex, .latex_kind = p::LatexKind::Frac}},

            // -- LatexSplit: operand pickup when latex left/right empty
            // 1+2\frac -> prefix=[1,+], left=[2]
            {.id = "latex :: trailing number becomes left",
             .input = branch({N("1"), Op_(OpId::Add), N("2"), Frac({}, {})}),
             .expected =
                 {.kind = K::Latex,
                  .prefix = {N("1"), Op_(OpId::Add)},
                  .left = {N("2")},
                  .latex_kind = p::LatexKind::Frac}},

            // \frac{}{}+2 ... wait: \frac 2+3 -> right=[2], suffix=[+,3]
            {.id = "latex :: leading number becomes right",
             .input = branch({Frac({}, {}), N("2"), Op_(OpId::Add), N("3")}),
             .expected =
                 {.kind = K::Latex,
                  .right = {N("2")},
                  .suffix = {Op_(OpId::Add), N("3")},
                  .latex_kind = p::LatexKind::Frac}},

            // \frac{1}{}+2 -> left from latex, right empty (op blocks pickup)
            {.id = "latex :: leading op blocks right pickup",
             .input = branch({Frac({N("1")}, {}), Op_(OpId::Add), N("2")}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .suffix = {Op_(OpId::Add), N("2")},
                  .latex_kind = p::LatexKind::Frac}},

            // 1+\frac{}{2} -> left empty (op blocks), right from latex
            {.id = "latex :: trailing op blocks left pickup",
             .input = branch({N("1"), Op_(OpId::Add), Frac({}, {N("2")})}),
             .expected =
                 {.kind = K::Latex,
                  .prefix = {N("1"), Op_(OpId::Add)},
                  .right = {N("2")},
                  .latex_kind = p::LatexKind::Frac}},

            // (2+5)+\frac{}{} -> closed paren BEFORE latex stays in prefix,
            // not a ParenSplit (rule: paren must wrap or be unmatched past latex)
            {.id = "latex :: closed paren before frac stays in prefix",
             .input =
                 branch({kOPN, N("2"), Op_(OpId::Add), N("5"), kCPN, Op_(OpId::Add), Frac({}, {})}),
             .expected =
                 {.kind = K::Latex,
                  .prefix = {kOPN, N("2"), Op_(OpId::Add), N("5"), kCPN, Op_(OpId::Add)},
                  .latex_kind = p::LatexKind::Frac}},

            // -- LatexSplit: trailing operand is a paren group
            // 1\frac{}{} -> left=[1], suffix=[]
            {.id = "latex :: trailing num before latex",
             .input = branch({N("1"), Frac({}, {})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {},
                  .latex_kind = p::LatexKind::Frac}},

            // \frac{1}{}(2+3) -> right=[(2+3)], suffix=[]
            {.id = "latex :: trailing paren group becomes right",
             .input = branch({Frac({N("1")}, {}), kOPN, N("2"), Op_(OpId::Add), N("3"), kCPN}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {kOPN, N("2"), Op_(OpId::Add), N("3"), kCPN},
                  .latex_kind = p::LatexKind::Frac}},
            // 1\frac{}{}(2+3) -> right=[(2+3)], suffix=[]
            {.id = "latex :: trailing num and paren group becomes right and left",
             .input = branch({N("1"), Frac({}, {}), kOPN, N("2"), Op_(OpId::Add), N("3"), kCPN}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {kOPN, N("2"), Op_(OpId::Add), N("3"), kCPN},
                  .latex_kind = p::LatexKind::Frac}},

            // -- ParenSplit: paren wraps first latex
            // (\frac{2}{3})
            {.id = "paren :: matched paren wraps frac",
             .input = branch({kOPN, Frac({N("2")}, {N("3")}), kCPN}),
             .expected =
                 {.kind = K::Paren,
                  .left = {Frac({N("2")}, {N("3")})},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // (1+\frac{2}{3} -> unmatched open, no suffix, no close_tok
            {.id = "paren :: unmatched open before frac",
             .input = branch({kOPN, N("1"), Op_(OpId::Add), Frac({N("2")}, {N("3")})}),
             .expected =
                 {.kind = K::Paren,
                  .left = {N("1"), Op_(OpId::Add), Frac({N("2")}, {N("3")})},
                  .open_tok = kPOP,
                  .close_tok = std::nullopt}},

            // (2+\frac{2}{})\frac{}{} -> outer paren wraps first frac, second is suffix
            {.id = "paren :: wrap first frac, second frac in suffix",
             .input =
                 branch({kOPN, N("2"), Op_(OpId::Add), Frac({N("2")}, {}), kCPN, Frac({}, {})}),
             .expected =
                 {.kind = K::Paren,
                  .left = {N("2"), Op_(OpId::Add), Frac({N("2")}, {})},
                  .suffix = {Frac({}, {})},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // ((1)+\frac{2}{3}) -> outer paren is the candidate
            {.id = "paren :: outer paren picked over inner",
             .input =
                 branch({kOPN, kOPN, N("1"), kCPN, Op_(OpId::Add), Frac({N("2")}, {N("3")}), kCPN}),
             .expected =
                 {.kind = K::Paren,
                  .left = {kOPN, N("1"), kCPN, Op_(OpId::Add), Frac({N("2")}, {N("3")})},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // -- Sibling latex (no parens): first wins, rest goes to suffix --
            {.id = "latex :: sibling fracs first wins",
             .input = branch({Frac({N("1")}, {N("2")}), Op_(OpId::Add), Frac({N("3")}, {N("4")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {N("2")},
                  .suffix = {Op_(OpId::Add), Frac({N("3")}, {N("4")})},
                  .latex_kind = p::LatexKind::Frac}},

            // Paren AFTER first latex doesn't trigger ParenSplit
            {.id = "latex :: paren after first frac stays in suffix",
             .input = branch(
                 {Frac({N("1")}, {N("2")}), Op_(OpId::Add), kOPN, Frac({N("3")}, {N("4")}), kCPN}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {N("2")},
                  .suffix = {Op_(OpId::Add), kOPN, Frac({N("3")}, {N("4")}), kCPN},
                  .latex_kind = p::LatexKind::Frac}},

            // -- Nested latex (top-level token has nested Latex inside)
            // \frac{\frac{1}{2}}{3} -> outer wins; nested frac is one element of left
            {.id = "latex :: nested frac in left",
             .input = branch({Frac({Frac({N("1")}, {N("2")})}, {N("3")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {Frac({N("1")}, {N("2")})},
                  .right = {N("3")},
                  .latex_kind = p::LatexKind::Frac}},

            // \frac{1}{\frac{2}{3}} -> outer wins; nested frac sits in right
            {.id = "latex :: nested frac in right",
             .input = branch({Frac({N("1")}, {Frac({N("2")}, {N("3")})})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {Frac({N("2")}, {N("3")})},
                  .latex_kind = p::LatexKind::Frac}},

            // -- Nested parens around a latex
            // ((1+\frac{2}{3})) -> outermost paren wraps everything
            {.id = "paren :: doubly nested wraps frac",
             .input =
                 branch({kOPN, kOPN, N("1"), Op_(OpId::Add), Frac({N("2")}, {N("3")}), kCPN, kCPN}),
             .expected =
                 {.kind = K::Paren,
                  .left = {kOPN, N("1"), Op_(OpId::Add), Frac({N("2")}, {N("3")}), kCPN},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // 1+(2+\frac{3}{4})*5 -> paren wraps frac, ops on both sides
            {.id = "paren :: wrap frac with ops on both sides",
             .input = branch(
                 {N("1"),
                  Op_(OpId::Add),
                  kOPN,
                  N("2"),
                  Op_(OpId::Add),
                  Frac({N("3")}, {N("4")}),
                  kCPN,
                  Op_(OpId::Mul),
                  N("5")}),
             .expected =
                 {.kind = K::Paren,
                  .prefix = {N("1"), Op_(OpId::Add)},
                  .left = {N("2"), Op_(OpId::Add), Frac({N("3")}, {N("4")})},
                  .suffix = {Op_(OpId::Mul), N("5")},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // -- Sibling: more than two
            // \frac{1}{2}+\frac{3}{4}+\frac{5}{6} -> first wins, rest in suffix
            {.id = "latex :: three sibling fracs",
             .input = branch(
                 {Frac({N("1")}, {N("2")}),
                  Op_(OpId::Add),
                  Frac({N("3")}, {N("4")}),
                  Op_(OpId::Add),
                  Frac({N("5")}, {N("6")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {N("2")},
                  .suffix =
                      {Op_(OpId::Add),
                       Frac({N("3")}, {N("4")}),
                       Op_(OpId::Add),
                       Frac({N("5")}, {N("6")})},
                  .latex_kind = p::LatexKind::Frac}},

            // (\frac{1}{2}+\frac{3}{4}) -> paren wraps both siblings
            {.id = "paren :: wrap two sibling fracs",
             .input = branch(
                 {kOPN, Frac({N("1")}, {N("2")}), Op_(OpId::Add), Frac({N("3")}, {N("4")}), kCPN}),
             .expected =
                 {.kind = K::Paren,
                  .left = {Frac({N("1")}, {N("2")}), Op_(OpId::Add), Frac({N("3")}, {N("4")})},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // -- Sibling + nested mix
            // \frac{1}{\frac{2}{3}}+\frac{4}{5} -> first frac wins
            {.id = "latex :: nested-right then sibling",
             .input = branch(
                 {Frac({N("1")}, {Frac({N("2")}, {N("3")})}),
                  Op_(OpId::Add),
                  Frac({N("4")}, {N("5")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {Frac({N("2")}, {N("3")})},
                  .suffix = {Op_(OpId::Add), Frac({N("4")}, {N("5")})},
                  .latex_kind = p::LatexKind::Frac}},

            // (\frac{1}{2})+\frac{3}{4} -> outer paren wraps first frac
            {.id = "paren :: wrapped frac plus sibling outside",
             .input = branch(
                 {kOPN, Frac({N("1")}, {N("2")}), kCPN, Op_(OpId::Add), Frac({N("3")}, {N("4")})}),
             .expected =
                 {.kind = K::Paren,
                  .left = {Frac({N("1")}, {N("2")})},
                  .suffix = {Op_(OpId::Add), Frac({N("3")}, {N("4")})},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // -- Two sibling ParenSplits
            // (\frac{1}{2})+(\frac{3}{4}) -> first paren wins; second paren group
            // sits in suffix as raw tokens
            {.id = "paren :: two sibling paren-wrapped fracs",
             .input = branch(
                 {kOPN,
                  Frac({N("1")}, {N("2")}),
                  kCPN,
                  Op_(OpId::Add),
                  kOPN,
                  Frac({N("3")}, {N("4")}),
                  kCPN}),
             .expected =
                 {.kind = K::Paren,
                  .left = {Frac({N("1")}, {N("2")})},
                  .suffix = {Op_(OpId::Add), kOPN, Frac({N("3")}, {N("4")}), kCPN},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // (\frac{1}{2}+1)*(2-\frac{3}{4})
            {.id = "paren :: two sibling paren groups with inner ops",
             .input = branch(
                 {kOPN,
                  Frac({N("1")}, {N("2")}),
                  Op_(OpId::Add),
                  N("1"),
                  kCPN,
                  Op_(OpId::Mul),
                  kOPN,
                  N("2"),
                  Op_(OpId::Sub),
                  Frac({N("3")}, {N("4")}),
                  kCPN}),
             .expected =
                 {.kind = K::Paren,
                  .left = {Frac({N("1")}, {N("2")}), Op_(OpId::Add), N("1")},
                  .suffix =
                      {Op_(OpId::Mul),
                       kOPN,
                       N("2"),
                       Op_(OpId::Sub),
                       Frac({N("3")}, {N("4")}),
                       kCPN},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // (\frac{1}{2})+(\frac{3}{4})*(\frac{5}{6}) -> first wins
            {.id = "paren :: three sibling paren-wrapped fracs",
             .input = branch(
                 {kOPN,
                  Frac({N("1")}, {N("2")}),
                  kCPN,
                  Op_(OpId::Add),
                  kOPN,
                  Frac({N("3")}, {N("4")}),
                  kCPN,
                  Op_(OpId::Mul),
                  kOPN,
                  Frac({N("5")}, {N("6")}),
                  kCPN}),
             .expected =
                 {.kind = K::Paren,
                  .left = {Frac({N("1")}, {N("2")})},
                  .suffix =
                      {Op_(OpId::Add),
                       kOPN,
                       Frac({N("3")}, {N("4")}),
                       kCPN,
                       Op_(OpId::Mul),
                       kOPN,
                       Frac({N("5")}, {N("6")}),
                       kCPN},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},

            // ((\frac{1}{2}+1))+(\frac{3}{4})+(\frac{5}{6})
            {.id = "paren :: four paren groups, first has nested wrap",
             .input = branch(
                 {kOPN,
                  kOPN,
                  Frac({N("1")}, {N("2")}),
                  Op_(OpId::Add),
                  N("1"),
                  kCPN,
                  kCPN,
                  Op_(OpId::Add),
                  kOPN,
                  Frac({N("3")}, {N("4")}),
                  kCPN,
                  Op_(OpId::Add),
                  kOPN,
                  Frac({N("5")}, {N("6")}),
                  kCPN}),
             .expected =
                 {.kind = K::Paren,
                  .left = {kOPN, Frac({N("1")}, {N("2")}), Op_(OpId::Add), N("1"), kCPN},
                  .suffix =
                      {Op_(OpId::Add),
                       kOPN,
                       Frac({N("3")}, {N("4")}),
                       kCPN,
                       Op_(OpId::Add),
                       kOPN,
                       Frac({N("5")}, {N("6")}),
                       kCPN},
                  .open_tok = kPOP,
                  .close_tok = kPCL}},
        };

        const auto to_vec = [](std::span<const Token> a) {
            return std::vector<Token>(a.begin(), a.end());
        };

        for (const auto &tc : split_cases) {
            test_detail::with_case(ctx, std::string("structural_split :: ") + tc.id, [&] {
                const auto got = p::structural_split(tc.input);
                const auto &exp = tc.expected;

                if (exp.kind == K::None) {
                    EXPECT_TRUE(ctx, !got.has_value());
                    return;
                }
                EXPECT_TRUE(ctx, got.has_value());
                if (!got.has_value())
                    return;

                std::visit(
                    [&](const auto &s) {
                        using T = std::decay_t<decltype(s)>;
                        constexpr bool is_paren = std::is_same_v<T, p::ParenSplit>;

                        EXPECT_TRUE(ctx, exp.kind == (is_paren ? K::Paren : K::Latex));
                        EXPECT_EQ(ctx, to_vec(s.prefix), exp.prefix);
                        EXPECT_EQ(ctx, to_vec(s.left), exp.left);
                        EXPECT_EQ(ctx, to_vec(s.suffix), exp.suffix);

                        if constexpr (is_paren) {
                            EXPECT_TRUE(ctx, s.open_tok == exp.open_tok);
                            EXPECT_EQ(ctx, s.close_tok.has_value(), exp.close_tok.has_value());
                            if (s.close_tok && exp.close_tok)
                                EXPECT_TRUE(ctx, *s.close_tok == *exp.close_tok);
                        } else {
                            EXPECT_TRUE(ctx, s.kind == exp.latex_kind);
                            EXPECT_EQ(ctx, to_vec(s.right), exp.right);
                        }
                    },
                    *got);
            });
        }
    }
}