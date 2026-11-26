/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/internal/helpers.hpp"
#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <limits>
#include <optional>
#include <string>
#include <vector>

using tcalc::Collection;
using tcalc::CollectionItem;
using K = tcalc::CollectionKind;

namespace {
Collection list(std::vector<CollectionItem> items) {
    return Collection{K::List, std::move(items)};
}

/// Generic test-row template: id label, input value, expected value.
template <typename InputT, typename ExpectedT> struct Case {
    const char *id;
    InputT input;
    ExpectedT expected;
};

using NtFn = CollectionItem (Calculator::*)(const Collection &) const;

/// The list, then the expected item. A null tol asserts exact equality; a tol is relative.
struct NtCase {
    const char *id;
    NtFn fn;
    std::vector<CollectionItem> input;
    CollectionItem expected;
    const char *tol = nullptr;
};

/// exact_int_log's argument shape: value then base.
struct LogArg {
    long long value;
    long long base;
};
/// Case row for exact_int_log: the k with base^k == value, or nullopt.
using ExactLogCase = Case<LogArg, std::optional<long long>>;

/// exact_rational_log's argument shape: value then base, both Rational.
struct RatLogArg {
    Rational value;
    Rational base;
};
/// Case row for exact_rational_log: the same question over a fraction.
using ExactRatLogCase = Case<RatLogArg, std::optional<long long>>;

} // namespace

