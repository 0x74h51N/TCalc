#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <cmath>
#include <cstdint>
#include <limits>

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

    // A power refused by the exact kernel, computed from its exact base and exponent (#231).
    // Each part within `tol` ulps of the double nearest the exact value; an exact zero part is
    // +0. The ulp is taken on got's side: below a power of two it is half the one above.
    const auto within = [](double got, double want, int tol) {
        if (want == 0.0)
            return got == 0.0 && !std::signbit(got);
        const double ulp = std::fabs(std::nextafter(want, got) - want);
        return std::fabs(got - want) <= tol * ulp;
    };
    constexpr std::int64_t kMin = (std::numeric_limits<std::int64_t>::min)();
    constexpr std::int64_t kMax = (std::numeric_limits<std::int64_t>::max)();

    struct RealPowerCase {
        const char *id;
        Rational x;
        Rational y;
        double expected;
        int tol = 1;
    };
    const std::vector<RealPowerCase> real_power_cases = {
        {.id = "a positive base",
         .x = Rational(17),
         .y = Rational(8711, 674),
         .expected = 7993386127887876.0},
        {.id = "a base that is no double",
         .x = Rational(38, 3),
         .y = Rational(20993, 82),
         .expected = 1.9724528358173784e+282},
        {.id = "a result near 1e267",
         .x = Rational(10),
         .y = Rational(331897, 1242),
         .expected = 1.6898894438436359e+267},
        {.id = "a base below one",
         .x = Rational(1, 2),
         .y = Rational(8711, 674),
         .expected = 0.00012864363123970833},
        {.id = "an odd degree past 2^53",
         .x = Rational(-2),
         .y = Rational(1, 9007199254740993),
         .expected = -1.0},
        {.id = "int64 min at an odd degree",
         .x = Rational(kMin),
         .y = Rational(1, kMax),
         .expected = -1.0},
        {.id = "a cube root past 2^53",
         .x = Rational(kMax),
         .y = Rational(1, 3),
         .expected = 2097152.0},
        {.id = "a cube root keeps the real root kernel",
         .x = Rational(109889063671LL),
         .y = Rational(1, 3),
         .expected = 4789.80858033901,
         .tol = 0},
        {.id = "a negative base at an odd degree",
         .x = Rational(-10),
         .y = Rational(1, 5),
         .expected = -1.5848931924611134},
    };
    for (const auto &tc : real_power_cases) {
        test_detail::with_case(ctx, std::string("real_power :: ") + tc.id, [&] {
            EXPECT_TRUE(ctx, within(c.real_power(tc.x, tc.y), tc.expected, tc.tol));
        });
    }

    struct PrincipalPowerCase {
        const char *id;
        Rational x;
        Rational y;
        Z expected;
    };
    const std::vector<PrincipalPowerCase> principal_power_cases = {
        {.id = "an exponent near one",
         .x = Rational(-2),
         .y = Rational(10000000000001LL, 10000000000000LL),
         .expected = Z(-2.0000000000001386, -6.283185307180022e-13)},
        {.id = "three halves on the axis",
         .x = Rational(-2),
         .y = Rational(3, 2),
         .expected = Z(0.0, -2.8284271247461903)},
        {.id = "a fraction base on the axis",
         .x = Rational(-1, 2),
         .y = Rational(3, 2),
         .expected = Z(0.0, -0.3535533905932738)},
        {.id = "a half of minus four",
         .x = Rational(-4),
         .y = Rational(1, 2),
         .expected = Z(0.0, 2.0)},
        {.id = "a large result on the axis",
         .x = Rational(-10),
         .y = Rational(301, 2),
         .expected = Z(0.0, 3.1622776601683793e+150)},
        {.id = "a large angle",
         .x = Rational(-3),
         .y = Rational(609803, 1058),
         .expected = Z(3.8745589136552445e+274, 9.2182330420805e+274)},
        {.id = "a half of int64 min",
         .x = Rational(kMin),
         .y = Rational(1, 2),
         .expected = Z(0.0, 3037000499.97605)},
    };
    for (const auto &tc : principal_power_cases) {
        test_detail::with_case(ctx, std::string("principal_power :: ") + tc.id, [&] {
            const Z got = c.principal_power(tc.x, tc.y);
            EXPECT_TRUE(ctx, within(got.real(), tc.expected.real(), 1));
            EXPECT_TRUE(ctx, within(got.imag(), tc.expected.imag(), 1));
        });
    }
}
