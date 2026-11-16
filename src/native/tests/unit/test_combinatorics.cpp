#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <limits>
#include <vector>

namespace {

using CombFn = BigReal (Calculator::*)(long long, long long) const;

/// a and b, then the expected value as text. A null tol asserts exact equality; a tol is
/// relative, since the results span hundreds of thousands of decades.
struct CombCase {
    const char *id;
    CombFn fn;
    long long a;
    long long b;
    const char *expected;
    const char *tol;
};

} // namespace

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
    // A pole reached through a division that leaves a guard-digit residue is still a pole.
    TEST_CASE(ctx, "bigreal :: gamma domain pole from a quotient throws", {
        EXPECT_THROWS(ctx, c.gamma(BigReal("-9e400") / BigReal("3e400")));
    });
    TEST_CASE(ctx, "bigreal :: gamma domain negative int throws", {
        EXPECT_THROWS(ctx, c.gamma(BigReal("-2")));
    });

    const BigReal f199 = c.fact(BigReal("199"));
    const BigReal f200 = c.fact(BigReal("200"));
    TEST_CASE(ctx, "bigreal :: fact ratio", {
        EXPECT_TRUE(ctx, approx_big(f200 / f199, BigReal("200"), BigReal("1e-30")));
    });

    constexpr long long kMax = std::numeric_limits<long long>::max();
    const std::vector<CombCase> comb_cases = {
        {.id = "permute :: basic",
         .fn = &Calculator::permute,
         .a = 5,
         .b = 2,
         .expected = "20",
         .tol = nullptr},
        {.id = "choose :: basic",
         .fn = &Calculator::choose,
         .a = 5,
         .b = 2,
         .expected = "10",
         .tol = nullptr},
        {.id = "permute :: out of range",
         .fn = &Calculator::permute,
         .a = 5,
         .b = 6,
         .expected = "0",
         .tol = nullptr},
        {.id = "choose :: out of range",
         .fn = &Calculator::choose,
         .a = 5,
         .b = 6,
         .expected = "0",
         .tol = nullptr},
        {.id = "choose :: all",
         .fn = &Calculator::choose,
         .a = kMax,
         .b = kMax,
         .expected = "1",
         .tol = nullptr},
        {.id = "permute :: full 30",
         .fn = &Calculator::permute,
         .a = 30,
         .b = 30,
         .expected = "265252859812191058636308480000000",
         .tol = nullptr},
        {.id = "permute :: large a small b",
         .fn = &Calculator::permute,
         .a = 1000000000000000000,
         .b = 3,
         .expected = "999999999999999997000000000000000002000000000000000000",
         .tol = nullptr},
        {.id = "choose :: exact mid",
         .fn = &Calculator::choose,
         .a = 60,
         .b = 30,
         .expected = "118264581564861424",
         .tol = nullptr},
        {.id = "choose :: exact 100",
         .fn = &Calculator::choose,
         .a = 100,
         .b = 50,
         .expected = "100891344545564193334812497256",
         .tol = nullptr},
        {.id = "choose :: exact 48 digits",
         .fn = &Calculator::choose,
         .a = 176,
         .b = 60,
         .expected = "700938637298704280812242467451564851471559064800",
         .tol = nullptr},
        {.id = "permute :: million",
         .fn = &Calculator::permute,
         .a = 1000000,
         .b = 1000000,
         .expected = "8.2639316883312400623766461031726662911353479789639e+5565708",
         .tol = "1e-45"},
        {.id = "choose :: million",
         .fn = &Calculator::choose,
         .a = 1000000,
         .b = 500000,
         .expected = "7.8995787722769708417702379031791126849833959830511e+301026",
         .tol = "1e-45"},
        {.id = "permute :: past BigReal range",
         .fn = &Calculator::permute,
         .a = kMax,
         .b = kMax,
         .expected = "inf",
         .tol = nullptr},
        {.id = "choose :: past BigReal range",
         .fn = &Calculator::choose,
         .a = kMax,
         .b = kMax / 2,
         .expected = "inf",
         .tol = nullptr},
    };
    for (const auto &tc : comb_cases) {
        test_detail::with_case(ctx, tc.id, [&] {
            const BigReal got = (c.*tc.fn)(tc.a, tc.b);
            const BigReal want(tc.expected);
            if (tc.tol == nullptr)
                EXPECT_EQ(ctx, got, want);
            else
                EXPECT_TRUE(ctx, approx_big(got, want, BigReal(tc.tol) * abs(want)));
        });
    }
    TEST_CASE(ctx, "permute :: domain throws", { EXPECT_THROWS(ctx, c.permute(-1, 2)); });
    TEST_CASE(ctx, "choose :: domain throws", { EXPECT_THROWS(ctx, c.choose(3, -2)); });
}
