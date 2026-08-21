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

    // Integer extraction on values that are exactly an integer at the 50 digits BigReal
    // advertises but sit just under it in the guard digits it keeps internally.
    struct IntPartCase {
        const char *id;
        BigReal input;
        const char *trunc;
        const char *floor;
        const char *ceil;
    };
    const BigReal third = BigReal("1") / BigReal("3");
    const std::vector<IntPartCase> int_part_cases = {
        {"exact big quotient", BigReal("9e400") / BigReal("3e400"), "3", "3", "3"},
        {"exact quotient", BigReal("93") / BigReal("3"), "31", "31", "31"},
        {"quotient times its divisor", third * BigReal("3"), "1", "1", "1"},
        {"negative product", -(third * BigReal("3")), "-1", "-1", "-1"},
        // A large magnitude leaves a correspondingly large residue, 6.7e-9 here, so the
        // threshold has to scale with the value rather than being a fixed epsilon.
        {"large magnitude",
         (BigReal("1e60") / BigReal("3")) * BigReal("3"),
         "1e60",
         "1e60",
         "1e60"},
        {"a plain fraction", BigReal("2.7"), "2", "2", "3"},
        {"a negative fraction", BigReal("-2.7"), "-2", "-3", "-2"},
        {"an integer", BigReal("3"), "3", "3", "3"},
        {"zero", BigReal("0"), "0", "0", "0"},
        {"below one", BigReal("1e-60"), "0", "0", "1"},
        {"above minus one", BigReal("-1e-60"), "0", "-1", "0"},
    };

    for (const auto &tc : int_part_cases) {
        test_detail::with_case(ctx, std::string("bigreal :: trunc :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, c.trunc(tc.input), BigReal(tc.trunc));
        });
        test_detail::with_case(ctx, std::string("bigreal :: floor :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, c.floor(tc.input), BigReal(tc.floor));
        });
        test_detail::with_case(ctx, std::string("bigreal :: ceil :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, c.ceil(tc.input), BigReal(tc.ceil));
        });
    }

    // BigComplex arithmetic
    const BigComplex bc_a("1.5", "-2.5");
    const BigComplex bc_b("0.5", "0.25");
    const BigComplex bc_div = c.div(bc_a, bc_b);
    TEST_CASE(ctx, "bigcomplex :: div roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.mul(bc_div, bc_b), bc_a));
    });
}
