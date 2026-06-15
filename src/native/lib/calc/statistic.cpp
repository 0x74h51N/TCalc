/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <span>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

#include "calc/pub/errors.hpp"
#include "collection/collection.hpp"

using tcalc::CollectionKind;
using tcalc::compute_target_arm;
using tcalc::promote_item;
using tcalc::ScalarArm;

namespace {

constexpr double kPairMeanDivisor = 2.0;

// Neumaier (Kahan-Babuska-Neumaier) compensated sum: error ~2*eps, independent of
// element count and magnitude spread (recovers low bits lost to cancellation).
// double scalar; complex componentwise.
template <typename T> T neumaier_sum(std::span<const CollectionItem> items) {
    if constexpr (std::is_same_v<T, Complex>) {
        const Complex first = std::get<Complex>(items[0]);
        double sr = first.real();
        double si = first.imag();
        double cr = 0.0;
        double ci = 0.0;
        for (std::size_t i = 1; i < items.size(); ++i) {
            const Complex v = std::get<Complex>(items[i]);
            const double vr = v.real();
            const double tr = sr + vr;
            cr += (std::abs(sr) >= std::abs(vr)) ? (sr - tr) + vr : (vr - tr) + sr;
            sr = tr;
            const double vi = v.imag();
            const double ti = si + vi;
            ci += (std::abs(si) >= std::abs(vi)) ? (si - ti) + vi : (vi - ti) + si;
            si = ti;
        }
        return Complex(sr + cr, si + ci);
    } else {
        double sum = std::get<double>(items[0]);
        double c = 0.0;
        for (std::size_t i = 1; i < items.size(); ++i) {
            const double v = std::get<double>(items[i]);
            const double t = sum + v;
            c += (std::abs(sum) >= std::abs(v)) ? (sum - t) + v : (v - t) + sum;
            sum = t;
        }
        return sum + c;
    }
}

template <typename T> CollectionItem mean_pair(const T &a, const T &b) {
    if constexpr (std::is_same_v<T, std::int64_t>) {
        const __int128 sum = static_cast<__int128>(a) + static_cast<__int128>(b);
        return static_cast<double>(sum) / kPairMeanDivisor;
    } else {
        return (a + b) / T(2);
    }
}

// Per-column reduction over a List of Points: re-normalize each column's arm,
// then apply the scalar reducer. Shared by mean/min/max/median.
template <typename Reducer>
CollectionItem reduce_points(std::span<const CollectionItem> pts, const Reducer &reducer) {
    const auto &p0 = *std::get<std::shared_ptr<const Collection>>(pts[0]);
    const std::size_t k = p0.items.size();

    std::vector<CollectionItem> out;
    out.reserve(k);
    for (std::size_t j = 0; j < k; ++j) {
        std::vector<CollectionItem> column;
        column.reserve(pts.size());
        for (const auto &p : pts)
            column.push_back(std::get<std::shared_ptr<const Collection>>(p)->items[j]);

        const ScalarArm arm = compute_target_arm(column);
        for (auto &c : column)
            promote_item(c, arm);
        out.push_back(reducer(std::span<const CollectionItem>(column)));
    }
    return std::make_shared<const Collection>(CollectionKind::Point, std::move(out));
}

// Shared reduction driver: guards + structural dispatch, identical for every op.
// `arm` is a per-arm reducer (callable as arm.operator()<T>(span)); the only thing
// each op varies is its name (for errors) and which scalar reducer it passes.
template <typename ArmReducer>
CollectionItem reduce_collection(const Collection &a, const char *name, ArmReducer arm) {
    const auto &items = a.items;
    if (items.empty())
        throw CalculatorError((std::string(name) + " of an empty collection").c_str());
    if (a.kind == CollectionKind::Point)
        throw CalculatorError((std::string(name) + " is not defined for a single point").c_str());
    if (items.size() == 1)
        return items[0];

    const auto on_column = [&](std::span<const CollectionItem> col) {
        return std::visit(
            [&](const auto &first) -> CollectionItem {
                using T = std::decay_t<decltype(first)>;
                return arm.template operator()<T>(col);
            },
            col[0]);
    };

    if (std::holds_alternative<std::shared_ptr<const Collection>>(items[0]))
        return reduce_points(items, on_column);
    return on_column(items);
}

} // namespace

