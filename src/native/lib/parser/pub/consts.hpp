/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <array>
#include <complex>
#include <cstdint>
#include <string_view>
#include <variant>

#include <boost/math/constants/constants.hpp>

namespace tcalc::consts {

enum class ConstId : std::uint8_t { Pi, E, ImagUnit, Phi, Tau, Count };

using Complex = std::complex<double>;
using ConstValue = std::variant<double, Complex>; // CalcValue-style: natural type per constant

struct ConstSpec {
    ConstId id;
    std::string_view symbol;                 // display + matchable
    std::array<std::string_view, 3> aliases; // extra matchable spellings
    ConstValue value;                        // boost double, or Complex(0,1) for imaginary unit
};

inline constexpr std::array kConstants{
    ConstSpec{
        .id = ConstId::Pi,
        .symbol = "π",
        .aliases = {"pi"},
        .value = boost::math::constants::pi<double>()},
    ConstSpec{
        .id = ConstId::E,
        .symbol = "e",
        .aliases = {},
        .value = boost::math::constants::e<double>()},
    ConstSpec{
        .id = ConstId::ImagUnit,
        .symbol = "i",
        .aliases = {"I", "j", "J"},
        .value = Complex(0.0, 1.0)},
    ConstSpec{
        .id = ConstId::Phi,
        .symbol = "φ",
        .aliases = {"phi"},
        .value = boost::math::constants::phi<double>()},
    ConstSpec{
        .id = ConstId::Tau,
        .symbol = "τ",
        .aliases = {"tau"},
        .value = boost::math::constants::two_pi<double>()},
};

consteval auto build_consts_by_id() {
    std::array<const ConstSpec *, static_cast<std::size_t>(ConstId::Count)> out{};
    for (auto &p : out) {
        p = nullptr;
    }
    for (const auto &c : kConstants) {
        const std::size_t idx = static_cast<std::size_t>(c.id);
        if (idx >= out.size()) {
            throw "consts.hpp: ConstId out of range";
        }
        if (out[idx] != nullptr) {
            throw "consts.hpp: duplicate ConstId";
        }
        out[idx] = &c;
    }
    return out;
}
inline constexpr auto kConstsById = build_consts_by_id();

inline constexpr const ConstSpec *const_spec(ConstId id) {
    return kConstsById[static_cast<std::size_t>(id)];
}

inline constexpr const ConstSpec *
match_const(std::string_view s, std::size_t i, std::size_t &out_len) {
    const std::string_view rest = s.substr(i);
    const ConstSpec *best = nullptr;
    std::size_t best_len = 0;
    const auto consider = [&](std::string_view name, const ConstSpec &c) {
        if (!name.empty() && name.size() > best_len && rest.starts_with(name)) {
            best = &c;
            best_len = name.size();
        }
    };
    for (const auto &c : kConstants) {
        consider(c.symbol, c);
        for (const auto &alias : c.aliases) {
            consider(alias, c);
        }
    }
    out_len = best_len;
    return best;
}

} // namespace tcalc::consts
