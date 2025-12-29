#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "internal/test_helpers.hpp"
#include "parser/pub/parser.hpp"

namespace {

using tcalc::ops::OpId;
using tcalc::parser::Token;
using tcalc::parser::TokenKind;

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

    const double d = 1.0 / 3.0;
    std::ostringstream expected_double;
    expected_double << std::setprecision(std::numeric_limits<double>::max_digits10) << d;
    EXPECT_EQ(ctx, printed(d), expected_double.str());

    const BigReal big("1.234567890123456789");
    std::ostringstream expected_big;
    expected_big << std::setprecision(std::numeric_limits<BigReal>::digits10) << big;
    EXPECT_EQ(ctx, printed(big), expected_big.str());

    EXPECT_EQ(ctx, printed(42), "42");
    EXPECT_EQ(ctx, printed(NoStream{1}), "<unprintable>");

    EXPECT_EQ(ctx, printed(std::vector<int>{}), "[]");
    EXPECT_EQ(ctx, printed(std::vector<int>{7}), "[7]");
    EXPECT_EQ(ctx, printed(std::vector<std::string>{"a", "b"}), "[a, b]");

    const Token number{TokenKind::Number, OpId::Count, "2"};
    const Token add{TokenKind::Op, OpId::Add, ""};
    const Token lparen{TokenKind::LParen, OpId::Count, ""};
    EXPECT_EQ(
        ctx,
        printed(number),
        "Token{kind=" + std::to_string(static_cast<int>(number.kind)) + ", op_id=" +
            std::to_string(static_cast<int>(number.op_id)) + ", value=\"" + number.value + "\"}");
    EXPECT_EQ(
        ctx,
        printed(std::vector<Token>{number, add, lparen}),
        "[" +
            ("Token{kind=" + std::to_string(static_cast<int>(number.kind)) + ", op_id=" +
             std::to_string(static_cast<int>(number.op_id)) + ", value=\"" + number.value + "\"}") +
            ", " +
            ("Token{kind=" + std::to_string(static_cast<int>(add.kind)) + ", op_id=" +
             std::to_string(static_cast<int>(add.op_id)) + ", value=\"" + add.value + "\"}") +
            ", " +
            ("Token{kind=" + std::to_string(static_cast<int>(lparen.kind)) + ", op_id=" +
             std::to_string(static_cast<int>(lparen.op_id)) + ", value=\"" + lparen.value + "\"}") +
            "]");

    EXPECT_TRUE(ctx, approx(1.0, 1.0 + 1e-13));
    EXPECT_TRUE(ctx, !approx(1.0, 1.0 + 1e-6));

    EXPECT_TRUE(ctx, approx_big(BigReal("1"), BigReal("1.0000000000001"), BigReal("1e-10")));
    EXPECT_TRUE(ctx, !approx_big(BigReal("1"), BigReal("1.1"), BigReal("1e-3")));

    TestContext local{};
    local.verbose = false;
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
}
