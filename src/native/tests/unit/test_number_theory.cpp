/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/internal/helpers.hpp"
#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

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
