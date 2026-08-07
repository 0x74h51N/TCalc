/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <optional>
#include <string>
#include <boost/multiprecision/cpp_int.hpp>
#include "eval/pub/eval.hpp"
#include "eval/pub/varstore.hpp"
#include "parser/pub/consts.hpp"
#include "value.hpp"

namespace tcalc::eval {

using CppRat = boost::multiprecision::cpp_rational;

/// One symbol in a product: a table constant, or a single-letter session variable. One id field
/// carries both namespaces, and their ranges overlap (ConstIds count from 0, letters from 'A'),
/// so the sign discriminates. These four are the only place that encoding is written.
struct Sym {
    std::int16_t id = 0;
    std::int8_t exp = 0;
};

constexpr std::int16_t const_sym(consts::ConstId id) {
    return static_cast<std::int16_t>(id);
}
constexpr std::int16_t var_sym(char name) {
    return static_cast<std::int16_t>(-static_cast<int>(name));
}
constexpr bool is_const_sym(std::int16_t id) {
    return id >= 0;
}
constexpr char sym_var_name(std::int16_t id) {
    return static_cast<char>(-id);
}

inline constexpr std::size_t kMaxSyms = 6;
// The exponent is an int8_t, and every arithmetic path checks against these before narrowing.
inline constexpr int kMaxSymExp = 127;
inline constexpr int kMinSymExp = -128;
// Size ceiling for Scalar, 112 as measured. What keeps a std::vector out of the struct: one would
// add its own header plus a heap block per coefficient, and Poly holds one Scalar per degree.
inline constexpr std::size_t kMaxScalarBytes = 128;

/// A product term: coeff * PRODUCT(sym^exp) * real. `real` is 1 unless the symbolic form was
/// lost, which happens when two unlike products are added.
struct Scalar {
    CppRat coeff{1};
    std::array<Sym, kMaxSyms> syms{};
    std::uint8_t n_syms = 0;
    double real = 1.0;
};

inline Scalar scalar_rational(const CppRat &c) {
    Scalar s;
    s.coeff = c;
    return s;
}

/// A Value as an exact rational, or nullopt. A double is never lifted: 0.1 has no exact rational
/// form, and pretending otherwise would fake precision.
inline std::optional<CppRat> const_coeff(const Value &v) {
    const std::optional<Rational> r = to_rational(v);
    if (!r)
        return std::nullopt;
    return CppRat(r->numerator(), r->denominator());
}

inline Scalar scalar_of(std::int16_t id) {
    Scalar s;
    s.syms[0] = Sym{id, 1};
    s.n_syms = 1;
    return s;
}

inline Scalar scalar_symbol(consts::ConstId id) {
    return scalar_of(const_sym(id));
}

inline Scalar scalar_variable(char name) {
    return scalar_of(var_sym(name));
}

/// No symbols and no residual: the value is exactly `coeff`, so every existing exact path applies.
inline bool scalar_is_rational(const Scalar &s) {
    return s.n_syms == 0 && s.real == 1.0;
}

/// Zero on the effective value: a zero coefficient or a zero residual makes the whole term zero.
inline bool scalar_is_zero(const Scalar &s) {
    return s.coeff == 0 || s.real == 0.0;
}

/// Structural. Two scalars are the same factor when their symbol sets and residuals match; the
/// coefficient is deliberately excluded, so this answers "is this the same kind of term".
inline bool scalar_same_symbols(const Scalar &a, const Scalar &b) {
    if (a.n_syms != b.n_syms || a.real != b.real)
        return false;
    for (std::size_t i = 0; i < a.n_syms; ++i)
        if (a.syms[i].id != b.syms[i].id || a.syms[i].exp != b.syms[i].exp)
            return false;
    return true;
}

inline bool scalar_equal(const Scalar &a, const Scalar &b) {
    return a.coeff == b.coeff && scalar_same_symbols(a, b);
}

/// Resolve a symbol to its numeric value. A constant comes from the table; a variable from the
/// session store, which must still hold it (the walk only creates one for a bound value).
inline std::optional<double> sym_value(const Sym &s) {
    if (is_const_sym(s.id)) {
        const Value v = const_value(static_cast<consts::ConstId>(s.id));
        const auto *d = std::get_if<double>(&v);
        return d ? std::optional<double>(*d) : std::nullopt;
    }
    const Value *v = session_vars().get(std::string(1, sym_var_name(s.id)));
    if (v == nullptr)
        return std::nullopt;
    const auto *d = std::get_if<double>(v);
    return d ? std::optional<double>(*d) : std::nullopt;
}

/// The whole term as a double. nullopt when a symbol cannot be resolved.
inline std::optional<double> scalar_eval(const Scalar &s) {
    double acc = s.coeff.convert_to<double>() * s.real;
    for (std::size_t i = 0; i < s.n_syms; ++i) {
        const auto v = sym_value(s.syms[i]);
        if (!v)
            return std::nullopt;
        // Repeated multiply or divide, not std::pow: exponents here are small integers, and a
        // reciprocal built by division lands on the same double the expression it came from does.
        for (int k = 0; k < s.syms[i].exp; ++k)
            acc *= *v;
        for (int k = 0; k > s.syms[i].exp; --k)
            acc /= *v;
    }
    return acc;
}

/// The scalar's symbolic part alone, coefficient dropped. What a caller multiplies back in when
/// the exact core already accounted for the coefficient.
inline Scalar scalar_symbols_of(const Scalar &s) {
    Scalar r = s;
    r.coeff = 1;
    return r;
}

/// Insert or merge a symbol at `exp`, keeping the list sorted by id so comparison is structural.
/// Returns false when the slots are full, which makes the caller decline.
inline bool scalar_push(Scalar &s, std::int16_t id, int exp) {
    for (std::size_t i = 0; i < s.n_syms; ++i) {
        if (s.syms[i].id != id)
            continue;
        const int e = s.syms[i].exp + exp;
        if (e > kMaxSymExp || e < kMinSymExp)
            return false;
        s.syms[i].exp = static_cast<std::int8_t>(e);
        if (s.syms[i].exp == 0) { // the symbol cancelled out
            for (std::size_t j = i; j + 1 < s.n_syms; ++j)
                s.syms[j] = s.syms[j + 1];
            --s.n_syms;
        }
        return true;
    }
    if (s.n_syms == kMaxSyms || exp > kMaxSymExp || exp < kMinSymExp)
        return false;
    std::size_t at = 0;
    while (at < s.n_syms && s.syms[at].id < id)
        ++at;
    for (std::size_t j = s.n_syms; j > at; --j)
        s.syms[j] = s.syms[j - 1];
    s.syms[at] = Sym{id, static_cast<std::int8_t>(exp)};
    ++s.n_syms;
    return true;
}

inline std::optional<Scalar> scalar_mul(const Scalar &a, const Scalar &b) {
    Scalar r = a;
    r.coeff *= b.coeff;
    r.real *= b.real;
    for (std::size_t i = 0; i < b.n_syms; ++i)
        if (!scalar_push(r, b.syms[i].id, b.syms[i].exp))
            return std::nullopt;
    return r;
}

inline std::optional<Scalar> scalar_div(const Scalar &a, const Scalar &b) {
    if (scalar_is_zero(b))
        return std::nullopt; // the caller raises the calc's own division error
    Scalar r = a;
    r.coeff /= b.coeff;
    r.real /= b.real;
    for (std::size_t i = 0; i < b.n_syms; ++i)
        if (!scalar_push(r, b.syms[i].id, -b.syms[i].exp))
            return std::nullopt;
    return r;
}

inline Scalar scalar_negate_copy(const Scalar &s) {
    Scalar r = s;
    r.coeff = -r.coeff;
    return r;
}

/// a + sign*b. Like products add exactly; unlike ones leave the symbolic world and keep only
/// their value, which is what makes `5 + pi` a term at all. nullopt only when a value is
/// unresolvable.
inline std::optional<Scalar> scalar_add(const Scalar &a, const Scalar &b, int sign) {
    if (scalar_is_zero(a))
        return sign < 0 ? scalar_negate_copy(b) : b;
    if (scalar_is_zero(b))
        return a;
    if (scalar_same_symbols(a, b)) {
        Scalar r = a;
        r.coeff = a.coeff + sign * b.coeff;
        return r;
    }
    const auto va = scalar_eval(a);
    const auto vb = scalar_eval(b);
    if (!va || !vb)
        return std::nullopt;
    Scalar r;
    r.real = *va + sign * *vb;
    return r;
}

} // namespace tcalc::eval

static_assert(sizeof(tcalc::eval::Scalar) <= tcalc::eval::kMaxScalarBytes, "Scalar grew");
