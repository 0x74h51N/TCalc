#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

void unit_arithmetic(TestContext &ctx) {
    Calculator c;
    using Z = Calculator::Complex;

    // Real arithmetic
    TEST_CASE(ctx, "real :: add", { EXPECT_EQ(ctx, c.add(2.0, 3.0), 5.0); });
    TEST_CASE(ctx, "real :: sub", { EXPECT_EQ(ctx, c.sub(2.0, 3.0), -1.0); });
    TEST_CASE(ctx, "real :: mul", { EXPECT_EQ(ctx, c.mul(2.0, 3.0), 6.0); });
    TEST_CASE(ctx, "real :: div", { EXPECT_EQ(ctx, c.div(6.0, 3.0), 2.0); });
    TEST_CASE(ctx, "real :: div zero throws", { EXPECT_THROWS(ctx, c.div(1.0, 0.0)); });

    TEST_CASE(ctx, "real :: mod", { EXPECT_EQ(ctx, c.mod(8.0, 3.0), 2.0); });
    TEST_CASE(ctx, "real :: mod negative", { EXPECT_EQ(ctx, c.mod(-8.0, 3.0), -2.0); });
    TEST_CASE(ctx, "real :: mod zero throws", { EXPECT_THROWS(ctx, c.mod(1.0, 0.0)); });

    TEST_CASE(ctx, "real :: intdiv round down", { EXPECT_EQ(ctx, c.intdiv(5.9, 2.0), 2LL); });
    TEST_CASE(ctx, "real :: intdiv exact", { EXPECT_EQ(ctx, c.intdiv(5.0, 2.0), 2LL); });
    TEST_CASE(ctx, "real :: intdiv negative a", { EXPECT_EQ(ctx, c.intdiv(-5.9, 2.0), -2LL); });
    TEST_CASE(
        ctx, "real :: intdiv negative a exact", { EXPECT_EQ(ctx, c.intdiv(-5.0, 2.0), -2LL); });
    TEST_CASE(ctx, "real :: intdiv negative b", { EXPECT_EQ(ctx, c.intdiv(5.9, -2.0), -2LL); });
    TEST_CASE(ctx, "real :: intdiv negative both", { EXPECT_EQ(ctx, c.intdiv(-5.9, -2.0), 2LL); });
    TEST_CASE(ctx, "real :: intdiv non integer b", { EXPECT_EQ(ctx, c.intdiv(5.0, 2.5), 2LL); });
    TEST_CASE(ctx, "real :: intdiv zero throws", { EXPECT_THROWS(ctx, c.intdiv(1.0, 0.0)); });

    // Complex arithmetic
    const Z i(0.0, 1.0);
    TEST_CASE(
        ctx, "complex :: add", { EXPECT_EQ(ctx, c.add(Z(1.0, 2.0), Z(3.0, 4.0)), Z(4.0, 6.0)); });
    TEST_CASE(ctx, "complex :: mul i squared", { EXPECT_EQ(ctx, c.mul(i, i), Z(-1.0, 0.0)); });
    TEST_CASE(ctx, "complex :: div zero throws", {
        EXPECT_THROWS(ctx, c.div(Z(1.0, 0.0), Z(0.0, 0.0)));
    });

    // BigReal arithmetic
    const BigReal a("1.5");
    const BigReal b("2.0");
    TEST_CASE(ctx, "bigreal :: add", { EXPECT_EQ(ctx, c.add(a, b), BigReal("3.5")); });
    TEST_CASE(ctx, "bigreal :: mul", { EXPECT_EQ(ctx, c.mul(a, b), BigReal("3.0")); });
    TEST_CASE(ctx, "bigreal :: intdiv round down", {
        EXPECT_EQ(ctx, c.intdiv(BigReal("5.9"), BigReal("2.0")), BigReal("2"));
    });
    TEST_CASE(ctx, "bigreal :: intdiv negative", {
        EXPECT_EQ(ctx, c.intdiv(BigReal("-5"), BigReal("2")), BigReal("-2"));
    });
    TEST_CASE(ctx, "bigreal :: div zero throws", {
        EXPECT_THROWS(ctx, c.div(BigReal("1.0"), BigReal("0.0")));
    });
    TEST_CASE(ctx, "bigreal :: mod negative", {
        EXPECT_EQ(ctx, c.mod(BigReal("-8.5"), BigReal("2.5")), BigReal("-1.0"));
    });
    // An exact division used to come back as the divisor itself.
    TEST_CASE(ctx, "bigreal :: mod exact division", {
        EXPECT_EQ(ctx, c.mod(BigReal("93"), BigReal("3")), BigReal("0"));
    });
    TEST_CASE(ctx, "bigreal :: mod exact division negative a", {
        EXPECT_EQ(ctx, c.mod(BigReal("-93"), BigReal("3")), BigReal("0"));
    });
    TEST_CASE(ctx, "bigreal :: mod exact division negative b", {
        EXPECT_EQ(ctx, c.mod(BigReal("93"), BigReal("-3")), BigReal("0"));
    });
    TEST_CASE(ctx, "bigreal :: mod exact division fractional", {
        EXPECT_EQ(ctx, c.mod(BigReal("9.6"), BigReal("1.2")), BigReal("0"));
    });
    TEST_CASE(ctx, "bigreal :: intdiv exact division", {
        EXPECT_EQ(ctx, c.intdiv(BigReal("93"), BigReal("3")), BigReal("31"));
    });
    TEST_CASE(ctx, "bigreal :: intdiv exact division negative", {
        EXPECT_EQ(ctx, c.intdiv(BigReal("-93"), BigReal("3")), BigReal("-31"));
    });
    TEST_CASE(ctx, "bigreal :: intdiv exact division fractional", {
        EXPECT_EQ(ctx, c.intdiv(BigReal("9.6"), BigReal("1.2")), BigReal("8"));
    });

    // BigComplex arithmetic
    const BigComplex bc_a("1.5", "-2.5");
    const BigComplex bc_b("0.5", "0.25");
    const BigComplex bc_div = c.div(bc_a, bc_b);
    TEST_CASE(ctx, "bigcomplex :: div roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.mul(bc_div, bc_b), bc_a));
    });
}
