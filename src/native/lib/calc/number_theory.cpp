/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"
#include "calc/pub/error_messages.hpp"

#include <cmath>
#include <limits>
#include <numeric>

using tcalc::CollectionKind;

namespace {

/// 2^63, the first whole double past int64; a double holds it exactly.
constexpr double kInt64End = 0x1p63;

/// std::gcd and std::lcm take the absolute value, which INT64_MIN has none of in int64.
std::int64_t to_integer(const CollectionItem &it, const char *name) {
    if (std::holds_alternative<std::int64_t>(it)) {
        const std::int64_t v = std::get<std::int64_t>(it);
        if (v == std::numeric_limits<std::int64_t>::min())
            calc_detail::math_error();
        return v;
    }
    if (std::holds_alternative<double>(it)) {
        const double d = std::get<double>(it);
        if (calc_detail::int_like(d)) {
            if (std::fabs(d) >= kInt64End)
                calc_detail::math_error();
            return static_cast<std::int64_t>(std::llround(d));
        }
    }
    throw CalculatorError(tcalc::errmsg::integers_only(name).c_str());
}

template <typename F> CollectionItem fold_integers(const Collection &a, const char *name, F op) {
    if (a.kind == CollectionKind::Point)
        throw CalculatorError(tcalc::errmsg::not_for_point(name).c_str());
    if (a.items().empty())
        throw CalculatorError(tcalc::errmsg::empty_collection(name).c_str());
    std::int64_t acc = to_integer(a.items()[0], name);
    for (std::size_t i = 1; i < a.items().size(); ++i)
        acc = op(acc, to_integer(a.items()[i], name));
    return CollectionItem{acc};
}

} // namespace

CollectionItem Calculator::gcd(const Collection &a) const {
    return fold_integers(a, "gcd", [](std::int64_t x, std::int64_t y) { return std::gcd(x, y); });
}

CollectionItem Calculator::lcm(const Collection &a) const {
    return fold_integers(a, "lcm", [](std::int64_t x, std::int64_t y) { return std::lcm(x, y); });
}
