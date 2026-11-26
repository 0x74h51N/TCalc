/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"
#include "calc/internal/helpers.hpp"
#include "calc/pub/error_messages.hpp"
#include "value.hpp"

#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <optional>
#include <string>
#include <type_traits>

#include <boost/multiprecision/cpp_int.hpp>

using tcalc::CollectionKind;

namespace {

namespace mp = boost::multiprecision;
using BigInt = mp::cpp_int;

/// BigReal always holds 73 digits; from 72 a whole BigReal may be a rounded one, and gcd of a
/// rounded integer is a wrong number, not a rounded one (2^{265} loses its last 8 digits).
constexpr int kExactBigDigits = 72;

/// x finite and whole. The digits come from the text: BigReal arithmetic scaling by 10^k
/// rounds, the text does not.
BigInt whole_of(const BigReal &x) {
    std::string text = BigReal(abs(x)).str(0, std::ios_base::scientific);
    const auto e = text.find('e');
    const auto exponent = std::stoll(text.substr(e + 1));
    text.erase(e);
    std::erase(text, '.');
    while (text.size() > 1 && text.back() == '0')
        text.pop_back();
    const auto ten = exponent - (static_cast<std::int64_t>(text.size()) - 1);
    return BigInt(text) * mp::pow(BigInt(kDecimalBase), static_cast<unsigned>(ten));
}

BigInt whole_operand(std::int64_t v, const char *) {
    return calc_detail::magnitude(v);
}

/// The magnitude arm 1 folds of a double: a near-integer below 2^53 rounded, as int_like takes
/// it (denorm_min is 0).
std::optional<std::uint64_t> small_magnitude(double d) {
    if (calc_detail::int_like(d) && std::fabs(d) < static_cast<double>(kExactIntLimit))
        return calc_detail::magnitude(std::llround(d));
    return std::nullopt;
}

/// A double past 2^53 is read as its shortest text (to_big), the value it shows.
BigInt whole_operand(double d, const char *name) {
    if (const auto m = small_magnitude(d))
        return *m;
    if (!calc_detail::int_like(d))
        throw CalculatorError(tcalc::errmsg::integers_only(name).c_str());
    return whole_of(tcalc::to_big(d));
}

/// Past 10^72 (an infinity too) the integer is a rounded one: its gcd is the multiprecision
/// mode's (#275).
BigInt whole_operand(const BigReal &b, const char *name) {
    static const BigReal kRoundedFrom = mp::pow(BigReal(kDecimalBase), kExactBigDigits);
    if (BigReal(abs(b)) >= kRoundedFrom)
        throw CalculatorError(std::string(tcalc::errmsg::kNeedsMultiprecision));
    if (!calc_detail::whole(b))
        throw CalculatorError(tcalc::errmsg::integers_only(name).c_str());
    return whole_of(b);
}

/// The magnitude arm 1 folds: an Int64, or a small whole double.
std::optional<std::uint64_t> small_magnitude(const CollectionItem &it) {
    if (const auto *v = std::get_if<std::int64_t>(&it))
        return calc_detail::magnitude(*v);
    if (const auto *d = std::get_if<double>(&it))
        return small_magnitude(*d);
    return std::nullopt;
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

using SmallStep = std::optional<std::uint64_t> (*)(std::uint64_t, std::uint64_t);

/// Arm 1 folds uint64 magnitudes; an operand or a step it cannot hold hands the fold to
/// arm 2, cpp_int.
CollectionItem
fold_integers(const Collection &a, const char *name, SmallStep small, calc_detail::BigStep big) {
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
    BigInt f = first ? BigInt(acc) : calc_detail::int_operand(items[0], name);
    for (; i < items.size(); ++i)
        f = big(f, calc_detail::int_operand(items[i], name));
    return calc_detail::item_of(f);
}

} // namespace

namespace calc_detail {

std::uint64_t magnitude(std::int64_t v) {
    return v < 0 ? 0 - static_cast<std::uint64_t>(v) : static_cast<std::uint64_t>(v);
}

BigInt int_operand(const CollectionItem &it, const char *name) {
    return std::visit(
        [name](const auto &x) -> BigInt {
            using T = std::decay_t<decltype(x)>;
            if constexpr (
                std::is_same_v<T, std::int64_t> || std::is_same_v<T, double> ||
                std::is_same_v<T, BigReal>)
                return whole_operand(x, name);
            else
                throw CalculatorError(tcalc::errmsg::integers_only(name).c_str());
        },
        it);
}

BigInt gcd_of(const BigInt &a, const BigInt &b) {
    return mp::gcd(a, b);
}

BigInt lcm_of(const BigInt &a, const BigInt &b) {
    return mp::lcm(a, b);
}

CollectionItem item_of(const BigInt &n) {
    if (n <= std::numeric_limits<std::int64_t>::max())
        return CollectionItem{static_cast<std::int64_t>(n)};
    return CollectionItem{BigReal(n.str())};
}

} // namespace calc_detail

CollectionItem Calculator::gcd(const Collection &a) const {
    return fold_integers(a, "gcd", small_gcd, calc_detail::gcd_of);
}

CollectionItem Calculator::lcm(const Collection &a) const {
    return fold_integers(a, "lcm", small_lcm, calc_detail::lcm_of);
}
