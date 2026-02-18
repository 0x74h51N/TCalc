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
using p::ExprKind;
using p::ExprToken;
using p::NumberToken;
using p::OpToken;
using p::ParenKind;
using p::ParenToken;
using p::ParenType;
using p::Token;
using p::TokenKind;

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

} // namespace

void unit_parser(TestContext &ctx) {

    // Tokenizations
    const std::vector<TokCase> tok_cases = {
        {.id = "basic add",
         .input = "1+2",
         .expected =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 2,
                  .end_pos = 3},
             }},

        {.id = "leading negate decimal",
         .input = "-3.5",
         .expected =
             {
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::Negate},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"3.5"},
                  .start_pos = 1,
                  .end_pos = 4},
             }},

        {.id = "negate then plus",
         .input = "-+2",
         .expected =
             {
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::Negate},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::UnaryPlus},
                  .start_pos = 1,
                  .end_pos = 2},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 2,
                  .end_pos = 3},
             }},

        {.id = "func parens imag",
         .input = "sin(2i)",
         .expected =
             {
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sin}, .start_pos = 0, .end_pos = 3},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Open, ParenKind::Paren},
                  .start_pos = 3,
                  .end_pos = 4},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2i"},
                  .start_pos = 4,
                  .end_pos = 6},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Close, ParenKind::Paren},
                  .start_pos = 6,
                  .end_pos = 7},
             }},

        {.id = "spacing and unicode",
         .input = "-2 ³√( 3 ( π ",
         .expected =
             {
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::Negate},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 1,
                  .end_pos = 2},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Cbrt}, .start_pos = 3, .end_pos = 4},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Open, ParenKind::Paren},
                  .start_pos = 4,
                  .end_pos = 5},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"3"},
                  .start_pos = 6,
                  .end_pos = 7},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Open, ParenKind::Paren},
                  .start_pos = 8,
                  .end_pos = 9},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"π"},
                  .start_pos = 10,
                  .end_pos = 11},
             }},

        {.id = "sci notation imag",
         .input = "1.2e-3i",
         .expected =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1.2e-3i"},
                  .start_pos = 0,
                  .end_pos = 7},
             }},

        {.id = "binary plus unary minus",
         .input = "1+-2",
         .expected =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::Negate},
                  .start_pos = 2,
                  .end_pos = 3},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 3,
                  .end_pos = 4},
             }},

        {.id = "negate in parens",
         .input = "(-2)",
         .expected =
             {
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Open, ParenKind::Paren},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::Negate},
                  .start_pos = 1,
                  .end_pos = 2},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 2,
                  .end_pos = 3},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Close, ParenKind::Paren},
                  .start_pos = 3,
                  .end_pos = 4},
             }},

        {.id = "asinh parens",
         .input = "asinh(2)",
         .expected =
             {
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::Asinh},
                  .start_pos = 0,
                  .end_pos = 5},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Open, ParenKind::Paren},
                  .start_pos = 5,
                  .end_pos = 6},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 6,
                  .end_pos = 7},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Close, ParenKind::Paren},
                  .start_pos = 7,
                  .end_pos = 8},
             }},

        {.id = "sqrt parens",
         .input = "sqrt(2)",
         .expected =
             {
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sqrt}, .start_pos = 0, .end_pos = 4},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Open, ParenKind::Paren},
                  .start_pos = 4,
                  .end_pos = 5},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 5,
                  .end_pos = 6},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Close, ParenKind::Paren},
                  .start_pos = 6,
                  .end_pos = 7},
             }
        },

        {.id = "postfix unicode",
        .input = "2³",
        .expected = {
            {.kind = TokenKind::Number, .data = NumberToken{"2"},    .start_pos = 0, .end_pos = 1},
            {.kind = TokenKind::Op,     .data = OpToken{OpId::Cube}, .start_pos = 1, .end_pos = 2},
        }},

        // == Paren types ==============================================

        {.id = "curly braces",
        .input = "{1+2}",
        .expected = {
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Open,  ParenKind::Brace}, .start_pos = 0, .end_pos = 1},
            {.kind = TokenKind::Number, .data = NumberToken{"1"},    .start_pos = 1, .end_pos = 2},
            {.kind = TokenKind::Op,     .data = OpToken{OpId::Add},  .start_pos = 2, .end_pos = 3},
            {.kind = TokenKind::Number, .data = NumberToken{"2"},    .start_pos = 3, .end_pos = 4},
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Close, ParenKind::Brace}, .start_pos = 4, .end_pos = 5},
        }},

        {.id = "square brackets",
        .input = "[3+4]",
        .expected = {
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Open,  ParenKind::Bracket}, .start_pos = 0, .end_pos = 1},
            {.kind = TokenKind::Number, .data = NumberToken{"3"},    .start_pos = 1, .end_pos = 2},
            {.kind = TokenKind::Op,     .data = OpToken{OpId::Add},  .start_pos = 2, .end_pos = 3},
            {.kind = TokenKind::Number, .data = NumberToken{"4"},    .start_pos = 3, .end_pos = 4},
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Close, ParenKind::Bracket}, .start_pos = 4, .end_pos = 5},
        }},

        {.id = "mixed paren kinds",
        .input = "({[1]})",
        .expected = {
            {.kind = TokenKind::Paren,  
                .data = ParenToken{ParenType::Open,  ParenKind::Paren},   .start_pos = 0, .end_pos = 1},
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Open,  ParenKind::Brace},   .start_pos = 1, .end_pos = 2},
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Open,  ParenKind::Bracket}, .start_pos = 2, .end_pos = 3},
            {.kind = TokenKind::Number, .data = NumberToken{"1"},    .start_pos = 3, .end_pos = 4},
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Close, ParenKind::Bracket}, .start_pos = 4, .end_pos = 5},
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Close, ParenKind::Brace},   .start_pos = 5, .end_pos = 6},
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Close, ParenKind::Paren},   .start_pos = 6, .end_pos = 7},
        }},

        {.id = "negate inside curly",
        .input = "{-2}",
        .expected = {
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Open, ParenKind::Brace},  .start_pos = 0, .end_pos = 1},
            {.kind = TokenKind::Op,     .data = OpToken{OpId::Negate}, .start_pos = 1, .end_pos = 2},
            {.kind = TokenKind::Number, .data = NumberToken{"2"},      .start_pos = 2, .end_pos = 3},
            {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Close, ParenKind::Brace}, .start_pos = 3, .end_pos = 4},
        }},

        // == ExprToken (LaTeX) ========================================

        {.id = "frac simple",
        .input = "\\frac{2}{3}",
        .expected = {
            {.kind = TokenKind::Expr, .data = ExprToken{
                .kind = ExprKind::Frac,
                .left  = {{.kind = TokenKind::Number, .data = NumberToken{"2"}}},
                .right = {{.kind = TokenKind::Number, .data = NumberToken{"3"}}},
            }, .start_pos = 0, .end_pos = 11},
        }},

        {.id = "pow simple",
        .input = "\\pow{5}{2}",
        .expected = {
            {.kind = TokenKind::Expr, .data = ExprToken{
                .kind = ExprKind::Pow,
                .left  = {{.kind = TokenKind::Number, .data = NumberToken{"5"}}},
                .right = {{.kind = TokenKind::Number, .data = NumberToken{"2"}}},
            }, .start_pos = 0, .end_pos = 10},
        }},

        {.id = "root simple",
        .input = "\\root{3}{8}",
        .expected = {
            {.kind = TokenKind::Expr, .data = ExprToken{
                .kind = ExprKind::Root,
                .left  = {{.kind = TokenKind::Number, .data = NumberToken{"3"}}},
                .right = {{.kind = TokenKind::Number, .data = NumberToken{"8"}}},
            }, .start_pos = 0, .end_pos = 11},
        }},

        {.id = "frac with inner expr",
        .input = "\\frac{2+3}{4}",
        .expected = {
            {.kind = TokenKind::Expr, .data = ExprToken{
                .kind = ExprKind::Frac,
                .left  = {
                    {.kind = TokenKind::Number, .data = NumberToken{"2"}},
                    {.kind = TokenKind::Op,     .data = OpToken{OpId::Add}},
                    {.kind = TokenKind::Number, .data = NumberToken{"3"}},
                },
                .right = {{.kind = TokenKind::Number, .data = NumberToken{"4"}}},
            }, .start_pos = 0, .end_pos = 13},
        }},

        {.id = "frac nested in frac",
        .input = "\\frac{\\frac{1}{2}}{3}",
        .expected = {
            {.kind = TokenKind::Expr, .data = ExprToken{
                .kind = ExprKind::Frac,
                .left  = {{.kind = TokenKind::Expr, .data = ExprToken{
                    .kind = ExprKind::Frac,
                    .left  = {{.kind = TokenKind::Number, .data = NumberToken{"1"}}},
                    .right = {{.kind = TokenKind::Number, .data = NumberToken{"2"}}},
                }}},
                .right = {{.kind = TokenKind::Number, .data = NumberToken{"3"}}},
            }, .start_pos = 0, .end_pos = 21},
        }},

        {.id = "frac with pow inside",
        .input = "\\frac{\\pow{4}{2}}{3}",
        .expected = {
            {.kind = TokenKind::Expr, .data = ExprToken{
                .kind = ExprKind::Frac,
                .left  = {{.kind = TokenKind::Expr, .data = ExprToken{
                    .kind = ExprKind::Pow,
                    .left  = {{.kind = TokenKind::Number, .data = NumberToken{"4"}}},
                    .right = {{.kind = TokenKind::Number, .data = NumberToken{"2"}}},
                }}},
                .right = {{.kind = TokenKind::Number, .data = NumberToken{"3"}}},
            }, .start_pos = 0, .end_pos = 20},
        }
    },

    // == Mixed: plain tokens + ExprToken ==========================

    {.id = "number then frac",
     .input = "1+\\frac{2}{3}",
     .expected = {
         {.kind = TokenKind::Number, .data = NumberToken{"1"}, .start_pos = 0, .end_pos = 1},
         {.kind = TokenKind::Op,     .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2},
         {.kind = TokenKind::Expr,   .data = ExprToken{
             .kind = ExprKind::Frac,
             .left  = {{.kind = TokenKind::Number, .data = NumberToken{"2"}}},
             .right = {{.kind = TokenKind::Number, .data = NumberToken{"3"}}},
         }, .start_pos = 2, .end_pos = 13},
     }},

    {.id = "frac between numbers",
     .input = "1+\\frac{2}{3}+4",
     .expected = {
         {.kind = TokenKind::Number, .data = NumberToken{"1"}, .start_pos = 0, .end_pos = 1},
         {.kind = TokenKind::Op,     .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2},
         {.kind = TokenKind::Expr,   .data = ExprToken{
             .kind = ExprKind::Frac,
             .left  = {{.kind = TokenKind::Number, .data = NumberToken{"2"}}},
             .right = {{.kind = TokenKind::Number, .data = NumberToken{"3"}}},
         }, .start_pos = 2, .end_pos = 13},
         {.kind = TokenKind::Op,     .data = OpToken{OpId::Add}, .start_pos = 13, .end_pos = 14},
         {.kind = TokenKind::Number, .data = NumberToken{"4"}, .start_pos = 14, .end_pos = 15},
     }},

    // == User curly braces inside LaTeX args ======================

    {.id = "user brace inside frac numerator",
     .input = "\\frac{{1+2}}{3}",
     .expected = {
         {.kind = TokenKind::Expr, .data = ExprToken{
             .kind = ExprKind::Frac,
             .left  = {
                 {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Open, ParenKind::Brace}},
                 {.kind = TokenKind::Number, .data = NumberToken{"1"}},
                 {.kind = TokenKind::Op,     .data = OpToken{OpId::Add}},
                 {.kind = TokenKind::Number, .data = NumberToken{"2"}},
                 {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Close, ParenKind::Brace}},
             },
             .right = {{.kind = TokenKind::Number, .data = NumberToken{"3"}}},
         }, .start_pos = 0, .end_pos = 15},
     }},

    {.id = "user brace around frac",
     .input = "{\\frac{1}{2}}",
     .expected = {
         {.kind = TokenKind::Paren, .data = ParenToken{ParenType::Open, ParenKind::Brace}, .start_pos = 0, .end_pos = 1},
         {.kind = TokenKind::Expr,  .data = ExprToken{
             .kind = ExprKind::Frac,
             .left  = {{.kind = TokenKind::Number, .data = NumberToken{"1"}}},
             .right = {{.kind = TokenKind::Number, .data = NumberToken{"2"}}},
         }, .start_pos = 1, .end_pos = 12},
         {.kind = TokenKind::Paren, .data = ParenToken{ParenType::Close, ParenKind::Brace}, .start_pos = 12, .end_pos = 13},
     }},

    {.id = "complex nested: frac with user brace and inner pow",
     .input = "\\frac{{\\pow{4}{2}}}{3}",
     .expected = {
         {.kind = TokenKind::Expr, .data = ExprToken{
             .kind = ExprKind::Frac,
             .left  = {
                 {.kind = TokenKind::Paren, .data = ParenToken{ParenType::Open, ParenKind::Brace}},
                 {.kind = TokenKind::Expr,  .data = ExprToken{
                     .kind = ExprKind::Pow,
                     .left  = {{.kind = TokenKind::Number, .data = NumberToken{"4"}}},
                     .right = {{.kind = TokenKind::Number, .data = NumberToken{"2"}}},
                 }},
                 {.kind = TokenKind::Paren, .data = ParenToken{ParenType::Close, ParenKind::Brace}},
             },
             .right = {{.kind = TokenKind::Number, .data = NumberToken{"3"}}},
         }, .start_pos = 0, .end_pos = 22},
     }},

    {.id = "curly brace then number plain",
     .input = "2{3+4}+5",
     .expected = {
         {.kind = TokenKind::Number, .data = NumberToken{"2"},    .start_pos = 0, .end_pos = 1},
         {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Open,  ParenKind::Brace}, .start_pos = 1, .end_pos = 2},
         {.kind = TokenKind::Number, .data = NumberToken{"3"},    .start_pos = 2, .end_pos = 3},
         {.kind = TokenKind::Op,     .data = OpToken{OpId::Add},  .start_pos = 3, .end_pos = 4},
         {.kind = TokenKind::Number, .data = NumberToken{"4"},    .start_pos = 4, .end_pos = 5},
         {.kind = TokenKind::Paren,  .data = ParenToken{ParenType::Close, ParenKind::Brace}, .start_pos = 5, .end_pos = 6},
         {.kind = TokenKind::Op,     .data = OpToken{OpId::Add},  .start_pos = 6, .end_pos = 7},
         {.kind = TokenKind::Number, .data = NumberToken{"5"},    .start_pos = 7, .end_pos = 8},
     }},
};

    // Normalizations
    const std::vector<NormCase> norm_cases = {

        {.id = "double sub to add",
         .input =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 2, .end_pos = 3},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 3,
                  .end_pos = 4},
             },
         .expected =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 3,
                  .end_pos = 4},
             }},

        {.id = "add sub to sub",
         .input =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 2, .end_pos = 3},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 3,
                  .end_pos = 4},
             },
         .expected =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 3,
                  .end_pos = 4},
             }},

        {.id = "mixed sign collapse",
         .input =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 2, .end_pos = 3},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 3, .end_pos = 4},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 4, .end_pos = 5},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 5, .end_pos = 6},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 6, .end_pos = 7},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 7, .end_pos = 8},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 8, .end_pos = 9},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 9, .end_pos = 10},
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::Add},
                  .start_pos = 10,
                  .end_pos = 11},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 11,
                  .end_pos = 12},
             },
         .expected =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Sub}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 11,
                  .end_pos = 12},
             }},

        {.id = "add then negate kept",
         .input =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::Negate},
                  .start_pos = 2,
                  .end_pos = 3},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 3,
                  .end_pos = 4},
             },
         .expected =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"1"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Op,
                  .data = OpToken{OpId::Negate},
                  .start_pos = 2,
                  .end_pos = 3},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 3,
                  .end_pos = 4},
             }},

        // Implicit
        // multiplications
        {.id = "implicit mul before lparen",
         .input =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Open, ParenKind::Paren},
                  .start_pos = 1,
                  .end_pos = 2},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"3"},
                  .start_pos = 2,
                  .end_pos = 3},
             },
         .expected =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Mul}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Paren,
                  .data = ParenToken{ParenType::Open, ParenKind::Paren},
                  .start_pos = 2,
                  .end_pos = 3},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"3"},
                  .start_pos = 3,
                  .end_pos = 4},
             }},

        {.id = "implicit mul after postfix",
         .input =
             {
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"3"},
                  .start_pos = 0,
                  .end_pos = 1},
                 {.kind = TokenKind::Op, .data = OpToken{OpId::Fact}, .start_pos = 1, .end_pos = 2},
                 {.kind = TokenKind::Number,
                  .data = NumberToken{"2"},
                  .start_pos = 2,
                  .end_pos = 3},
             },
         .expected = {
             {.kind = TokenKind::Number, .data = NumberToken{"3"}, .start_pos = 0, .end_pos = 1},
             {.kind = TokenKind::Op, .data = OpToken{OpId::Fact}, .start_pos = 1, .end_pos = 2},
             {.kind = TokenKind::Op, .data = OpToken{OpId::Mul}, .start_pos = 2, .end_pos = 3},
             {.kind = TokenKind::Number, .data = NumberToken{"2"}, .start_pos = 3, .end_pos = 4},
         }}};

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
                 {TokenKind::Number, NumberToken{"1"}},
                 {TokenKind::Op, OpToken{OpId::Add}},
                 {TokenKind::Number, NumberToken{"2"}},
                 {TokenKind::Op, OpToken{OpId::Mul}},
                 {TokenKind::Number, NumberToken{"3"}},
                 {TokenKind::Op, OpToken{OpId::Pow}},
                 {TokenKind::Number, NumberToken{"4"}},
             },
         .expected =
             {
                 {TokenKind::Number, NumberToken{"1"}},
                 {TokenKind::Number, NumberToken{"2"}},
                 {TokenKind::Number, NumberToken{"3"}},
                 {TokenKind::Number, NumberToken{"4"}},
                 {TokenKind::Op, OpToken{OpId::Pow}},
                 {TokenKind::Op, OpToken{OpId::Mul}},
                 {TokenKind::Op, OpToken{OpId::Add}},
             }},

        {.id = "pow right assoc",
         .input =
             {
                 {TokenKind::Number, NumberToken{"2"}},
                 {TokenKind::Op, OpToken{OpId::Pow}},
                 {TokenKind::Number, NumberToken{"3"}},
                 {TokenKind::Op, OpToken{OpId::Pow}},
                 {TokenKind::Number, NumberToken{"4"}},
             },
         .expected =
             {
                 {TokenKind::Number, NumberToken{"2"}},
                 {TokenKind::Number, NumberToken{"3"}},
                 {TokenKind::Number, NumberToken{"4"}},
                 {TokenKind::Op, OpToken{OpId::Pow}},
                 {TokenKind::Op, OpToken{OpId::Pow}},
             }},

        {.id = "unary before func",
         .input =
             {
                 {TokenKind::Op, OpToken{OpId::Sin}},
                 {TokenKind::Op, OpToken{OpId::Negate}},
                 {TokenKind::Number, NumberToken{"2"}},
             },
         .expected =
             {
                 {TokenKind::Number, NumberToken{"2"}},
                 {TokenKind::Op, OpToken{OpId::Negate}},
                 {TokenKind::Op, OpToken{OpId::Sin}},
             }},

        {.id = "implicit mul after rparen",
         .input =
             {
                 {TokenKind::Number, NumberToken{"2"}},
                 {TokenKind::Paren, ParenToken{ParenType::Open, ParenKind::Paren}},
                 {TokenKind::Number, NumberToken{"3"}},
                 {TokenKind::Op, OpToken{OpId::Add}},
                 {TokenKind::Number, NumberToken{"4"}},
                 {TokenKind::Paren, ParenToken{ParenType::Close, ParenKind::Paren}},
             },
         .expected =
             {
                 {TokenKind::Number, NumberToken{"2"}},
                 {TokenKind::Number, NumberToken{"3"}},
                 {TokenKind::Number, NumberToken{"4"}},
                 {TokenKind::Op, OpToken{OpId::Add}},
                 {TokenKind::Op, OpToken{OpId::Mul}},
             }},

        {.id = "postfix percent precedence",
         .input =
             {
                 {TokenKind::Number, NumberToken{"2"}},
                 {TokenKind::Op, OpToken{OpId::Pow}},
                 {TokenKind::Number, NumberToken{"3"}},
                 {TokenKind::Op, OpToken{OpId::Percent}},
                 {TokenKind::Op, OpToken{OpId::Add}},
                 {TokenKind::Number, NumberToken{"4"}},
             },
         .expected =
             {
                 {TokenKind::Number, NumberToken{"2"}},
                 {TokenKind::Number, NumberToken{"3"}},
                 {TokenKind::Op, OpToken{OpId::Percent}},
                 {TokenKind::Op, OpToken{OpId::Pow}},
                 {TokenKind::Number, NumberToken{"4"}},
                 {TokenKind::Op, OpToken{OpId::Add}},
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
        EXPECT_EQ(ctx, result.expr_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.expr_indices[0], 0UL);
        // \frac{2}{3} spans 0-11
        EXPECT_EQ(ctx, result.tokens[0].start_pos, 0UL);
        EXPECT_EQ(ctx, result.tokens[0].end_pos, 11UL);
    });

    test_detail::with_case(ctx, "positions :: mixed", [&] {
        const auto result = p::tokenize("1 + \\frac{2}{3} + 4");
        EXPECT_EQ(ctx, result.tokens.size(), 5UL);
        EXPECT_EQ(ctx, result.expr_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.expr_indices[0], 2UL);
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
        EXPECT_EQ(ctx, result.expr_indices.size(), 2UL);
        EXPECT_EQ(ctx, result.expr_indices[0], 0UL);
        EXPECT_EQ(ctx, result.expr_indices[1], 2UL);
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
        // (1+2) → tokens: ( 1 + 2 )   indices: 0 1 2 3 4
        auto result = p::tokenize("(1+2)");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), 4UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 4), 0UL);
    });

    test_detail::with_case(ctx, "match_parens :: nested same kind", [&] {
        // ((1)) → ( ( 1 ) )   indices: 0 1 2 3 4
        auto result = p::tokenize("((1))");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), 4UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 1), 3UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 3), 1UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 4), 0UL);
    });

    test_detail::with_case(ctx, "match_parens :: mixed kinds nested", [&] {
        // ({[1]}) → ( { [ 1 ] } )   indices: 0 1 2 3 4 5 6
        auto result = p::tokenize("({[1]})");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), 6UL); // ( <-> )
        EXPECT_EQ(ctx, pair_of(result.tokens, 1), 5UL); // { <-> }
        EXPECT_EQ(ctx, pair_of(result.tokens, 2), 4UL); // [ <-> ]
        EXPECT_EQ(ctx, pair_of(result.tokens, 4), 2UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 5), 1UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 6), 0UL);
    });

    test_detail::with_case(ctx, "match_parens :: sequential groups", [&] {
        // (1)+(2) → ( 1 ) + ( 2 )   indices: 0 1 2 3 4 5 6
        auto result = p::tokenize("(1)+(2)");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), 2UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 2), 0UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 4), 6UL);
        EXPECT_EQ(ctx, pair_of(result.tokens, 6), 4UL);
    });

    test_detail::with_case(ctx, "match_parens :: unmatched open", [&] {
        // (1+2 → ( 1 + 2
        auto result = p::tokenize("(1+2");
        EXPECT_EQ(ctx, pair_of(result.tokens, 0), p::kNoMatch);
    });

    test_detail::with_case(ctx, "match_parens :: unmatched close", [&] {
        // 1+2) → 1 + 2 )
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
        // No paren tokens, nothing to check — just ensure no crash.
        EXPECT_EQ(ctx, result.tokens.size(), 3UL);
    });
}
