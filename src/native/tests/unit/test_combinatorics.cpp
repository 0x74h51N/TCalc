#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

void unit_combinatorics(TestContext &ctx) {
    Calculator c;

    TEST_CASE(ctx, "fact :: zero", { EXPECT_TRUE(ctx, c.fact(0.0) == 1.0); });
    TEST_CASE(ctx, "fact :: positive int", { EXPECT_TRUE(ctx, c.fact(5.0) == 120.0); });
    TEST_CASE(ctx, "fact :: domain throws", { EXPECT_THROWS(ctx, c.fact(-1.0)); });
    TEST_CASE(ctx, "fact :: fractional", { EXPECT_TRUE(ctx, c.fact(0.25) == 0.9064024770554771); });

    TEST_CASE(ctx, "gamma :: one", { EXPECT_TRUE(ctx, c.gamma(1.0) == 1.0); });
    TEST_CASE(ctx, "gamma :: half positive", { EXPECT_TRUE(ctx, c.gamma(0.5) > 1.7); });
    TEST_CASE(ctx, "gamma :: domain zero throws", { EXPECT_THROWS(ctx, c.gamma(0.0)); });
    TEST_CASE(ctx, "gamma :: domain negative int throws", { EXPECT_THROWS(ctx, c.gamma(-2.0)); });

    TEST_CASE(ctx, "bigreal :: gamma", {
        EXPECT_TRUE(ctx, approx_big(c.gamma(BigReal("6")), BigReal("120"), BigReal("1e-30")));
    });
    TEST_CASE(ctx, "bigreal :: fact large", {
        EXPECT_TRUE(
            ctx,
            approx_big(c.fact(BigReal("20")), BigReal("2432902008176640000"), BigReal("1e-10")));
    });
    TEST_CASE(ctx, "bigreal :: fact domain throws", { EXPECT_THROWS(ctx, c.fact(BigReal("-1"))); });
    TEST_CASE(ctx, "bigreal :: fact fractional", {
        EXPECT_TRUE(
            ctx,
            approx_big(c.fact(BigReal("0.25")), BigReal("0.9064024770554771"), BigReal("1e-10")));
    });

    TEST_CASE(
        ctx, "bigreal :: gamma domain zero throws", { EXPECT_THROWS(ctx, c.gamma(BigReal("0"))); });
    TEST_CASE(ctx, "bigreal :: gamma domain negative int throws", {
        EXPECT_THROWS(ctx, c.gamma(BigReal("-2")));
    });

    const BigReal f199 = c.fact(BigReal("199"));
    const BigReal f200 = c.fact(BigReal("200"));
    TEST_CASE(ctx, "bigreal :: fact ratio", {
        EXPECT_TRUE(ctx, approx_big(f200 / f199, BigReal("200"), BigReal("1e-30")));
    });

    TEST_CASE(ctx, "permute :: basic", { EXPECT_TRUE(ctx, c.permute(5, 2) == BigReal("20")); });
    TEST_CASE(ctx, "choose :: basic", { EXPECT_TRUE(ctx, c.choose(5, 2) == BigReal("10")); });
    TEST_CASE(ctx, "choose :: out of range", { EXPECT_TRUE(ctx, c.choose(5, 6) == BigReal("0")); });
    TEST_CASE(
        ctx, "permute :: out of range", { EXPECT_TRUE(ctx, c.permute(5, 6) == BigReal("0")); });
    TEST_CASE(ctx, "permute :: domain throws", { EXPECT_THROWS(ctx, c.permute(-1, 2)); });
    TEST_CASE(ctx, "choose :: domain throws", { EXPECT_THROWS(ctx, c.choose(3, -2)); });
}
