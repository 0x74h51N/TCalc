/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <vector>

using tcalc::Collection;
using tcalc::CollectionItem;
using K = tcalc::CollectionKind;

namespace {
Collection list(std::vector<CollectionItem> items) {
    return Collection{K::List, std::move(items)};
}
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
}
