/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

// native_probe boost: a Boost function called with TCalc bypassed, to tell a Boost result
// from TCalc's own. A finding that needs one adds its row to kBoostRows.

#include <array>
#include <optional>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <span>
#include <sstream>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

#include <boost/multiprecision/cpp_bin_float.hpp>
#include <boost/multiprecision/cpp_dec_float.hpp>

#include "frame.hpp"

namespace tcalc::probe {
namespace {

enum class BoostType : std::uint8_t { Double, LongDouble, Dec50, Bin100 };

struct TypeName {
    BoostType type;
    std::string_view name;
};

constexpr std::array kTypes{
    TypeName{BoostType::Double, "double"},
    TypeName{BoostType::LongDouble, "ldbl"},
    TypeName{BoostType::Dec50, "dec50"},
    TypeName{BoostType::Bin100, "bin"},
};

template <class T> T read_arg(const std::string &text) {
    std::optional<T> value;
    if constexpr (std::is_floating_point_v<T>) {
        value = whole<T>(text);
    } else {
        value = read_number<T>(text);
    }
    if (!value) {
        throw ProbeError("argument '" + text + "' is not a number");
    }
    return *value;
}

template <class T> std::string text_of(const T &value) {
    std::ostringstream out;
    out << std::setprecision(std::numeric_limits<T>::max_digits10) << value;
    return out.str();
}

/// Fn on args read as T; Fn is a generic lambda of one or two arguments.
template <class T, auto Fn> std::string call(std::span<const std::string> args) {
    using F = decltype(Fn);
    if constexpr (std::is_invocable_v<F, T>) {
        if (args.size() == 1) {
            return text_of(T(Fn(read_arg<T>(args[0]))));
        }
    }
    if constexpr (std::is_invocable_v<F, T, T>) {
        if (args.size() == 2) {
            return text_of(T(Fn(read_arg<T>(args[0]), read_arg<T>(args[1]))));
        }
    }
    throw ProbeError(
        "this row takes another count of arguments than " + std::to_string(args.size()));
}

template <auto Fn> std::string run(BoostType type, std::span<const std::string> args) {
    switch (type) {
    case BoostType::Double:
        return call<double, Fn>(args);
    case BoostType::LongDouble:
        return call<long double, Fn>(args);
    case BoostType::Dec50:
        return call<boost::multiprecision::cpp_dec_float_50, Fn>(args);
    case BoostType::Bin100:
        return call<boost::multiprecision::cpp_bin_float_100, Fn>(args);
    }
    throw ProbeError("a BoostType with no call");
}

struct BoostRow {
    std::string_view name;
    std::string (*run)(BoostType, std::span<const std::string>);
};

// A row, std:: named so ADL still finds Boost's overload:
// BoostRow{"fmod", run<[](const auto &x, const auto &y) { using std::fmod; return fmod(x, y); }>}
constexpr std::array<BoostRow, 0> kBoostRows{};

} // namespace

Row boost_row(std::span<const std::string> words) {
    constexpr std::size_t kNameAndType = 2;
    if (words.size() < kNameAndType) {
        throw ProbeError("boost needs NAME TYPE ARG...");
    }
    const auto *row = std::ranges::find(kBoostRows, words[0], &BoostRow::name);
    if (row == kBoostRows.end()) {
        throw ProbeError(
            "no Boost row '" + words[0] + "'; the rows are " +
            (kBoostRows.empty() ? "(none)" : names_of(kBoostRows, &BoostRow::name)) +
            "; add one to kBoostRows in src/native/tools/probe/boost_table.cpp");
    }
    const auto *type = std::ranges::find(kTypes, words[1], &TypeName::name);
    if (type == kTypes.end()) {
        throw ProbeError(
            "no type '" + words[1] + "'; the types are " + names_of(kTypes, &TypeName::name));
    }
    return {
        join(words, " "),
        "boost",
        std::string(type->name),
        row->run(type->type, words.subspan(2)),
        {}};
}

} // namespace tcalc::probe
