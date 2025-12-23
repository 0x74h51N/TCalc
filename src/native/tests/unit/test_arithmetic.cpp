#include "calc/internal/calculator.hpp"
#include "internal/test_helpers.hpp"

void unit_arithmetic(TestContext &ctx) {
    Calculator c;
    using Z = Calculator::Complex;

    // Real arithmetic
    EXPECT_EQ(ctx, c.add(2.0, 3.0), 5.0);
    EXPECT_EQ(ctx, c.sub(2.0, 3.0), -1.0);
    EXPECT_EQ(ctx, c.mul(2.0, 3.0), 6.0);
    EXPECT_EQ(ctx, c.div(6.0, 3.0), 2.0);
    EXPECT_THROWS(ctx, c.div(1.0, 0.0));

    EXPECT_EQ(ctx, c.mod(8.0, 3.0), 2.0);
    EXPECT_EQ(ctx, c.mod(-8.0, 3.0), -2.0);
    EXPECT_THROWS(ctx, c.mod(1.0, 0.0));

    EXPECT_EQ(ctx, c.intdiv(5.9, 2.0), 2LL);
    EXPECT_EQ(ctx, c.intdiv(5.0, 2.0), 2LL);
    EXPECT_EQ(ctx, c.intdiv(-5.9, 2.0), -2LL);
    EXPECT_EQ(ctx, c.intdiv(-5.0, 2.0), -2LL);
    EXPECT_EQ(ctx, c.intdiv(5.9, -2.0), -2LL);
    EXPECT_EQ(ctx, c.intdiv(-5.9, -2.0), 2LL);
    EXPECT_EQ(ctx, c.intdiv(5.0, 2.5), 2LL);
    EXPECT_THROWS(ctx, c.intdiv(1.0, 0.0));

    // Complex arithmetic
    const Z i(0.0, 1.0);
    EXPECT_EQ(ctx, c.add(Z(1.0, 2.0), Z(3.0, 4.0)), Z(4.0, 6.0));
    EXPECT_EQ(ctx, c.mul(i, i), Z(-1.0, 0.0));
    EXPECT_THROWS(ctx, c.div(Z(1.0, 0.0), Z(0.0, 0.0)));

    // BigReal arithmetic
    const BigReal a("1.5");
    const BigReal b("2.0");
    EXPECT_EQ(ctx, c.add(a, b), BigReal("3.5"));
    EXPECT_EQ(ctx, c.mul(a, b), BigReal("3.0"));
    EXPECT_EQ(ctx, c.intdiv(BigReal("5.9"), BigReal("2.0")), BigReal("2"));
    EXPECT_EQ(ctx, c.intdiv(BigReal("-5"), BigReal("2")), BigReal("-2"));
    EXPECT_THROWS(ctx, c.div(BigReal("1.0"), BigReal("0.0")));
}
