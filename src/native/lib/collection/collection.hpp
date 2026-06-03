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

#include "parser/pub/parser.hpp"
#include "types.hpp"

namespace tcalc {

struct Collection;

using CollectionItem = std::variant<
    std::int64_t,
    double,
    BigReal,
    std::complex<double>,
    BigComplex,
    std::shared_ptr<const Collection>>;

struct Collection {
    parser::CollectionKind kind;
    std::vector<CollectionItem> items;

    Collection(parser::CollectionKind k, std::vector<CollectionItem> its);

    bool operator==(const Collection &) const = default;
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
