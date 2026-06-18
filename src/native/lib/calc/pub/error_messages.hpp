/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <string>
#include <string_view>

// Single source for call-function + collection error messages.
// TODO: extend to ALL error messages across the engine.
namespace tcalc::errmsg {

inline std::string integers_only(std::string_view fn) {
    return std::string(fn) + " is only defined for integers";
}

inline std::string empty_collection(std::string_view fn) {
    return std::string(fn) + " of an empty collection";
}

inline std::string not_for_point(std::string_view fn) {
    return std::string(fn) + " is not defined for a point";
}

} // namespace tcalc::errmsg
