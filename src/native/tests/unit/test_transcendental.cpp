#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <cmath>
#include <limits>

void unit_transcendental(TestContext &ctx) {
    Calculator c;
    using Z = Calculator::Complex;
    using BC = BigComplex;
    using BF = boost::multiprecision::cpp_bin_float_50;

    // ----
    // Real
    // ----
    EXPECT_EQ(ctx, c.sqrt(4.0), 2.0);
    EXPECT_THROWS(ctx, c.sqrt(-1.0));

    EXPECT_TRUE(ctx, approx(c.cbrt(27.0), 3.0, 1e-12));

    EXPECT_TRUE(ctx, approx(c.root(27.0, 3.0), 3.0));
    EXPECT_TRUE(ctx, approx(c.root(-8.0, 3.0), -2.0));
    EXPECT_THROWS(ctx, c.root(-8.0, 2.0));

    EXPECT_TRUE(ctx, approx(c.log(100.0), 2.0));
    EXPECT_TRUE(ctx, approx(c.ln(std::exp(1.0)), 1.0));
    EXPECT_THROWS(ctx, c.log(0.0));
    EXPECT_THROWS(ctx, c.ln(0.0));

    EXPECT_EQ(ctx, c.pow(2.0, 10LL), 1024.0);
    EXPECT_EQ(ctx, c.pow(2.0, -3LL), 0.125);
    EXPECT_THROWS(ctx, c.pow(0.0, -1LL));
    EXPECT_TRUE(ctx, approx(c.pow(9.0, 0.5), 3.0));

    // ----
    // BigReal
    // ----
    EXPECT_EQ(ctx, c.sqrt(BigReal("4.0")), BigReal("2.0"));
    EXPECT_THROWS(ctx, c.sqrt(BigReal("-1.0")));

    // Transcendentals: use tolerant comparisons.
    EXPECT_TRUE(
        ctx, approx_big(c.log(BigReal("1e-100000000")), BigReal("-100000000"), BigReal("1e-30")));
    EXPECT_TRUE(ctx,
                approx_big(c.log(BigReal("1e100000000")), BigReal("100000000"), BigReal("1e-30")));
    EXPECT_TRUE(ctx, approx_big(c.ln(BigReal("1")), BigReal("0"), BigReal("1e-40")));
    EXPECT_TRUE(ctx, c.ln(BigReal("1e-100000000")) < BigReal("0"));
    EXPECT_TRUE(ctx, c.ln(BigReal("1e-100000000")) < c.ln(BigReal("1e-1")));

    // ----
    // Complex
    // ----
    EXPECT_THROWS(ctx, c.log(Z(0.0, 0.0)));
    EXPECT_THROWS(ctx, c.ln(Z(0.0, 0.0)));

    // ----
    // BigComplex
    // ----
    const BC z("1e400", "1");
    const BC z_pow2 = c.pow(z, BC("2"));
    EXPECT_TRUE(ctx, approx_big(z_pow2, c.mul(z, z)));

    const BC z_sqrt = c.sqrt(z);
    EXPECT_TRUE(ctx, approx_big(c.mul(z_sqrt, z_sqrt), z));

    const BC z_root = c.root(z, BC("2"));
    EXPECT_TRUE(ctx, approx_big(c.pow(z_root, BC("2")), z));

    const BC z_log = c.log(z); // log10
    EXPECT_TRUE(ctx, approx_big(c.pow(BC("10"), z_log), z, BF("1e-20")));
}
