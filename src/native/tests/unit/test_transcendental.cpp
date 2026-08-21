#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <boost/math/constants/constants.hpp>
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
    TEST_CASE(ctx, "real :: sqrt", { EXPECT_EQ(ctx, c.sqrt(4.0), 2.0); });
    TEST_CASE(ctx, "real :: sqrt domain throws", { EXPECT_THROWS(ctx, c.sqrt(-1.0)); });

    TEST_CASE(ctx, "real :: cbrt", { EXPECT_TRUE(ctx, approx(c.cbrt(27.0), 3.0, 1e-12)); });

    TEST_CASE(ctx, "real :: root cube", { EXPECT_TRUE(ctx, approx(c.root(27.0, 3.0), 3.0)); });
    TEST_CASE(
        ctx, "real :: root negative odd", { EXPECT_TRUE(ctx, approx(c.root(-8.0, 3.0), -2.0)); });
    TEST_CASE(ctx, "real :: root domain throws", { EXPECT_THROWS(ctx, c.root(-8.0, 2.0)); });

    TEST_CASE(ctx, "real :: log base ten", { EXPECT_TRUE(ctx, approx(c.log(100.0), 2.0)); });
    TEST_CASE(ctx, "real :: ln", { EXPECT_TRUE(ctx, approx(c.ln(std::exp(1.0)), 1.0)); });
    TEST_CASE(ctx, "real :: log domain throws", { EXPECT_THROWS(ctx, c.log(0.0)); });
    TEST_CASE(ctx, "real :: ln domain throws", { EXPECT_THROWS(ctx, c.ln(0.0)); });

    TEST_CASE(ctx, "real :: pow int exp", { EXPECT_EQ(ctx, c.pow(2.0, 10LL), 1024.0); });
    TEST_CASE(ctx, "real :: pow int negative exp", { EXPECT_EQ(ctx, c.pow(2.0, -3LL), 0.125); });
    TEST_CASE(
        ctx, "real :: pow zero negative exp throws", { EXPECT_THROWS(ctx, c.pow(0.0, -1LL)); });
    TEST_CASE(ctx, "real :: pow frac exp", { EXPECT_TRUE(ctx, approx(c.pow(9.0, 0.5), 3.0)); });

    // ----
    // BigReal
    // ----
    TEST_CASE(ctx, "bigreal :: sqrt", { EXPECT_EQ(ctx, c.sqrt(BigReal("4.0")), BigReal("2.0")); });
    // An odd degree reached through a division that leaves a guard-digit residue is still odd.
    TEST_CASE(ctx, "bigreal :: root of a negative takes a quotient degree", {
        EXPECT_TRUE(
            ctx,
            approx_big(
                c.root(BigReal("-8"), BigReal("9e400") / BigReal("3e400")),
                BigReal("-2"),
                BigReal("1e-40")));
    });
    TEST_CASE(
        ctx, "bigreal :: sqrt domain throws", { EXPECT_THROWS(ctx, c.sqrt(BigReal("-1.0"))); });

    // Transcendentals: use tolerant comparisons.
    TEST_CASE(ctx, "bigreal :: log underflow range", {
        EXPECT_TRUE(
            ctx,
            approx_big(c.log(BigReal("1e-100000000")), BigReal("-100000000"), BigReal("1e-30")));
    });

    TEST_CASE(ctx, "bigreal :: log overflow range", {
        EXPECT_TRUE(
            ctx, approx_big(c.log(BigReal("1e100000000")), BigReal("100000000"), BigReal("1e-30")));
    });

    TEST_CASE(ctx, "bigreal :: ln one", {
        EXPECT_TRUE(ctx, approx_big(c.ln(BigReal("1")), BigReal("0"), BigReal("1e-40")));
    });
    TEST_CASE(ctx, "bigreal :: ln negative", {
        EXPECT_TRUE(ctx, c.ln(BigReal("1e-100000000")) < BigReal("0"));
    });
    TEST_CASE(ctx, "bigreal :: ln ordering", {
        EXPECT_TRUE(ctx, c.ln(BigReal("1e-100000000")) < c.ln(BigReal("1e-1")));
    });
    TEST_CASE(ctx, "bigreal :: root negative odd", {
        EXPECT_TRUE(
            ctx, approx_big(c.root(BigReal("-27"), BigReal("3")), BigReal("-3"), BigReal("1e-30")));
    });

    // ----
    // Complex
    // ----
    TEST_CASE(ctx, "complex :: log domain throws", { EXPECT_THROWS(ctx, c.log(Z(0.0, 0.0))); });
    TEST_CASE(ctx, "complex :: ln domain throws", { EXPECT_THROWS(ctx, c.ln(Z(0.0, 0.0))); });

    const Z i(0.0, 1.0);
    const Z i_pow = c.pow(i, Z(2.0, 0.0));
    TEST_CASE(ctx, "complex :: pow i squared real", {
        EXPECT_TRUE(ctx, approx(i_pow.real(), -1.0, 1e-12));
    });
    TEST_CASE(ctx, "complex :: pow i squared imag", {
        EXPECT_TRUE(ctx, approx(i_pow.imag(), 0.0, 1e-12));
    });

    const Z z_sqrt = c.sqrt(Z(-4.0, 0.0));
    TEST_CASE(ctx, "complex :: sqrt negative real", {
        EXPECT_TRUE(ctx, approx(z_sqrt.real(), 0.0, 1e-12));
    });
    TEST_CASE(ctx, "complex :: sqrt negative imag", {
        EXPECT_TRUE(ctx, approx(z_sqrt.imag(), 2.0, 1e-12));
    });

    // ----
    // BigComplex
    // ----
    const BC z("1e400", "1");
    const BC z_pow2 = c.pow(z, BC("2"));
    TEST_CASE(
        ctx, "bigcomplex :: pow square", { EXPECT_TRUE(ctx, approx_big(z_pow2, c.mul(z, z))); });

    const BC z_sqrt_bc = c.sqrt(z);
    TEST_CASE(ctx, "bigcomplex :: sqrt roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.mul(z_sqrt_bc, z_sqrt_bc), z));
    });

    const BC z_root = c.root(z, BC("2"));
    TEST_CASE(ctx, "bigcomplex :: root roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.pow(z_root, BC("2")), z));
    });

    const BC z_log = c.log(z);
    TEST_CASE(ctx, "bigcomplex :: log pow roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.pow(BC("10"), z_log), z, BF("1e-20")));
    });

    const BC z_ln("1e10", "1e-5");
    const BF &ln_ten = boost::math::constants::ln_ten<BF>();
    const BC ln_from_log = c.log(z_ln) * BC(ln_ten, BF(0));
    TEST_CASE(ctx, "bigcomplex :: ln matches log", {
        EXPECT_TRUE(ctx, approx_big(c.ln(z_ln), ln_from_log, BF("1e-20")));
    });
}
