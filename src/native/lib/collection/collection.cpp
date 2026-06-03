/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "collection/collection.hpp"

#include <algorithm>
#include <type_traits>

#include <boost/multiprecision/cpp_bin_float.hpp>

namespace tcalc {

ScalarArm compute_target_arm(std::span<const CollectionItem> items) {
    bool has_double = false;
    bool has_bigreal = false;
    bool has_complex = false;
    bool has_bigcomplex = false;
    for (const auto &it : items) {
        std::visit(
            [&](const auto &v) {
                using T = std::decay_t<decltype(v)>;
                if constexpr (std::is_same_v<T, double>)
                    has_double = true;
                else if constexpr (std::is_same_v<T, BigReal>)
                    has_bigreal = true;
                else if constexpr (std::is_same_v<T, std::complex<double>>)
                    has_complex = true;
                else if constexpr (std::is_same_v<T, BigComplex>)
                    has_bigcomplex = true;
            },
            it);
    }
    if (has_bigcomplex)
        return ScalarArm::BigComplex;
    if (has_complex)
        return ScalarArm::Complex;
    if (has_bigreal)
        return ScalarArm::BigReal;
    if (has_double)
        return ScalarArm::Double;
    return ScalarArm::I64;
}

namespace {

bool is_collection_item(const CollectionItem &it) {
    return std::holds_alternative<std::shared_ptr<const Collection>>(it);
}

const Collection &as_collection(const CollectionItem &it) {
    return *std::get<std::shared_ptr<const Collection>>(it);
}

using BF = boost::multiprecision::cpp_bin_float_50;

BF bigreal_to_bf(const BigReal &r) {
    return BF(r.str());
}

double i64_to_double(std::int64_t n) {
    return static_cast<double>(n);
}

BigReal i64_to_bigreal(std::int64_t n) {
    return BigReal(n);
}

std::complex<double> i64_to_complex(std::int64_t n) {
    return std::complex<double>(static_cast<double>(n), 0.0);
}

BigComplex i64_to_bigcomplex(std::int64_t n) {
    return BigComplex(BF(n), BF(0));
}

BigReal double_to_bigreal(double d) {
    return BigReal(d);
}

std::complex<double> double_to_complex(double d) {
    return std::complex<double>(d, 0.0);
}

BigComplex double_to_bigcomplex(double d) {
    return BigComplex(BF(d), BF(0));
}

std::complex<double> bigreal_to_complex(const BigReal &r) {
    return std::complex<double>(static_cast<double>(r), 0.0);
}

BigComplex bigreal_to_bigcomplex(const BigReal &r) {
    return BigComplex(bigreal_to_bf(r), BF(0));
}

BigComplex complex_to_bigcomplex(const std::complex<double> &c) {
    return BigComplex(BF(c.real()), BF(c.imag()));
}

} // namespace

void promote_item(CollectionItem &it, ScalarArm target) {
    std::visit(
        [&](auto &v) {
            using T = std::decay_t<decltype(v)>;

            if constexpr (
                std::is_same_v<T, std::shared_ptr<const Collection>> ||
                std::is_same_v<T, BigComplex>) {
                // Collection arm: not a scalar, never promoted.
                // BigComplex: already widest scalar, every target is a no-op.
                return;
            } else if constexpr (std::is_same_v<T, std::int64_t>) {
                switch (target) {
                case ScalarArm::I64:
                    return;
                case ScalarArm::Double:
                    it = i64_to_double(v);
                    return;
                case ScalarArm::BigReal:
                    it = i64_to_bigreal(v);
                    return;
                case ScalarArm::Complex:
                    it = i64_to_complex(v);
                    return;
                case ScalarArm::BigComplex:
                    it = i64_to_bigcomplex(v);
                    return;
                }
            } else if constexpr (std::is_same_v<T, double>) {
                switch (target) {
                case ScalarArm::I64:
                case ScalarArm::Double:
                    return;
                case ScalarArm::BigReal:
                    it = double_to_bigreal(v);
                    return;
                case ScalarArm::Complex:
                    it = double_to_complex(v);
                    return;
                case ScalarArm::BigComplex:
                    it = double_to_bigcomplex(v);
                    return;
                }
            } else if constexpr (std::is_same_v<T, BigReal>) {
                switch (target) {
                case ScalarArm::I64:
                case ScalarArm::Double:
                case ScalarArm::BigReal:
                    return;
                case ScalarArm::Complex:
                    it = bigreal_to_complex(v);
                    return;
                case ScalarArm::BigComplex:
                    it = bigreal_to_bigcomplex(v);
                    return;
                }
            } else if constexpr (std::is_same_v<T, std::complex<double>>) {
                switch (target) {
                case ScalarArm::I64:
                case ScalarArm::Double:
                case ScalarArm::BigReal:
                case ScalarArm::Complex:
                    return;
                case ScalarArm::BigComplex:
                    it = complex_to_bigcomplex(v);
                    return;
                }
            }
        },
        it);
}

Collection::Collection(parser::CollectionKind k, std::vector<CollectionItem> its)
    : kind(k)
    , items(std::move(its)) {
    if (kind == parser::CollectionKind::Point) {
        if (items.empty()) {
            throw std::invalid_argument("empty Point not supported");
        }
        if (items.size() >= 4) {
            throw std::invalid_argument("Point arity > 3 not supported");
        }
        for (const auto &it : items) {
            if (is_collection_item(it)) {
                throw std::invalid_argument("Point cannot contain Collection items");
            }
        }
    } else {
        if (items.empty())
            return;

        const bool has_collection_item = std::any_of(
            items.begin(), items.end(), [](const auto &it) { return is_collection_item(it); });

        if (has_collection_item) {
            const bool all_collection_items = std::all_of(
                items.begin(), items.end(), [](const auto &it) { return is_collection_item(it); });

            if (!all_collection_items) {
                throw std::invalid_argument("List elements must all be scalars OR all be Points");
            }

            std::size_t first_arity = 0;
            bool first = true;
            for (const auto &it : items) {
                const auto &inner = as_collection(it);
                if (inner.kind != parser::CollectionKind::Point) {
                    throw std::invalid_argument("nested List not allowed");
                }
                if (first) {
                    first_arity = inner.items.size();
                    first = false;
                } else if (inner.items.size() != first_arity) {
                    throw std::invalid_argument("list-of-points must have uniform arity");
                }
            }
            return; // list-of-points: nested Collections already promoted
        }
    }

    // Promote scalar items to a uniform variant arm.
    if (!items.empty()) {
        const ScalarArm target = compute_target_arm(items);
        for (auto &it : items) {
            promote_item(it, target);
        }
    }
}

} // namespace tcalc
