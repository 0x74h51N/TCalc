/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"
#include "calc/pub/error_messages.hpp"
#include "value.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <optional>
#include <string>

#include <boost/multiprecision/cpp_int.hpp>

using tcalc::CollectionKind;

namespace {

namespace mp = boost::multiprecision;
using Wide = mp::int512_t;

constexpr int kTwo = 2;
constexpr int kFive = 5;
/// msb(a) + msb(b) at most this keeps a * b under 2^511, inside int512_t.
constexpr std::size_t kWideProductMsb = 509;
/// An upper bound on log2 of each base, so base^e is known to fit before it is formed.
constexpr std::int64_t kTwoBits = 1;
constexpr std::int64_t kFiveBits = 3;
constexpr std::int64_t kTenBits = 4;

/// The integer r * 2^two * 5^five; r is 0 or not divisible by 2 or 5.
struct Factored {
    Wide r;
    std::int64_t two;
    std::int64_t five;
};

/// Factored with every 2 and 5 of r moved into its exponents.
Factored strip(Wide r, std::int64_t two, std::int64_t five) {
    if (r == 0)
        return {0, 0, 0};
    const auto twos = mp::lsb(r);
    r >>= twos;
    two += static_cast<std::int64_t>(twos);
    while (r % kFive == 0) {
        r /= kFive;
        ++five;
    }
    return {r, two, five};
}

Factored factored(std::uint64_t m) {
    return strip(Wide(m), 0, 0);
}

/// x finite and whole. The digits come from the text: BigReal arithmetic shifting by 10^k
/// rounds, the text does not.
Factored factored(const BigReal &x) {
    if (x == 0)
        return {0, 0, 0};
    std::string text = BigReal(abs(x)).str(0, std::ios_base::scientific);
    const auto e = text.find('e');
    const auto exponent = std::stoll(text.substr(e + 1));
    text.erase(e);
    std::erase(text, '.');
    while (text.size() > 1 && text.back() == '0')
        text.pop_back();
    const std::int64_t ten = exponent - (static_cast<std::int64_t>(text.size()) - 1);
    return strip(Wide(text), ten, ten);
}

/// a * base^e when it fits int512_t; bits is an upper bound on log2(base).
std::optional<Wide> scaled(const Wide &a, int base, std::int64_t e, std::int64_t bits) {
    if (a == 0 || e == 0)
        return a;
    if (e > static_cast<std::int64_t>(kWideProductMsb) / bits)
        return std::nullopt;
    const Wide factor = mp::pow(Wide(base), static_cast<unsigned>(e));
    if (mp::msb(a) + mp::msb(factor) > kWideProductMsb)
        return std::nullopt;
    return a * factor;
}

/// An Int64 when it fits, else a BigReal read from text with its exponent.
CollectionItem item_of(const Factored &f) {
    const std::int64_t p = std::min(f.two, f.five);
    const auto twos = scaled(f.r, kTwo, f.two - p, kTwoBits);
    const auto n = twos ? scaled(*twos, kFive, f.five - p, kFiveBits) : std::nullopt;
    if (n) {
        if (const auto whole = scaled(*n, kDecimalBase, p, kTenBits);
            whole && *whole <= std::numeric_limits<std::int64_t>::max())
            return CollectionItem{static_cast<std::int64_t>(*whole)};
        return CollectionItem{BigReal(n->str() + "e" + std::to_string(p))};
    }
    // Past int512_t: more digits than BigReal holds, so the BigReal product's rounding is all
    // that is lost; every digit is the multiprecision mode's (#275).
    using mp::pow;
    return CollectionItem{
        BigReal(f.r.str() + "e" + std::to_string(p)) * pow(BigReal(kTwo), f.two - p) *
        pow(BigReal(kFive), f.five - p)};
}

/// The magnitude arm 1 folds: an Int64, or a whole double a double holds every integer up to.
std::optional<std::uint64_t> small_magnitude(const CollectionItem &it) {
    if (const auto *v = std::get_if<std::int64_t>(&it))
        return *v < 0 ? 0 - static_cast<std::uint64_t>(*v) : static_cast<std::uint64_t>(*v);
    if (const auto *d = std::get_if<double>(&it);
        d && calc_detail::int_like(*d) && std::fabs(*d) < static_cast<double>(kExactIntLimit)) {
        const std::int64_t v = std::llround(*d);
        return v < 0 ? 0 - static_cast<std::uint64_t>(v) : static_cast<std::uint64_t>(v);
    }
    return std::nullopt;
}

/// A whole operand arm 1 does not take, as a BigReal; a double is read as its shortest decimal.
BigReal big_operand(const CollectionItem &it, const char *name) {
    if (const auto *d = std::get_if<double>(&it); d && calc_detail::int_like(*d))
        return tcalc::to_big(*d);
    // An infinity is whole to floor, but int512_t cannot hold it (#247's smoke list).
    if (const auto *b = std::get_if<BigReal>(&it);
        b && !boost::multiprecision::isinf(*b) && calc_detail::whole(*b))
        return *b;
    throw CalculatorError(tcalc::errmsg::integers_only(name).c_str());
}

Factored factored_item(const CollectionItem &it, const char *name) {
    if (const auto m = small_magnitude(it))
        return factored(*m);
    return factored(big_operand(it, name));
}

std::optional<std::uint64_t> small_gcd(std::uint64_t a, std::uint64_t b) {
    return std::gcd(a, b);
}

/// Empty when the lcm is past uint64; the product is formed in int256_t as a Rational
/// product is (Calculator::mul).
std::optional<std::uint64_t> small_lcm(std::uint64_t a, std::uint64_t b) {
    if (a == 0 || b == 0)
        return 0;
    const mp::int256_t product = mp::int256_t(a / std::gcd(a, b)) * b;
    if (product > std::numeric_limits<std::uint64_t>::max())
        return std::nullopt;
    return static_cast<std::uint64_t>(product);
}

Factored gcd_of(const Factored &a, const Factored &b) {
    if (a.r == 0)
        return b;
    if (b.r == 0)
        return a;
    return {mp::gcd(a.r, b.r), std::min(a.two, b.two), std::min(a.five, b.five)};
}

Factored lcm_of(const Factored &a, const Factored &b) {
    if (a.r == 0 || b.r == 0)
        return {0, 0, 0};
    const Wide q = a.r / mp::gcd(a.r, b.r);
    const std::int64_t two = std::max(a.two, b.two);
    const std::int64_t five = std::max(a.five, b.five);
    if (mp::msb(q) + mp::msb(b.r) <= kWideProductMsb)
        return {q * b.r, two, five};
    // Past int512_t the product has more digits than BigReal holds: it is rounded there.
    const Factored f = factored(BigReal(q.str()) * BigReal(b.r.str()));
    return {f.r, f.two + two, f.five + five};
}

using SmallStep = std::optional<std::uint64_t> (*)(std::uint64_t, std::uint64_t);
using FactoredStep = Factored (*)(const Factored &, const Factored &);

/// Arm 1 folds uint64 magnitudes; an operand or a step it cannot hold hands the fold to
/// arm 2, the factored integer.
CollectionItem
fold_integers(const Collection &a, const char *name, SmallStep small, FactoredStep big) {
    if (a.kind == CollectionKind::Point)
        throw CalculatorError(tcalc::errmsg::not_for_point(name).c_str());
    const auto &items = a.items();
    if (items.empty())
        throw CalculatorError(tcalc::errmsg::empty_collection(name).c_str());
    const auto first = small_magnitude(items[0]);
    std::size_t i = 1;
    std::uint64_t acc = first.value_or(0);
    if (first) {
        for (; i < items.size(); ++i) {
            const auto m = small_magnitude(items[i]);
            const auto next = m ? small(acc, *m) : std::nullopt;
            if (!next)
                break;
            acc = *next;
        }
        if (i == items.size() && acc <= std::numeric_limits<std::int64_t>::max())
            return CollectionItem{static_cast<std::int64_t>(acc)};
    }
    Factored f = first ? factored(acc) : factored_item(items[0], name);
    for (; i < items.size(); ++i)
        f = big(f, factored_item(items[i], name));
    return item_of(f);
}

} // namespace

CollectionItem Calculator::gcd(const Collection &a) const {
    return fold_integers(a, "gcd", small_gcd, gcd_of);
}

CollectionItem Calculator::lcm(const Collection &a) const {
    return fold_integers(a, "lcm", small_lcm, lcm_of);
}
