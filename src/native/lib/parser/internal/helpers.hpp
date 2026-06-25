/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <array>
#include <cstddef>
#include <string_view>

namespace tcalc::parser {

// First-byte dispatch: which leading bytes can begin a token, so a matcher can
// skip its scan where nothing can match.
inline constexpr std::size_t kByteValueCount = 256; // one slot per byte value
using FirstByteTable = std::array<bool, kByteValueCount>;

// Mark the first byte of `token` in `table` (no-op when `token` is empty).
constexpr void mark_first_byte(FirstByteTable &table, std::string_view token) {
    if (!token.empty()) {
        table[static_cast<unsigned char>(token[0])] = true;
    }
}

// Id-indexed pointer lookup into `items` (each has `.id`); compile error on an
// out-of-range or duplicate id.
template <class Spec, std::size_t Count, class Range>
consteval std::array<const Spec *, Count> index_by_id(const Range &items) {
    std::array<const Spec *, Count> out{}; // value-init = nullptr
    for (const auto &item : items) {
        const std::size_t idx = static_cast<std::size_t>(item.id);
        if (idx >= Count) {
            throw "index_by_id: id out of range";
        }
        if (out[idx] != nullptr) {
            throw "index_by_id: duplicate id";
        }
        out[idx] = &item;
    }
    return out;
}

} // namespace tcalc::parser
