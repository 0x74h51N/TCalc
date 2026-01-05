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
using p::Token;
using p::TokenKind;

namespace {

template <typename InputT, typename ExpectedT> struct Case {
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

using TokCase = Case<const char *, std::vector<Token>>;
using ScanCase = Case<ScanInput, ScanExpected>;
using NormCase = Case<std::vector<Token>, std::vector<Token>>;
using ShuntCase = Case<std::vector<Token>, std::vector<Token>>;

} // namespace

void unit_parser(TestContext &ctx) {

    // Tokenizations
    const std::vector<TokCase> tok_cases = {
        {.input = "1+2",
         .expected =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Number, OpId::Count, "2"}}},

        {.input = "-3.5",
         .expected = {{TokenKind::Op, OpId::Negate, ""}, {TokenKind::Number, OpId::Count, "3.5"}}},

        {.input = "-+2",
         .expected = {{TokenKind::Op, OpId::Negate, ""}, {TokenKind::Number, OpId::Count, "2"}}},

        {.input = "sin(2i)",
         .expected =
             {{TokenKind::Op, OpId::Sin, ""},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "2i"},
              {TokenKind::RParen, OpId::Count, ""}}},

        {.input = "-2 ³√( 3 ( π ",
         .expected =
             {{TokenKind::Op, OpId::Negate, ""},
              {TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Op, OpId::Cbrt, ""},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "π"}}},

        {.input = "1.2e-3i", .expected = {{TokenKind::Number, OpId::Count, "1.2e-3i"}}},

        {.input = "1+-2",
         .expected =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Op, OpId::Negate, ""},
              {TokenKind::Number, OpId::Count, "2"}}},

        {.input = "(-2)",
         .expected =
             {{TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Op, OpId::Negate, ""},
              {TokenKind::Number, OpId::Count, "2"},
              {TokenKind::RParen, OpId::Count, ""}}},

        {.input = "asinh(2)",
         .expected =
             {{TokenKind::Op, OpId::Asinh, ""},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "2"},
              {TokenKind::RParen, OpId::Count, ""}}},

        {.input = "sqrt(2)",
         .expected =
             {{TokenKind::Op, OpId::Sqrt, ""},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "2"},
              {TokenKind::RParen, OpId::Count, ""}}},

        {.input = "2³",
         .expected = {{TokenKind::Number, OpId::Count, "2"}, {TokenKind::Op, OpId::Cube, ""}}},
    };

    // Normalizations
    const std::vector<NormCase> norm_cases = {
        {.input =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Number, OpId::Count, "2"}},
         .expected =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Number, OpId::Count, "2"}}},

        {.input =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Number, OpId::Count, "2"}},
         .expected =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Number, OpId::Count, "2"}}},
        {.input =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Number, OpId::Count, "2"}},
         .expected =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Op, OpId::Sub, ""},
              {TokenKind::Number, OpId::Count, "2"}}},

        // Implicit multipications
        {.input =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "3"}},
         .expected =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Op, OpId::Mul, ""},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "3"}}},

        {.input =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Op, OpId::Sin, ""},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::RParen, OpId::Count, ""}},
         .expected =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Op, OpId::Mul, ""},
              {TokenKind::Op, OpId::Sin, ""},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::RParen, OpId::Count, ""}}},

        {.input =
             {{TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Op, OpId::Fact, ""},
              {TokenKind::Number, OpId::Count, "2"}},
         .expected =
             {{TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Op, OpId::Fact, ""},
              {TokenKind::Op, OpId::Mul, ""},
              {TokenKind::Number, OpId::Count, "2"}}},
    };

    // Scanifications
    const std::vector<ScanCase> scan_cases = {
        {.input = {.text = "123", .start = 0}, .expected = {.view = "123", .next = 3}},
        {.input = {.text = "12.34", .start = 0}, .expected = {.view = "12.34", .next = 5}},
        {.input = {.text = ".5", .start = 0}, .expected = {.view = ".5", .next = 2}},
        {.input = {.text = "5.", .start = 0}, .expected = {.view = "5.", .next = 2}},
        {.input = {.text = "1e10", .start = 0}, .expected = {.view = "1e10", .next = 4}},
        {.input = {.text = "1e-3", .start = 0}, .expected = {.view = "1e-3", .next = 4}},
        {.input = {.text = "1e+0", .start = 0}, .expected = {.view = "1e+0", .next = 4}},
        {.input = {.text = "1e+", .start = 0}, .expected = {.view = "1", .next = 1}},
        {.input = {.text = "1e-3i", .start = 0}, .expected = {.view = "1e-3", .next = 4}},
        {.input = {.text = "xx12.3", .start = 2}, .expected = {.view = "12.3", .next = 6}},
        {.input = {.text = "abc", .start = 0}, .expected = {.view = "", .next = 0}},
        {.input = {.text = ".", .start = 0}, .expected = {.view = "", .next = 0}},
    };

    // Shuntifications
    const std::vector<ShuntCase> shunt_cases = {
        {.input =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Op, OpId::Mul, ""},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Op, OpId::Pow, ""},
              {TokenKind::Number, OpId::Count, "4"}},
         .expected =
             {{TokenKind::Number, OpId::Count, "1"},
              {TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Number, OpId::Count, "4"},
              {TokenKind::Op, OpId::Pow, ""},
              {TokenKind::Op, OpId::Mul, ""},
              {TokenKind::Op, OpId::Add, ""}}},

        {.input =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Op, OpId::Pow, ""},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Op, OpId::Pow, ""},
              {TokenKind::Number, OpId::Count, "4"}},
         .expected =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Number, OpId::Count, "4"},
              {TokenKind::Op, OpId::Pow, ""},
              {TokenKind::Op, OpId::Pow, ""}}},

        {.input =
             {{TokenKind::Op, OpId::Sin, ""},
              {TokenKind::Op, OpId::Negate, ""},
              {TokenKind::Number, OpId::Count, "2"}},
         .expected =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Op, OpId::Negate, ""},
              {TokenKind::Op, OpId::Sin, ""}}},

        {.input =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::LParen, OpId::Count, ""},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Number, OpId::Count, "4"},
              {TokenKind::RParen, OpId::Count, ""}},
         .expected =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Number, OpId::Count, "4"},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Op, OpId::Mul, ""}}},

        {.input =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Op, OpId::Pow, ""},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Op, OpId::Percent, ""},
              {TokenKind::Op, OpId::Add, ""},
              {TokenKind::Number, OpId::Count, "4"}},
         .expected =
             {{TokenKind::Number, OpId::Count, "2"},
              {TokenKind::Number, OpId::Count, "3"},
              {TokenKind::Op, OpId::Percent, ""},
              {TokenKind::Op, OpId::Pow, ""},
              {TokenKind::Number, OpId::Count, "4"},
              {TokenKind::Op, OpId::Add, ""}}},
    };

    for (const auto &tc : tok_cases) {
        EXPECT_EQ(ctx, p::tokenize(tc.input), tc.expected);
    }

    for (const auto &tc : norm_cases) {
        EXPECT_EQ(ctx, d::normalize(tc.input), tc.expected);
    }

    for (const auto &tc : scan_cases) {
        std::size_t next = tc.input.start;
        const std::string_view view = d::scan_number(tc.input.text, tc.input.start, next);
        EXPECT_EQ(ctx, view, tc.expected.view);
        EXPECT_EQ(ctx, next, tc.expected.next);
    }

    for (const auto &tc : shunt_cases) {
        EXPECT_EQ(ctx, p::shunting_yard(tc.input), tc.expected);
    }
}
