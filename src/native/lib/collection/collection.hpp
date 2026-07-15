/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <complex>
#include <cstdint>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

#include "types.hpp"

namespace tcalc {

struct Collection;

using CollectionItem = std::
    variant<std::int64_t, double, BigReal, Complex, BigComplex, std::shared_ptr<const Collection>>;

enum class CollectionKind : std::uint8_t { List, Point };

struct Collection {
    CollectionKind kind;
    // Shared and immutable, so copying a Collection (and a Value that holds one) is a
    // refcount bump, not a deep copy of every item. Nothing mutates a collection after
    // construction, so the sharing is invisible.
    std::shared_ptr<const std::vector<CollectionItem>> items_;

    Collection(CollectionKind k, std::vector<CollectionItem> its);

    [[nodiscard]] const std::vector<CollectionItem> &items() const { return *items_; }

    bool operator==(const Collection &other) const;
};

enum class ScalarArm : std::uint8_t {
    I64,
    Double,
    BigReal,
    Complex,
    BigComplex,
};

ScalarArm compute_target_arm(std::span<const CollectionItem> items);
void promote_item(CollectionItem &it, ScalarArm target);

} // namespace tcalc
