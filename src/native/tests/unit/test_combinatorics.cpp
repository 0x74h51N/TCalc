#include "calculator.hpp"
#include "internal/test_helpers.hpp"

void unit_combinatorics(TestContext& ctx) {
    Calculator c;

    EXPECT_TRUE(ctx, c.fact(0.0) == 1.0);
    EXPECT_TRUE(ctx, c.fact(5.0) == 120.0);
    EXPECT_THROWS(ctx, c.fact(-1.0));
    EXPECT_THROWS(ctx, c.fact(1.5));

    EXPECT_TRUE(ctx, c.gamma(1.0) == 1.0);
    EXPECT_TRUE(ctx, c.gamma(0.5) > 1.7);
    EXPECT_THROWS(ctx, c.gamma(0.0));
    EXPECT_THROWS(ctx, c.gamma(-2.0));

    EXPECT_TRUE(ctx, approx_big(c.gamma(BigReal("6")), BigReal("120"), BigReal("1e-30")));
    EXPECT_TRUE(ctx, approx_big(c.fact(BigReal("20")), BigReal("2432902008176640000"), BigReal("1e-10")));
    EXPECT_THROWS(ctx, c.fact(BigReal("-1")));
    EXPECT_THROWS(ctx, c.fact(BigReal("1.5")));
    
    EXPECT_THROWS(ctx, c.gamma(BigReal("0")));
    EXPECT_THROWS(ctx, c.gamma(BigReal("-2")));

    const BigReal f199 = c.fact(BigReal("199"));
    const BigReal f200 = c.fact(BigReal("200"));
    EXPECT_TRUE(ctx, approx_big(f200 / f199, BigReal("200"), BigReal("1e-30")));

    EXPECT_TRUE(ctx, c.permute(5, 2) == BigReal("20"));
    EXPECT_TRUE(ctx, c.choose(5, 2) == BigReal("10"));
    EXPECT_TRUE(ctx, c.choose(5, 6) == BigReal("0"));
    EXPECT_TRUE(ctx, c.permute(5, 6) == BigReal("0"));
}
