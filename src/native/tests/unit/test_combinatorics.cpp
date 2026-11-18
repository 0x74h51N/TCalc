#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <cmath>
#include <limits>
#include <vector>

namespace {

using RealFn = double (Calculator::*)(double) const;
using BigFn = BigReal (Calculator::*)(const BigReal &) const;
using CombFn = BigReal (Calculator::*)(long long, long long) const;

/// tol 0 is equality.
struct RealCase {
    const char *id;
    RealFn fn;
    double input;
    double expected;
    double tol;
};

/// Input, expected and tol as text, so no double sneaks in.
struct BigCase {
    const char *id;
    BigFn fn;
    const char *input;
    const char *expected;
    const char *tol;
};

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

    const std::vector<RealCase> real_cases = {
        {.id = "fact :: zero", .fn = &Calculator::fact, .input = 0.0, .expected = 1.0, .tol = 0.0},
        {.id = "fact :: positive int",
         .fn = &Calculator::fact,
         .input = 5.0,
         .expected = 120.0,
         .tol = 0.0},
        {.id = "fact :: fractional",
         .fn = &Calculator::fact,
         .input = 0.25,
         .expected = 0.9064024770554771,
         .tol = 0.0},
        {.id = "fact :: 18 is exact",
         .fn = &Calculator::fact,
         .input = 18.0,
         .expected = 6402373705728000.0,
         .tol = 0.0},
        {.id = "fact :: 19 is exact",
         .fn = &Calculator::fact,
         .input = 19.0,
         .expected = 121645100408832000.0,
         .tol = 0.0},
        {.id = "fact :: 21 is exact",
         .fn = &Calculator::fact,
         .input = 21.0,
         .expected = 51090942171709440000.0,
         .tol = 0.0},
        {.id = "fact :: 22 is exact",
         .fn = &Calculator::fact,
         .input = 22.0,
         .expected = 1124000727777607680000.0,
         .tol = 0.0},
        {.id = "fact :: 100 is correctly rounded",
         .fn = &Calculator::fact,
         .input = 100.0,
         .expected = 9.332621544394415e157,
         .tol = 0.0},
        {.id = "gamma :: one", .fn = &Calculator::gamma, .input = 1.0, .expected = 1.0, .tol = 0.0},
        {.id = "gamma :: 19 is exact",
         .fn = &Calculator::gamma,
         .input = 19.0,
         .expected = 6402373705728000.0,
         .tol = 0.0},
        {.id = "gamma :: 23 is exact",
         .fn = &Calculator::gamma,
         .input = 23.0,
         .expected = 1124000727777607680000.0,
         .tol = 0.0},
        {.id = "gamma :: fraction past one",
         .fn = &Calculator::gamma,
         .input = 2.5,
         .expected = 1.329340388179137,
         .tol = 1e-15},
        {.id = "gamma :: half",
         .fn = &Calculator::gamma,
         .input = 0.5,
         .expected = 1.7724538509055159,
         .tol = 1e-15},
    };
    for (const auto &tc : real_cases) {
        test_detail::with_case(ctx, tc.id, [&] {
            const double got = (c.*tc.fn)(tc.input);
            if (tc.tol == 0.0)
                EXPECT_EQ(ctx, got, tc.expected);
            else
                EXPECT_TRUE(ctx, approx(got, tc.expected, tc.tol));
        });
    }

    const std::vector<BigCase> big_cases = {
        {.id = "bigreal :: gamma",
         .fn = &Calculator::gamma,
         .input = "6",
         .expected = "120",
         .tol = "1e-30"},
        {.id = "bigreal :: fact large",
         .fn = &Calculator::fact,
         .input = "20",
         .expected = "2432902008176640000",
         .tol = "1e-10"},
        {.id = "bigreal :: fact 25 is exact",
         .fn = &Calculator::fact,
         .input = "25",
         .expected = "15511210043330985984000000",
         .tol = "0"},
        {.id = "bigreal :: gamma 26 is exact",
         .fn = &Calculator::gamma,
         .input = "26",
         .expected = "15511210043330985984000000",
         .tol = "0"},
        {.id = "bigreal :: fact fractional",
         .fn = &Calculator::fact,
         .input = "0.25",
         .expected = "0.9064024770554771",
         .tol = "1e-10"},
    };
    for (const auto &tc : big_cases) {
        test_detail::with_case(ctx, tc.id, [&] {
            EXPECT_TRUE(
                ctx,
                approx_big((c.*tc.fn)(BigReal(tc.input)), BigReal(tc.expected), BigReal(tc.tol)));
        });
    }

    TEST_CASE(ctx, "fact :: domain throws", { EXPECT_THROWS(ctx, c.fact(-1.0)); });
    // nan cannot be compared in the table; -inf is whole but no factorial, so it stays tgamma's
    // nan.
    TEST_CASE(ctx, "fact :: -inf is nan", {
        EXPECT_TRUE(ctx, std::isnan(c.fact(-std::numeric_limits<double>::infinity())));
    });
    TEST_CASE(ctx, "gamma :: domain zero throws", { EXPECT_THROWS(ctx, c.gamma(0.0)); });
    TEST_CASE(ctx, "gamma :: domain negative int throws", { EXPECT_THROWS(ctx, c.gamma(-2.0)); });
    TEST_CASE(ctx, "bigreal :: fact domain throws", { EXPECT_THROWS(ctx, c.fact(BigReal("-1"))); });
    TEST_CASE(
        ctx, "bigreal :: gamma domain zero throws", { EXPECT_THROWS(ctx, c.gamma(BigReal("0"))); });
    // A pole reached through a division that leaves a guard-digit residue is still a pole.
    TEST_CASE(ctx, "bigreal :: gamma domain pole from a quotient throws", {
        EXPECT_THROWS(ctx, c.gamma(BigReal("-9e400") / BigReal("3e400")));
    });
    TEST_CASE(ctx, "bigreal :: gamma domain negative int throws", {
        EXPECT_THROWS(ctx, c.gamma(BigReal("-2")));
    });

    // A ratio of two calls, not one call against a value, so it is no table row.
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
