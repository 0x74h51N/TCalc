#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "internal/test_helpers.hpp"
#include "parser/pub/parser.hpp"

namespace p = tcalc::parser;
namespace o = tcalc::ops;
namespace {

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
struct NoStream {
    int v;
};

} // namespace

void unit_helpers(TestContext &ctx) {
    auto printed = [](const auto &value) -> std::string {
        std::ostringstream oss;
        print_value(oss, value);
        return oss.str();
    };

    TEST_CASE(ctx, "print :: double precision", {
        const double d = 1.0 / 3.0;
        std::ostringstream expected_double;
        expected_double << std::setprecision(std::numeric_limits<double>::max_digits10) << d;
        EXPECT_EQ(ctx, printed(d), expected_double.str());
    });

    TEST_CASE(ctx, "print :: bigreal precision", {
        const BigReal big("1.234567890123456789");
        std::ostringstream expected_big;
        expected_big << std::setprecision(std::numeric_limits<BigReal>::digits10) << big;
        EXPECT_EQ(ctx, printed(big), expected_big.str());
    });

    TEST_CASE(ctx, "print :: integer", { EXPECT_EQ(ctx, printed(42), "42"); });
    TEST_CASE(
        ctx, "print :: unprintable", { EXPECT_EQ(ctx, printed(NoStream{1}), "<unprintable>"); });

    TEST_CASE(ctx, "print :: vector empty", { EXPECT_EQ(ctx, printed(std::vector<int>{}), "[]"); });
    TEST_CASE(
        ctx, "print :: vector single", { EXPECT_EQ(ctx, printed(std::vector<int>{7}), "[7]"); });
    TEST_CASE(ctx, "print :: vector strings", {
        EXPECT_EQ(ctx, printed(std::vector<std::string>{"a", "b"}), "[a, b]");
    });

    TEST_CASE(ctx, "print :: token", {
        const Token number{
            .kind = TokenKind::Number, .data = NumberToken{"2"}, .start_pos = 0, .end_pos = 1};

        const Token add{
            .kind = TokenKind::Op, .data = OpToken{OpId::Add}, .start_pos = 1, .end_pos = 2};

        const Token lparen{
            .kind = TokenKind::Paren,
            .data = ParenToken{ParenType::Open, ParenKind::Paren},
            .start_pos = 2,
            .end_pos = 3};

        EXPECT_EQ(ctx, printed(number), "Token{kind=Number, value=\"2\"}");

        EXPECT_EQ(
            ctx,
            printed(std::vector<Token>{number, add, lparen}),
            "[\n"
            "  Token{kind=Number, value=\"2\"},\n"
            "  Token{kind=Op, op_id=add(+)},\n"
            "  Token{kind=LParen, type=Open, kind=Paren}\n"
            "]");
    });

    TEST_CASE(ctx, "approx :: double true", { EXPECT_TRUE(ctx, approx(1.0, 1.0 + 1e-13)); });
    TEST_CASE(ctx, "approx :: double false", { EXPECT_TRUE(ctx, !approx(1.0, 1.0 + 1e-6)); });

    TEST_CASE(ctx, "approx :: bigreal true", {
        EXPECT_TRUE(ctx, approx_big(BigReal("1"), BigReal("1.0000000000001"), BigReal("1e-10")));
    });
    TEST_CASE(ctx, "approx :: bigreal false", {
        EXPECT_TRUE(ctx, !approx_big(BigReal("1"), BigReal("1.1"), BigReal("1e-3")));
    });

    TEST_CASE(ctx, "context :: counts", {
        TestContext local{};
        local.output = TestContext::OutputMode::Quiet;
        {
            std::ostringstream sink;
            auto *old_buf = std::cerr.rdbuf(sink.rdbuf());
            expect_true(local, true, "true", "test", 1);
            expect_true(local, false, "false", "test", 2);
            expect_eq(local, 1, 2, "1", "2", "test", 4);
            expect_throws(local, [] {}, "no throw", "test", 6);
            std::cerr.rdbuf(old_buf);
        }
        EXPECT_EQ(ctx, local.checks, 4);
        EXPECT_EQ(ctx, local.failures, 3);
    });
}
