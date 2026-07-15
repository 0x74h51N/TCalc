/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "collection/collection.hpp"
#include "internal/test_helpers.hpp"
#include "parser/pub/parser.hpp"
#include "types.hpp"

#include <memory>
#include <stdexcept>
#include <vector>

void unit_collection(TestContext &ctx) {
    using K = tcalc::CollectionKind;

    test_detail::with_case(ctx, "collection :: list of scalars constructs", [&] {
        tcalc::Collection c{K::List, {1.0, 2.0}};
        EXPECT_EQ(ctx, c.kind, K::List);
        EXPECT_EQ(ctx, c.items().size(), 2u);
    });

    test_detail::with_case(ctx, "collection :: empty list constructs", [&] {
        tcalc::Collection c{K::List, {}};
        EXPECT_EQ(ctx, c.items().size(), 0u);
    });

    test_detail::with_case(ctx, "collection :: point arity 2 constructs", [&] {
        tcalc::Collection c{K::Point, {1.0, 2.0}};
        EXPECT_EQ(ctx, c.kind, K::Point);
        EXPECT_EQ(ctx, c.items().size(), 2u);
    });

    test_detail::with_case(ctx, "collection :: point arity 3 constructs", [&] {
        tcalc::Collection c{K::Point, {1.0, 2.0, 3.0}};
        EXPECT_EQ(ctx, c.items().size(), 3u);
    });

    test_detail::with_case(ctx, "collection :: empty point throws", [&] {
        bool threw = false;
        try {
            tcalc::Collection c{K::Point, {}};
            (void)c;
        } catch (const std::invalid_argument &) {
            threw = true;
        }
        EXPECT_TRUE(ctx, threw);
    });

    test_detail::with_case(ctx, "collection :: point arity 4 throws", [&] {
        bool threw = false;
        try {
            tcalc::Collection c{K::Point, {1.0, 2.0, 3.0, 4.0}};
            (void)c;
        } catch (const std::invalid_argument &) {
            threw = true;
        }
        EXPECT_TRUE(ctx, threw);
    });

    test_detail::with_case(ctx, "collection :: point with collection item throws", [&] {
        auto inner = std::make_shared<tcalc::Collection>(
            K::Point, std::vector<tcalc::CollectionItem>{1.0, 2.0});
        bool threw = false;
        try {
            tcalc::Collection outer{K::Point, std::vector<tcalc::CollectionItem>{1.0, inner}};
            (void)outer;
        } catch (const std::invalid_argument &) {
            threw = true;
        }
        EXPECT_TRUE(ctx, threw);
    });

    test_detail::with_case(ctx, "collection :: nested list throws", [&] {
        auto inner = std::make_shared<tcalc::Collection>(
            K::List, std::vector<tcalc::CollectionItem>{1.0, 2.0});
        bool threw = false;
        try {
            tcalc::Collection outer{K::List, std::vector<tcalc::CollectionItem>{inner, inner}};
            (void)outer;
        } catch (const std::invalid_argument &) {
            threw = true;
        }
        EXPECT_TRUE(ctx, threw);
    });

    test_detail::with_case(ctx, "collection :: list mixed scalar and point throws", [&] {
        auto pt = std::make_shared<tcalc::Collection>(
            K::Point, std::vector<tcalc::CollectionItem>{1.0, 2.0});
        bool threw = false;
        try {
            tcalc::Collection outer{K::List, std::vector<tcalc::CollectionItem>{1.0, pt}};
            (void)outer;
        } catch (const std::invalid_argument &) {
            threw = true;
        }
        EXPECT_TRUE(ctx, threw);
    });

    test_detail::with_case(ctx, "collection :: list of points uniform arity ok", [&] {
        auto p1 = std::make_shared<tcalc::Collection>(
            K::Point, std::vector<tcalc::CollectionItem>{1.0, 2.0});
        auto p2 = std::make_shared<tcalc::Collection>(
            K::Point, std::vector<tcalc::CollectionItem>{3.0, 4.0});
        tcalc::Collection outer{K::List, std::vector<tcalc::CollectionItem>{p1, p2}};
        EXPECT_EQ(ctx, outer.items().size(), 2u);
    });

    test_detail::with_case(ctx, "collection :: list of points mixed arity throws", [&] {
        auto p2d = std::make_shared<tcalc::Collection>(
            K::Point, std::vector<tcalc::CollectionItem>{1.0, 2.0});
        auto p3d = std::make_shared<tcalc::Collection>(
            K::Point, std::vector<tcalc::CollectionItem>{3.0, 4.0, 5.0});
        bool threw = false;
        try {
            tcalc::Collection outer{K::List, std::vector<tcalc::CollectionItem>{p2d, p3d}};
            (void)outer;
        } catch (const std::invalid_argument &) {
            threw = true;
        }
        EXPECT_TRUE(ctx, threw);
    });

    test_detail::with_case(ctx, "collection :: equality same kind and items", [&] {
        tcalc::Collection a{K::List, {1.0, 2.0}};
        tcalc::Collection b{K::List, {1.0, 2.0}};
        EXPECT_EQ(ctx, a, b);
    });

    test_detail::with_case(ctx, "collection :: inequality across kind", [&] {
        tcalc::Collection a{K::List, {1.0, 2.0}};
        tcalc::Collection b{K::Point, {1.0, 2.0}};
        EXPECT_TRUE(ctx, !(a == b));
    });

    test_detail::with_case(ctx, "collection :: items uniform i64", [&] {
        tcalc::Collection c{K::List, {std::int64_t{1}, std::int64_t{2}}};
        EXPECT_EQ(ctx, c.items()[0].index(), 0u);
        EXPECT_EQ(ctx, c.items()[1].index(), 0u);
    });

    test_detail::with_case(ctx, "collection :: int promoted to double when mixed", [&] {
        tcalc::Collection c{K::List, {std::int64_t{1}, 2.5}};
        EXPECT_EQ(ctx, c.items()[0].index(), 1u);
        EXPECT_EQ(ctx, c.items()[1].index(), 1u);
    });

    test_detail::with_case(ctx, "collection :: int promoted to big_real when mixed", [&] {
        tcalc::Collection c{K::List, {std::int64_t{1}, BigReal("2.0")}};
        EXPECT_EQ(ctx, c.items()[0].index(), 2u);
        EXPECT_EQ(ctx, c.items()[1].index(), 2u);
    });
}
