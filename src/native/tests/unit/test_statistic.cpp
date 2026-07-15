/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/pub/errors.hpp"
#include "collection/collection.hpp"
#include "internal/test_helpers.hpp"
#include "types.hpp"

#include <cstdint>
#include <memory>
#include <vector>

namespace {

using tcalc::Collection;
using tcalc::CollectionItem;
using K = tcalc::CollectionKind;

Collection list(std::vector<CollectionItem> items) {
    return Collection{K::List, std::move(items)};
}

std::shared_ptr<const Collection> point(std::vector<CollectionItem> items) {
    return std::make_shared<const Collection>(K::Point, std::move(items));
}

} // namespace

void unit_statistic(TestContext &ctx) {
    const Calculator calc;

    // ---- mean ----------------------------------------------------------
    test_detail::with_case(ctx, "mean :: int list -> double 2.5", [&] {
        const auto r =
            calc.mean(list({std::int64_t{1}, std::int64_t{2}, std::int64_t{3}, std::int64_t{4}}));
        EXPECT_EQ(ctx, r.index(), 1u);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 2.5));
    });

    test_detail::with_case(ctx, "mean :: int list -> double 2.0", [&] {
        const auto r = calc.mean(list({std::int64_t{1}, std::int64_t{2}, std::int64_t{3}}));
        EXPECT_EQ(ctx, r.index(), 1u);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 2.0));
    });

    test_detail::with_case(ctx, "mean :: double list -> double", [&] {
        const auto r = calc.mean(list({1.5, 2.5}));
        EXPECT_EQ(ctx, r.index(), 1u);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 2.0));
    });

    test_detail::with_case(ctx, "mean :: bigreal list -> bigreal", [&] {
        const auto r = calc.mean(list({BigReal("1.0"), BigReal("2.0"), BigReal("3.0")}));
        EXPECT_EQ(ctx, r.index(), 2u);
        EXPECT_TRUE(ctx, approx_big(std::get<BigReal>(r), BigReal("2.0")));
    });

    test_detail::with_case(ctx, "mean :: complex list -> complex", [&] {
        const auto r = calc.mean(list({Complex(1.0, 2.0), Complex(3.0, 4.0)}));
        EXPECT_EQ(ctx, r.index(), 3u);
        const auto c = std::get<Complex>(r);
        EXPECT_TRUE(ctx, approx(c.real(), 2.0));
        EXPECT_TRUE(ctx, approx(c.imag(), 3.0));
    });

    test_detail::with_case(ctx, "mean :: centroid of points", [&] {
        const auto r = calc.mean(list(
            {point({std::int64_t{0}, std::int64_t{0}}),
             point({std::int64_t{2}, std::int64_t{4}})}));
        EXPECT_EQ(ctx, r.index(), 5u);
        const auto &p = *std::get<std::shared_ptr<const Collection>>(r);
        EXPECT_EQ(ctx, p.kind, K::Point);
        EXPECT_EQ(ctx, p.items().size(), 2u);
        EXPECT_TRUE(ctx, approx(std::get<double>(p.items()[0]), 1.0));
        EXPECT_TRUE(ctx, approx(std::get<double>(p.items()[1]), 2.0));
    });

    test_detail::with_case(ctx, "mean :: int64 sum overflow guard", [&] {
        // Three near-max int64 values: their sum overflows int64 but fits __int128.
        const std::int64_t big = (std::int64_t{1} << 62);
        const auto r = calc.mean(list({big, big, big}));
        EXPECT_EQ(ctx, r.index(), 1u);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), static_cast<double>(big), 1.0));
    });

    test_detail::with_case(ctx, "mean :: pairwise accuracy", [&] {
        std::vector<CollectionItem> items;
        const std::size_t n = 1u << 20; // ~1M
        items.reserve(n + 1);
        items.push_back(1e8);
        for (std::size_t i = 0; i < n; ++i)
            items.push_back(1.0);
        const double exact = (1e8 + static_cast<double>(n)) / static_cast<double>(n + 1);
        const auto r = calc.mean(list(std::move(items)));
        EXPECT_TRUE(ctx, approx(std::get<double>(r), exact, exact * 1e-9));
    });

    test_detail::with_case(ctx, "mean :: cancellation (double)", [&] {
        // Exact sum is 1.0; naive/pairwise running-add loses it and returns 0.0.
        // mean = 1.0 / 3.
        const auto r = calc.mean(list({1e16, 1.0, -1e16}));
        EXPECT_EQ(ctx, r.index(), 1u);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 1.0 / 3.0, 1e-6));
    });

    test_detail::with_case(ctx, "mean :: cancellation (complex)", [&] {
        // Componentwise exact sum (1.0, 1.0); naive loses both. mean = (1/3, 1/3).
        const auto r =
            calc.mean(list({Complex(1e16, -1e16), Complex(1.0, 1.0), Complex(-1e16, 1e16)}));
        EXPECT_EQ(ctx, r.index(), 3u);
        const auto c = std::get<Complex>(r);
        EXPECT_TRUE(ctx, approx(c.real(), 1.0 / 3.0, 1e-6));
        EXPECT_TRUE(ctx, approx(c.imag(), 1.0 / 3.0, 1e-6));
    });

    // ---- sum ----------------------------------------------------------
    test_detail::with_case(ctx, "sum :: int list -> int64", [&] {
        const auto r = calc.sum(list({std::int64_t{1}, std::int64_t{2}, std::int64_t{3}}));
        EXPECT_EQ(ctx, r.index(), 0u);
        EXPECT_EQ(ctx, std::get<std::int64_t>(r), std::int64_t{6});
    });

    test_detail::with_case(ctx, "sum :: double list (neumaier cancellation)", [&] {
        const auto r = calc.sum(list({1e16, 1.0, -1e16}));
        EXPECT_EQ(ctx, r.index(), 1u);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 1.0, 1e-6));
    });

    test_detail::with_case(ctx, "sum :: single element returns it", [&] {
        const auto r = calc.sum(list({std::int64_t{7}}));
        EXPECT_EQ(ctx, std::get<std::int64_t>(r), std::int64_t{7});
    });

    test_detail::with_case(ctx, "sum :: per-column of points", [&] {
        const auto r = calc.sum(list(
            {point({std::int64_t{1}, std::int64_t{2}}),
             point({std::int64_t{3}, std::int64_t{4}})}));
        EXPECT_EQ(ctx, r.index(), 5u);
        const auto &p = *std::get<std::shared_ptr<const Collection>>(r);
        EXPECT_EQ(ctx, std::get<std::int64_t>(p.items()[0]), std::int64_t{4});
        EXPECT_EQ(ctx, std::get<std::int64_t>(p.items()[1]), std::int64_t{6});
    });

    // ---- variance / stddev --------------------------------------------
    test_detail::with_case(ctx, "varp :: population variance", [&] {
        const auto r = calc.variance_pop(list({2.0, 4.0, 6.0})); // mean 4, ss 8, /3
        EXPECT_EQ(ctx, r.index(), 1u);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 8.0 / 3.0, 1e-9));
    });

    test_detail::with_case(ctx, "var :: sample variance", [&] {
        const auto r = calc.variance(list({2.0, 4.0, 6.0})); // ss 8, /2
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 4.0, 1e-9));
    });

    test_detail::with_case(ctx, "stdp :: population stddev", [&] {
        const auto r = calc.stddev_pop(list({2.0, 4.0, 6.0}));
        EXPECT_TRUE(ctx, approx(std::get<double>(r), std::sqrt(8.0 / 3.0), 1e-9));
    });

    test_detail::with_case(ctx, "std :: sample stddev", [&] {
        const auto r = calc.stddev(list({2.0, 4.0, 6.0}));
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 2.0, 1e-9));
    });

    test_detail::with_case(ctx, "varp :: single element is zero", [&] {
        const auto r = calc.variance_pop(list({std::int64_t{5}}));
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 0.0, 1e-12));
    });

    test_detail::with_case(ctx, "var :: single element throws", [&] {
        EXPECT_THROWS(ctx, calc.variance(list({std::int64_t{5}})));
    });

    test_detail::with_case(ctx, "var :: complex rejected", [&] {
        EXPECT_THROWS(ctx, calc.variance(list({Complex(1.0, 2.0), Complex(3.0, 4.0)})));
    });

    test_detail::with_case(ctx, "varp :: per-column of points", [&] {
        const auto r = calc.variance_pop(list(
            {point({std::int64_t{0}, std::int64_t{0}}),
             point({std::int64_t{2}, std::int64_t{0}})})); // col0 mean1 ss2 /2=1; col1 all0=0
        EXPECT_EQ(ctx, r.index(), 5u);
        const auto &p = *std::get<std::shared_ptr<const Collection>>(r);
        EXPECT_TRUE(ctx, approx(std::get<double>(p.items()[0]), 1.0, 1e-9));
        EXPECT_TRUE(ctx, approx(std::get<double>(p.items()[1]), 0.0, 1e-12));
    });

    // ---- min / max -----------------------------------------------------
    test_detail::with_case(ctx, "min :: int list keeps arm", [&] {
        const auto r = calc.min(list({std::int64_t{3}, std::int64_t{1}, std::int64_t{2}}));
        EXPECT_EQ(ctx, r.index(), 0u);
        EXPECT_EQ(ctx, std::get<std::int64_t>(r), std::int64_t{1});
    });

    test_detail::with_case(ctx, "max :: int list keeps arm", [&] {
        const auto r = calc.max(list({std::int64_t{3}, std::int64_t{1}, std::int64_t{2}}));
        EXPECT_EQ(ctx, r.index(), 0u);
        EXPECT_EQ(ctx, std::get<std::int64_t>(r), std::int64_t{3});
    });

    test_detail::with_case(ctx, "min :: double list", [&] {
        const auto r = calc.min(list({1.5, 0.5, 2.5}));
        EXPECT_EQ(ctx, r.index(), 1u);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 0.5));
    });

    test_detail::with_case(ctx, "min/max :: bigreal list", [&] {
        const auto lo = calc.min(list({BigReal("3.0"), BigReal("1.0"), BigReal("2.0")}));
        const auto hi = calc.max(list({BigReal("3.0"), BigReal("1.0"), BigReal("2.0")}));
        EXPECT_EQ(ctx, lo.index(), 2u);
        EXPECT_EQ(ctx, hi.index(), 2u);
        EXPECT_TRUE(ctx, approx_big(std::get<BigReal>(lo), BigReal("1.0")));
        EXPECT_TRUE(ctx, approx_big(std::get<BigReal>(hi), BigReal("3.0")));
    });

    test_detail::with_case(ctx, "min/max :: bounding box of points", [&] {
        const auto lo = calc.min(list(
            {point({std::int64_t{1}, std::int64_t{4}}),
             point({std::int64_t{3}, std::int64_t{2}})}));
        const auto hi = calc.max(list(
            {point({std::int64_t{1}, std::int64_t{4}}),
             point({std::int64_t{3}, std::int64_t{2}})}));
        const auto &plo = *std::get<std::shared_ptr<const Collection>>(lo);
        const auto &phi = *std::get<std::shared_ptr<const Collection>>(hi);
        EXPECT_EQ(ctx, std::get<std::int64_t>(plo.items()[0]), std::int64_t{1});
        EXPECT_EQ(ctx, std::get<std::int64_t>(plo.items()[1]), std::int64_t{2});
        EXPECT_EQ(ctx, std::get<std::int64_t>(phi.items()[0]), std::int64_t{3});
        EXPECT_EQ(ctx, std::get<std::int64_t>(phi.items()[1]), std::int64_t{4});
    });

    test_detail::with_case(ctx, "min/max :: complex throws", [&] {
        EXPECT_THROWS(ctx, calc.min(list({Complex(1.0, 2.0), Complex(3.0, 4.0)})));
        EXPECT_THROWS(ctx, calc.max(list({Complex(1.0, 2.0), Complex(3.0, 4.0)})));
    });

    // ---- median --------------------------------------------------------
    test_detail::with_case(ctx, "median :: odd -> int arm", [&] {
        const auto r = calc.median(list({std::int64_t{1}, std::int64_t{2}, std::int64_t{3}}));
        EXPECT_EQ(ctx, r.index(), 0u);
        EXPECT_EQ(ctx, std::get<std::int64_t>(r), std::int64_t{2});
    });

    test_detail::with_case(ctx, "median :: even -> double", [&] {
        const auto r =
            calc.median(list({std::int64_t{1}, std::int64_t{2}, std::int64_t{3}, std::int64_t{4}}));
        EXPECT_EQ(ctx, r.index(), 1u);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 2.5));
    });

    test_detail::with_case(ctx, "median :: shuffled input", [&] {
        const auto r = calc.median(list(
            {std::int64_t{5}, std::int64_t{1}, std::int64_t{4}, std::int64_t{2}, std::int64_t{3}}));
        EXPECT_EQ(ctx, std::get<std::int64_t>(r), std::int64_t{3});
    });

    test_detail::with_case(ctx, "median :: complex throws", [&] {
        EXPECT_THROWS(ctx, calc.median(list({Complex(1.0, 2.0), Complex(3.0, 4.0)})));
    });

    // ---- shared dispatch ----------------------------------------------
    test_detail::with_case(ctx, "shared :: empty list throws", [&] {
        EXPECT_THROWS(ctx, calc.mean(list({})));
        EXPECT_THROWS(ctx, calc.min(list({})));
        EXPECT_THROWS(ctx, calc.max(list({})));
        EXPECT_THROWS(ctx, calc.median(list({})));
    });

    test_detail::with_case(ctx, "shared :: bare point throws", [&] {
        EXPECT_THROWS(ctx, calc.mean(Collection{K::Point, {1.0, 2.0}}));
        EXPECT_THROWS(ctx, calc.median(Collection{K::Point, {1.0, 2.0}}));
    });

    test_detail::with_case(ctx, "shared :: size 1 returns element", [&] {
        const auto r = calc.mean(list({std::int64_t{7}}));
        EXPECT_EQ(ctx, r.index(), 0u);
        EXPECT_EQ(ctx, std::get<std::int64_t>(r), std::int64_t{7});
        const auto m = calc.min(list({std::int64_t{7}}));
        EXPECT_EQ(ctx, std::get<std::int64_t>(m), std::int64_t{7});
    });
}