void unit_number_theory(TestContext &ctx) {
    const Calculator c;

    TEST_CASE(ctx, "gcd :: list fold", {
        EXPECT_EQ(
            ctx, std::get<std::int64_t>(c.gcd(list({std::int64_t{12}, std::int64_t{8}}))), 4LL);
        EXPECT_EQ(
            ctx,
            std::get<std::int64_t>(
                c.gcd(list({std::int64_t{12}, std::int64_t{8}, std::int64_t{6}}))),
            2LL);
    });
    TEST_CASE(ctx, "gcd :: single element", {
        EXPECT_EQ(ctx, std::get<std::int64_t>(c.gcd(list({std::int64_t{42}}))), 42LL);
    });
    TEST_CASE(ctx, "gcd :: int-like double accepted", {
        EXPECT_EQ(ctx, std::get<std::int64_t>(c.gcd(list({4.0, 6.0}))), 2LL);
    });
    TEST_CASE(ctx, "gcd :: non-integer rejected", { EXPECT_THROWS(ctx, c.gcd(list({1.5, 2.0}))); });
    // gcd and lcm of every whole operand (#247): an Int64 when the result fits, else a BigReal.
    // A null tol asserts exact equality. A tol is relative, for a result past what BigReal holds
    // exactly: the default owes it double's precision, every digit is the multiprecision mode's
    // (#275).
    const auto lo = std::numeric_limits<std::int64_t>::min();
    const auto hi = std::numeric_limits<std::int64_t>::max();
    const std::vector<NtCase> nt_cases = {
        {.id = "gcd :: a double past 2^63",
         .fn = &Calculator::gcd,
         .input = {1e19, 10.0},
         .expected = std::int64_t{10}},
        {.id = "gcd :: a double past 2^53 read as its value",
         .fn = &Calculator::gcd,
         .input = {1234567890123456768.0, 100.0},
         .expected = std::int64_t{4}},
        {.id = "gcd :: a BigReal past int64",
         .fn = &Calculator::gcd,
         .input = {BigReal("10000000000000000002"), BigReal("3")},
         .expected = std::int64_t{3}},
        {.id = "lcm :: a BigReal result",
         .fn = &Calculator::lcm,
         .input = {BigReal("1e19"), BigReal("3")},
         .expected = BigReal("3e19")},
        {.id = "lcm :: a step past int512 from three operands",
         .fn = &Calculator::lcm,
         .input = {BigReal("1e70") + 1, BigReal("1e70") + 3, BigReal("1e70") + 7},
         .expected = BigReal(
             "1000000000000000000000000000000000000000000000000000000000000000000001100000000000000"
             "0000000000000000000000000000000000000000000000000000003100000000000000000000000000000"
             "00000000000000000000000000000000000000021"),
         .tol = "1e-15"},
        {.id = "lcm :: a step past int512 folded again",
         .fn = &Calculator::lcm,
         .input =
             {BigReal("1e70") + 1, BigReal("1e70") + 3, BigReal("1e70") + 7, BigReal("1e70") + 1},
         .expected = BigReal(
             "1000000000000000000000000000000000000000000000000000000000000000000001100000000000000"
             "0000000000000000000000000000000000000000000000000000003100000000000000000000000000000"
             "00000000000000000000000000000000000000021"),
         .tol = "1e-15"},
        {.id = "gcd :: a single BigReal",
         .fn = &Calculator::gcd,
         .input = {BigReal("1e19")},
         .expected = BigReal("1e19")},
        {.id = "gcd :: a single negative BigReal",
         .fn = &Calculator::gcd,
         .input = {BigReal("-1e19")},
         .expected = BigReal("1e19")},
        {.id = "gcd :: a negative zero beside a large double",
         .fn = &Calculator::gcd,
         .input = {-0.0, 1e19},
         .expected = BigReal("1e19")},
        {.id = "lcm :: a zero BigReal",
         .fn = &Calculator::lcm,
         .input = {BigReal("0"), BigReal("1e19")},
         .expected = std::int64_t{0}},
        {.id = "gcd :: INT64_MIN alone",
         .fn = &Calculator::gcd,
         .input = {lo},
         .expected = BigReal("9223372036854775808")},
        {.id = "gcd :: INT64_MIN with 2",
         .fn = &Calculator::gcd,
         .input = {lo, std::int64_t{2}},
         .expected = std::int64_t{2}},
        {.id = "lcm :: INT64_MIN with 1",
         .fn = &Calculator::lcm,
         .input = {lo, std::int64_t{1}},
         .expected = BigReal("9223372036854775808")},
        {.id = "gcd :: INT64_MIN with 0",
         .fn = &Calculator::gcd,
         .input = {lo, std::int64_t{0}},
         .expected = BigReal("9223372036854775808")},
        {.id = "lcm :: INT64_MIN with 0",
         .fn = &Calculator::lcm,
         .input = {lo, std::int64_t{0}},
         .expected = std::int64_t{0}},
        {.id = "lcm :: int64 operands past uint64",
         .fn = &Calculator::lcm,
         .input = {std::int64_t{1000000000000}, std::int64_t{1000000000001}},
         .expected = BigReal("1000000000001000000000000")},
        {.id = "lcm :: past INT64_MAX inside uint64",
         .fn = &Calculator::lcm,
         .input = {hi, std::int64_t{2}},
         .expected = BigReal("18446744073709551614")},
        {.id = "lcm :: hand-over mid fold",
         .fn = &Calculator::lcm,
         .input =
             {2LL,
              3LL,
              5LL,
              7LL,
              11LL,
              13LL,
              17LL,
              19LL,
              23LL,
              29LL,
              31LL,
              37LL,
              41LL,
              43LL,
              47LL,
              53LL},
         .expected = BigReal("32589158477190044730")},
        {.id = "gcd :: a single negative",
         .fn = &Calculator::gcd,
         .input = {std::int64_t{-5}},
         .expected = std::int64_t{5}},
        {.id = "lcm :: a single negative",
         .fn = &Calculator::lcm,
         .input = {std::int64_t{-5}},
         .expected = std::int64_t{5}},
        {.id = "lcm :: the largest that fits",
         .fn = &Calculator::lcm,
         .input = {std::int64_t{3037000500}, std::int64_t{3037000499}},
         .expected = std::int64_t{9223372033963249500}},
    };
    for (const auto &tc : nt_cases) {
        test_detail::with_case(ctx, tc.id, [&] {
            const CollectionItem got = (c.*tc.fn)(list(tc.input));
            EXPECT_EQ(ctx, got.index(), tc.expected.index());
            if (const auto *want = std::get_if<std::int64_t>(&tc.expected)) {
                EXPECT_EQ(ctx, std::get<std::int64_t>(got), *want);
            } else if (tc.tol == nullptr) {
                EXPECT_TRUE(ctx, std::get<BigReal>(got) == std::get<BigReal>(tc.expected));
            } else {
                const BigReal &want_big = std::get<BigReal>(tc.expected);
                EXPECT_TRUE(
                    ctx,
                    approx_big(std::get<BigReal>(got), want_big, abs(want_big) * BigReal(tc.tol)));
            }
        });
    }
    // floor calls an infinity whole; its text "inf" would reach std::stoll and throw no
    // CalculatorError. The smoke list [dbl inf, big 1e400] reaches it.
    TEST_CASE(ctx, "gcd :: a BigReal infinity rejected", {
        EXPECT_THROWS(
            ctx, c.gcd(list({BigReal(std::numeric_limits<double>::infinity()), BigReal("1e400")})));
    });
    // int_like(inf) is false, so a double infinity never reaches to_big.
    TEST_CASE(ctx, "gcd :: a double infinity rejected", {
        EXPECT_THROWS(ctx, c.gcd(list({std::numeric_limits<double>::infinity(), 3.0})));
    });
    // From 72 digits a BigReal may have been rounded, and a rounded integer cannot be told
    // from an exact one: 2^{265} reaches gcd with its last 8 digits lost.
    TEST_CASE(ctx, "gcd/lcm :: a BigReal past 72 digits rejected", {
        const BigReal a79 = BigReal("1e79") + 1;
        EXPECT_THROWS(ctx, c.gcd(list({a79, BigReal("3")})));
        EXPECT_THROWS(ctx, c.gcd(list({BigReal("1e400000"), BigReal("1e399999")})));
        EXPECT_THROWS(ctx, c.lcm(list({a79, BigReal("1e79") + 3})));
        EXPECT_THROWS(ctx, c.gcd(list({BigReal("1e72"), BigReal("3")})));
    });
    TEST_CASE(ctx, "gcd :: a BigReal just under 72 digits accepted", {
        EXPECT_EQ(
            ctx, std::get<std::int64_t>(c.gcd(list({BigReal("1e72") - 1, BigReal("3")}))), 3LL);
    });
    // Past 50 digits the snap would make it whole; the exact whole does not.
    TEST_CASE(ctx, "gcd :: a BigReal fraction past 50 digits rejected", {
        EXPECT_THROWS(
            ctx,
            c.gcd(list(
                {BigReal("1000000000000000000000000000000000000000000000000000000000000.5"),
                 BigReal("3")})));
    });
    // The value 3^{40}/3^{39} gives; the snap would read it as 3.
    TEST_CASE(ctx, "gcd :: a BigReal just under an integer rejected", {
        EXPECT_THROWS(
            ctx,
            c.gcd(list(
                {BigReal(
                     "2.999999999999999999999999999999999999999999999999999999999999999999998944"),
                 BigReal("6")})));
    });
    TEST_CASE(ctx, "gcd :: INT64_MIN + 1 accepted", {
        const auto lo = std::numeric_limits<std::int64_t>::min() + 1;
        EXPECT_EQ(ctx, std::get<std::int64_t>(c.gcd(list({lo, std::int64_t{1}}))), 1LL);
    });
    TEST_CASE(ctx, "gcd :: empty rejected", { EXPECT_THROWS(ctx, c.gcd(list({}))); });
    TEST_CASE(ctx, "lcm :: list fold", {
        EXPECT_EQ(ctx, std::get<std::int64_t>(c.lcm(list({4LL, 6LL}))), 12LL);
        EXPECT_EQ(ctx, std::get<std::int64_t>(c.lcm(list({2LL, 3LL, 4LL}))), 12LL);
    });
    TEST_CASE(ctx, "lcm :: non-integer rejected", { EXPECT_THROWS(ctx, c.lcm(list({1.5, 2.0}))); });
    TEST_CASE(ctx, "lcm :: empty rejected", { EXPECT_THROWS(ctx, c.lcm(list({}))); });
    TEST_CASE(ctx, "gcd/lcm :: point rejected", {
        EXPECT_THROWS(ctx, c.gcd(Collection{K::Point, {std::int64_t{12}, std::int64_t{8}}}));
        EXPECT_THROWS(ctx, c.lcm(Collection{K::Point, {std::int64_t{12}, std::int64_t{8}}}));
    });
    TEST_CASE(ctx, "gcd :: zero and negative", {
        EXPECT_EQ(
            ctx, std::get<std::int64_t>(c.gcd(list({std::int64_t{0}, std::int64_t{0}}))), 0LL);
        EXPECT_EQ(
            ctx, std::get<std::int64_t>(c.gcd(list({std::int64_t{0}, std::int64_t{5}}))), 5LL);
        EXPECT_EQ(
            ctx, std::get<std::int64_t>(c.gcd(list({std::int64_t{-12}, std::int64_t{8}}))), 4LL);
    });
    TEST_CASE(ctx, "lcm :: zero", {
        EXPECT_EQ(
            ctx, std::get<std::int64_t>(c.lcm(list({std::int64_t{0}, std::int64_t{5}}))), 0LL);
    });

    // calc_detail::exact_int_log: the k with base^k == value, or nullopt.
    // ln(x)/ln(b) gets 12 of the first 56 exact powers wrong, log_3(243) among them. The
    // question is an integer one, so it is answered on integers.
    const std::vector<ExactLogCase> exact_int_log_cases = {
        {.id = "log_2(8) is 3", .input = {8, 2}, .expected = 3},
        {.id = "log_3(243) is 5", .input = {243, 3}, .expected = 5},
        {.id = "log_10(1000) is 3", .input = {1000, 10}, .expected = 3},
        {.id = "log_2(1) is 0", .input = {1, 2}, .expected = 0},
        {.id = "log_2(10) has no integer answer", .input = {10, 2}, .expected = std::nullopt},
        // These two hang without the b <= 1 guard rather than answering wrongly.
        {.id = "base 1 has no answer", .input = {8, 1}, .expected = std::nullopt},
        {.id = "base 0 has no answer", .input = {8, 0}, .expected = std::nullopt},
        // These two need no guard. The rows are here to stop anyone adding one.
        {.id = "value 0 has no answer", .input = {0, 2}, .expected = std::nullopt},
        {.id = "a negative value has no answer", .input = {-8, 2}, .expected = std::nullopt},
    };
    for (const auto &tc : exact_int_log_cases) {
        test_detail::with_case(ctx, std::string("exact_int_log :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, calc_detail::exact_int_log(tc.input.value, tc.input.base), tc.expected);
        });
    }

    // calc_detail::exact_rational_log: the same question for a fraction. Numerator and
    // denominator are the same question and must agree on k; a negative k is the same
    // question with the base inverted.
    const std::vector<ExactRatLogCase> exact_rational_log_cases = {
        {.id = "log_2(1/8) is -3", .input = {Rational(1, 8), Rational(2)}, .expected = -3},
        {.id = "log_{1/2}(8) is -3", .input = {Rational(8), Rational(1, 2)}, .expected = -3},
        {.id = "log_{1/2}(1/8) is 3", .input = {Rational(1, 8), Rational(1, 2)}, .expected = 3},
        {.id = "log_{2/3}(4/9) is 2", .input = {Rational(4, 9), Rational(2, 3)}, .expected = 2},
        {.id = "log_{2/3}(1/2) has no answer",
         .input = {Rational(1, 2), Rational(2, 3)},
         .expected = std::nullopt},
        {.id = "log_{3/2}(9/4) is 2", .input = {Rational(9, 4), Rational(3, 2)}, .expected = 2},
        {.id = "log_{3/2}(4/9) is -2", .input = {Rational(4, 9), Rational(3, 2)}, .expected = -2},
    };
    for (const auto &tc : exact_rational_log_cases) {
        test_detail::with_case(ctx, std::string("exact_rational_log :: ") + tc.id, [&] {
            EXPECT_EQ(
                ctx, calc_detail::exact_rational_log(tc.input.value, tc.input.base), tc.expected);
        });
    }
}
