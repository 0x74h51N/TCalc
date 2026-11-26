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
#include <type_traits>

#include <boost/multiprecision/cpp_int.hpp>

using tcalc::CollectionKind;

namespace {

namespace mp = boost::multiprecision;
using BigInt = mp::cpp_int;

/// BigReal holds 73 digits, so from 10^72 a whole BigReal may be a rounded one, and gcd of a
/// rounded integer is a wrong number, not a rounded one (2^{265} loses its last 7 digits).
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

/// The magnitude arm 1 folds of a double: a near-integer below 2^53 rounded, as int_like takes
/// it (denorm_min is 0).
std::optional<std::uint64_t> small_magnitude(double d) {
    if (calc_detail::int_like(d) && std::fabs(d) < static_cast<double>(kExactIntLimit))
        return calc_detail::magnitude(std::llround(d));
    return std::nullopt;
}

/// An item's whole magnitude; the arms a kernel item shares with a Value read in calc_detail.
BigInt int_operand(const CollectionItem &it, const char *name) {
    return std::visit(
        [name](const auto &x) -> BigInt {
            using T = std::decay_t<decltype(x)>;
            if constexpr (
                std::is_same_v<T, std::int64_t> || std::is_same_v<T, double> ||
                std::is_same_v<T, BigReal>)
                return calc_detail::whole_operand(x, name);
            else
                throw CalculatorError(tcalc::errmsg::integers_only(name).c_str());
        },
        it);
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

/// n rounded to a BigReal from its leading digits: the whole text of a 16384-bit integer takes
/// 0.8 ms, its leading digits 0.02 ms. A last digit of 1 stands for a nonzero rest, so the
/// rounding is the whole text's.
BigReal rounded_big(const BigInt &n) {
    // More digits than BigReal reads, guard digits included.
    constexpr std::int64_t kLeadingDigits = 100;
    namespace k = boost::math::constants;
    const double bits = static_cast<double>(mp::msb(n));
    const auto digits =
        static_cast<std::int64_t>(bits * k::ln_two<double>() * k::log10_e<double>()) + 1;
    const auto ten = std::max<std::int64_t>(digits - kLeadingDigits, 0);
    BigInt lead;
    BigInt rest;
    mp::divide_qr(n, mp::pow(BigInt(kDecimalBase), static_cast<unsigned>(ten)), lead, rest);
    return BigReal(lead.str() + (rest == 0 ? "0" : "1") + "e" + std::to_string(ten - 1));
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
    BigInt f = first ? BigInt(acc) : int_operand(items[0], name);
    for (; i < items.size(); ++i)
        f = big(f, int_operand(items[i], name));
    return calc_detail::item_of(f);
}

} // namespace

namespace calc_detail {

std::uint64_t magnitude(std::int64_t v) {
    return v < 0 ? 0 - static_cast<std::uint64_t>(v) : static_cast<std::uint64_t>(v);
}

BigInt whole_operand(std::int64_t v, const char *) {
    return magnitude(v);
}

/// A double past 2^53 is read as its shortest text (to_big), the value it shows.
BigInt whole_operand(double d, const char *name) {
    if (const auto m = small_magnitude(d))
        return *m;
    if (!int_like(d))
        throw CalculatorError(tcalc::errmsg::integers_only(name).c_str());
    return whole_of(tcalc::to_big(d));
}

/// Past 10^72 (an infinity too) the integer may be a rounded one: its gcd is the multiprecision
/// mode's (#275).
BigInt whole_operand(const BigReal &b, const char *name) {
    static const BigReal kRoundedFrom = mp::pow(BigReal(kDecimalBase), kExactBigDigits);
    if (BigReal(abs(b)) >= kRoundedFrom)
        throw CalculatorError(std::string(tcalc::errmsg::kNeedsMultiprecision));
    if (!whole(b))
        throw CalculatorError(tcalc::errmsg::integers_only(name).c_str());
    return whole_of(b);
}

BigInt gcd_of(const BigInt &a, const BigInt &b) {
    return mp::gcd(a, b);
}

BigInt lcm_of(const BigInt &a, const BigInt &b) {
    static const BigInt kLimit = BigInt(1) << (kMaxIntBits + 1);
    BigInt l = mp::lcm(a, b);
    if (l >= kLimit)
        throw CalculatorError(std::string(tcalc::errmsg::kNeedsMultiprecision));
    return l;
}

CollectionItem item_of(const BigInt &n) {
    if (n <= std::numeric_limits<std::int64_t>::max())
        return CollectionItem{static_cast<std::int64_t>(n)};
    return CollectionItem{rounded_big(n)};
}

} // namespace calc_detail

CollectionItem Calculator::gcd(const Collection &a) const {
    return fold_integers(a, "gcd", small_gcd, calc_detail::gcd_of);
}

CollectionItem Calculator::lcm(const Collection &a) const {
    return fold_integers(a, "lcm", small_lcm, calc_detail::lcm_of);
}
