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

#include "parser/internal/helpers.hpp"

namespace tcalc::consts {

enum class CategoryId : std::uint8_t {
    Mathematics,
    Universal,
    Electromagnetism,
    AtomicNuclear,
    Thermodynamics,
    Chemistry,
    Count
};

enum class ConstId : std::uint8_t {
    Pi,
    EulerNumber,
    Imaginary,
    GoldenRatio,
    Tau,
    SpeedOfLight,
    PlanckH,
    PlanckHbar,
    Gravitation,
    VacuumPermittivity,
    VacuumPermeability,
    VacuumImpedance,
    ElementaryCharge,
    FineStructure,
    BohrRadius,
    Rydberg,
    ElectronMass,
    ProtonMass,
    NeutronMass,
    GasConstant,
    Boltzmann,
    Avogadro,
    Faraday,
    AtomicMass,
    StefanBoltzmann,
    WienDisplacement,
    VonKlitzing,
    Josephson,
    BohrMagneton,
    NuclearMagneton,
    Count
};

using Complex = std::complex<double>;
using ConstValue = std::variant<double, Complex>; // CalcValue-style: natural type per constant

struct ConstSpec {
    ConstId id;
    CategoryId category;                     // GUI menu grouping; 1 byte, constexpr
    std::string_view symbol;                 // display + matchable
    std::array<std::string_view, 3> aliases; // extra matchable spellings
    ConstValue value;                        // boost double, or Complex(0,1) for imaginary unit
};

inline constexpr std::array kConstants{
    ConstSpec{
        .id = ConstId::Pi,
        .category = CategoryId::Mathematics,
        .symbol = "π",
        .aliases = {"pi"},
        .value = boost::math::constants::pi<double>()},
    ConstSpec{
        .id = ConstId::EulerNumber,
        .category = CategoryId::Mathematics,
        .symbol = "e",
        .aliases = {"euler"},
        .value = boost::math::constants::e<double>()},
    ConstSpec{
        .id = ConstId::Imaginary,
        .category = CategoryId::Mathematics,
        .symbol = "i",
        .aliases = {"I", "j"},
        .value = Complex(0.0, 1.0)},
    ConstSpec{
        .id = ConstId::GoldenRatio,
        .category = CategoryId::Mathematics,
        .symbol = "φ",
        .aliases = {"phi"},
        .value = boost::math::constants::phi<double>()},
    ConstSpec{
        .id = ConstId::Tau,
        .category = CategoryId::Mathematics,
        .symbol = "τ",
        .aliases = {"tau"},
        .value = boost::math::constants::two_pi<double>()},
    ConstSpec{
        .id = ConstId::SpeedOfLight,
        .category = CategoryId::Universal,
        .symbol = "c",
        .aliases = {"lightspeed"},
        .value = 299792458.0},
    ConstSpec{
        .id = ConstId::PlanckH,
        .category = CategoryId::Universal,
        .symbol = "h",
        .aliases = {"planck"},
        .value = 6.62607015e-34},
    ConstSpec{
        .id = ConstId::PlanckHbar,
        .category = CategoryId::Universal,
        .symbol = "ℏ",
        .aliases = {"hbar"},
        .value = 6.62607015e-34 / (2.0 * boost::math::constants::pi<double>())},
    ConstSpec{
        .id = ConstId::Gravitation,
        .category = CategoryId::Universal,
        .symbol = "G",
        .aliases = {"gravitation"},
        .value = 6.67430e-11},
    ConstSpec{
        .id = ConstId::VacuumPermittivity,
        .category = CategoryId::Electromagnetism,
        .symbol = "ε₀",
        .aliases = {"vacuumpermittivity", "permittivity"},
        .value = 8.8541878188e-12},
    ConstSpec{
        .id = ConstId::VacuumPermeability,
        .category = CategoryId::Electromagnetism,
        .symbol = "μ₀",
        .aliases = {"vacuumpermeability", "permeability"},
        .value = 1.25663706127e-6},
    ConstSpec{
        .id = ConstId::VacuumImpedance,
        .category = CategoryId::Electromagnetism,
        .symbol = "Z₀",
        .aliases = {"vacuumimpedance", "impedance"},
        .value = 376.730313412},
    ConstSpec{
        .id = ConstId::ElementaryCharge,
        .category = CategoryId::Electromagnetism,
        .symbol = "ᵉ",
        .aliases = {"elementarycharge"},
        .value = 1.602176634e-19},
    ConstSpec{
        .id = ConstId::FineStructure,
        .category = CategoryId::AtomicNuclear,
        .symbol = "α",
        .aliases = {"finestructure"},
        .value = 7.2973525643e-3},
    ConstSpec{
        .id = ConstId::BohrRadius,
        .category = CategoryId::AtomicNuclear,
        .symbol = "a₀",
        .aliases = {"bohrradius"},
        .value = 5.29177210544e-11},
    ConstSpec{
        .id = ConstId::Rydberg,
        .category = CategoryId::AtomicNuclear,
        .symbol = "R_{∞}",
        .aliases = {"rydberg"},
        .value = 10973731.568157},
    ConstSpec{
        .id = ConstId::ElectronMass,
        .category = CategoryId::AtomicNuclear,
        .symbol = "mₑ",
        .aliases = {"electronmass"},
        .value = 9.1093837139e-31},
    ConstSpec{
        .id = ConstId::ProtonMass,
        .category = CategoryId::AtomicNuclear,
        .symbol = "mₚ",
        .aliases = {"protonmass"},
        .value = 1.67262192595e-27},
    ConstSpec{
        .id = ConstId::NeutronMass,
        .category = CategoryId::AtomicNuclear,
        .symbol = "mₙ",
        .aliases = {"neutronmass"},
        .value = 1.67492750056e-27},
    ConstSpec{
        .id = ConstId::GasConstant,
        .category = CategoryId::Thermodynamics,
        .symbol = "R",
        .aliases = {"gasconstant"},
        .value = 8.314462618},
    ConstSpec{
        .id = ConstId::Boltzmann,
        .category = CategoryId::Thermodynamics,
        .symbol = "k",
        .aliases = {"boltzmann"},
        .value = 1.380649e-23},
    ConstSpec{
        .id = ConstId::Avogadro,
        .category = CategoryId::Chemistry,
        .symbol = "Nₐ",
        .aliases = {"avogadro"},
        .value = 6.02214076e23},
    ConstSpec{
        .id = ConstId::Faraday,
        .category = CategoryId::Chemistry,
        .symbol = "F",
        .aliases = {"faraday"},
        .value = 96485.33212},
    ConstSpec{
        .id = ConstId::AtomicMass,
        .category = CategoryId::Chemistry,
        .symbol = "mᵤ",
        .aliases = {"atomicmass"},
        .value = 1.66053906892e-27},
    ConstSpec{
        .id = ConstId::StefanBoltzmann,
        .category = CategoryId::Thermodynamics,
        .symbol = "σ_{SB}",
        .aliases = {},
        .value = 5.670374419e-8},
    ConstSpec{
        .id = ConstId::WienDisplacement,
        .category = CategoryId::Thermodynamics,
        .symbol = "b_{W}",
        .aliases = {},
        .value = 2.897771955e-3},
    ConstSpec{
        .id = ConstId::VonKlitzing,
        .category = CategoryId::Electromagnetism,
        .symbol = "R_{K}",
        .aliases = {},
        .value = 25812.80745},
    ConstSpec{
        .id = ConstId::Josephson,
        .category = CategoryId::Electromagnetism,
        .symbol = "K_{J}",
        .aliases = {},
        .value = 483597.8484e9},
    ConstSpec{
        .id = ConstId::BohrMagneton,
        .category = CategoryId::AtomicNuclear,
        .symbol = "μ_{B}",
        .aliases = {},
        .value = 9.2740100657e-24},
    ConstSpec{
        .id = ConstId::NuclearMagneton,
        .category = CategoryId::AtomicNuclear,
        .symbol = "μ_{N}",
        .aliases = {},
        .value = 5.0507837393e-27},
};

inline constexpr auto kConstsById =
    parser::index_by_id<ConstSpec, static_cast<std::size_t>(ConstId::Count)>(kConstants);

inline constexpr const ConstSpec *const_spec(ConstId id) {
    return kConstsById[static_cast<std::size_t>(id)];
}

// First-byte filter: kConstCanStart[b] is true iff some constant symbol or alias
// starts with byte b. Lets match_const skip the scan at non-constant positions.
consteval parser::FirstByteTable build_const_can_start() {
    parser::FirstByteTable out{};
    for (const auto &c : kConstants) {
        parser::mark_first_byte(out, c.symbol);
        for (const auto &alias : c.aliases) {
            parser::mark_first_byte(out, alias);
        }
    }
    return out;
}
inline constexpr auto kConstCanStart = build_const_can_start();

inline constexpr const ConstSpec *
match_const(std::string_view s, std::size_t i, std::size_t &out_len) {
    const std::string_view rest = s.substr(i);
    if (rest.empty() || !kConstCanStart[static_cast<unsigned char>(rest[0])]) {
        out_len = 0;
        return nullptr;
    }
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