template <typename T>
CollectionItem Calculator::mean_scalar(std::span<const CollectionItem> items) const {
    const std::size_t n = items.size();

    if constexpr (std::is_same_v<T, std::shared_ptr<const Collection>>) {
        (void)n;
        throw CalculatorError("mean: unexpected nested collection arm");
    } else if constexpr (std::is_same_v<T, std::int64_t>) {
        __int128 sum = 0;
        for (const auto &it : items)
            sum += std::get<std::int64_t>(it);
        return static_cast<double>(sum) / static_cast<double>(n);
    } else if constexpr (std::is_same_v<T, double> || std::is_same_v<T, Complex>) {
        const T sum = neumaier_sum<T>(items);
        return sum / T(static_cast<double>(n));
    } else {
        T acc = std::get<T>(items[0]);
        for (std::size_t i = 1; i < n; ++i)
            acc += std::get<T>(items[i]);
        return acc / T(static_cast<long long>(n));
    }
}

template <typename T, bool IsMax>
CollectionItem Calculator::minmax_scalar(std::span<const CollectionItem> items) const {
    if constexpr (std::is_same_v<T, std::shared_ptr<const Collection>>) {
        throw CalculatorError("minmax: unexpected nested collection arm");
    } else if constexpr (std::is_same_v<T, Complex> || std::is_same_v<T, BigComplex>) {
        throw CalculatorError("min-max not defined for complex values");
    } else {
        T best = std::get<T>(items[0]);
        for (std::size_t i = 1; i < items.size(); ++i) {
            const T &v = std::get<T>(items[i]);
            if constexpr (IsMax) {
                if (best < v)
                    best = v;
            } else {
                if (v < best)
                    best = v;
            }
        }
        return best;
    }
}

template <typename T>
CollectionItem Calculator::median_scalar(std::span<const CollectionItem> items) const {
    if constexpr (std::is_same_v<T, std::shared_ptr<const Collection>>) {
        throw CalculatorError("median: unexpected nested collection arm");
    } else if constexpr (std::is_same_v<T, Complex> || std::is_same_v<T, BigComplex>) {
        throw CalculatorError("median is not defined for complex values");
    } else {
        std::vector<T> v;
        v.reserve(items.size());
        for (const auto &it : items)
            v.push_back(std::get<T>(it));
        const std::size_t m = v.size() / 2;
        std::nth_element(v.begin(), v.begin() + m, v.end());
        if (v.size() % 2)
            return CollectionItem{v[m]};
        std::nth_element(v.begin(), v.begin() + (m - 1), v.begin() + m);
        return mean_pair<T>(v[m - 1], v[m]);
    }
}

CollectionItem Calculator::mean(const Collection &a) const {
    return reduce_collection(a, "mean", [this]<typename T>(std::span<const CollectionItem> col) {
        return mean_scalar<T>(col);
    });
}

CollectionItem Calculator::min(const Collection &a) const {
    return reduce_collection(a, "min", [this]<typename T>(std::span<const CollectionItem> col) {
        return minmax_scalar<T, false>(col);
    });
}

CollectionItem Calculator::max(const Collection &a) const {
    return reduce_collection(a, "max", [this]<typename T>(std::span<const CollectionItem> col) {
        return minmax_scalar<T, true>(col);
    });
}

CollectionItem Calculator::median(const Collection &a) const {
    return reduce_collection(a, "median", [this]<typename T>(std::span<const CollectionItem> col) {
        return median_scalar<T>(col);
    });
}
