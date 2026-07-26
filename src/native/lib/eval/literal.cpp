/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "eval/pub/literal.hpp"

#include <cctype>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>

#include <boost/multiprecision/cpp_int.hpp>

#include "parser/pub/consts.hpp"

namespace tcalc::eval {

namespace {

using BigInt = boost::multiprecision::cpp_int;

constexpr int kDecimalBase = 10;
/// A decimal whose adjusted exponent runs past int64's ~19 significant digits cannot fit a
/// Rational, so the exact path bails at this magnitude.
constexpr long long kMaxRationalExp = 18;

/// True when c is the imaginary unit's symbol or one of its aliases. Read from the
/// constants table rather than hard-coded, so "i"/"I"/"j" stay in sync with consts.hpp.
bool is_imag_unit_char(char c) {
    const auto *spec = consts::const_spec(consts::ConstId::Imaginary);
    if (spec->symbol.size() == 1 && spec->symbol[0] == c)
        return true;
    for (const auto &alias : spec->aliases)
        if (alias.size() == 1 && alias[0] == c)
            return true;
    return false;
}

/// True when a literal's digits (ignoring sign, dot and any exponent) are all zero,
/// i.e. the literal denotes zero rather than a value too small for a double to hold.
bool literal_digits_are_zero(const std::string &s) {
    const auto e_pos = s.find_first_of("eE");
    const std::string_view mantissa =
        e_pos == std::string::npos ? std::string_view(s) : std::string_view(s).substr(0, e_pos);
    for (const char c : mantissa)
        if (c >= '1' && c <= '9')
            return false;
    return true;
}

/// A decimal literal split the way Decimal does: significant digits (leading zeros
/// stripped, "0" for a zero value) and the power of ten applied to them, so that the
/// value equals `digits * 10^exponent`.
struct DecimalParts {
    std::string digits;
    long long exponent = 0;
    bool negative = false;
};

DecimalParts parse_decimal_parts(const std::string &s) {
    std::size_t i = 0;
    bool neg = false;
    if (i < s.size() && (s[i] == '+' || s[i] == '-')) {
        neg = s[i] == '-';
        ++i;
    }
    std::string int_part;
    while (i < s.size() && std::isdigit(static_cast<unsigned char>(s[i])))
        int_part += s[i++];
    std::string frac_part;
    if (i < s.size() && s[i] == '.') {
        ++i;
        while (i < s.size() && std::isdigit(static_cast<unsigned char>(s[i])))
            frac_part += s[i++];
    }
    long long explicit_exp = 0;
    if (i < s.size() && (s[i] == 'e' || s[i] == 'E')) {
        ++i;
        explicit_exp = std::stoll(s.substr(i));
    }

    const std::string digit_string = int_part + frac_part;
    const long long exponent = explicit_exp - static_cast<long long>(frac_part.size());
    const auto first_nonzero = digit_string.find_first_not_of('0');
    const std::string digits =
        first_nonzero == std::string::npos ? "0" : digit_string.substr(first_nonzero);
    return {digits, exponent, neg};
}

/// digits * 10^abs(exp), computed with arbitrary precision so overflow past int64 is
/// detected exactly rather than wrapping.
BigInt pow10(long long exp) {
    BigInt result(1);
    for (long long i = 0; i < exp; ++i)
        result *= kDecimalBase;
    return result;
}

/// The exact-fraction path for a decimal literal: Rational(num, den) with Boost
/// reducing by GCD. Returns nullopt when the fraction could not fit an int64
/// numerator/denominator, so the caller falls back to the real reader.
std::optional<Rational> exact_decimal(const std::string &s) {
    const DecimalParts parts = parse_decimal_parts(s);
    const long long digit_count = static_cast<long long>(parts.digits.size());
    const long long adjusted = parts.exponent + digit_count - 1;
    if (adjusted > kMaxRationalExp || adjusted < -kMaxRationalExp)
        return std::nullopt;

    const BigInt coeff(parts.digits);
    BigInt num;
    BigInt den;
    if (parts.exponent >= 0) {
        num = coeff * pow10(parts.exponent);
        den = 1;
    } else {
        num = coeff;
        den = pow10(-parts.exponent);
    }
    if (parts.negative)
        num = -num;

    static const BigInt kMax(std::numeric_limits<std::int64_t>::max());
    static const BigInt kMin(std::numeric_limits<std::int64_t>::min());
    if (num > kMax || num < kMin || den > kMax)
        return std::nullopt;

    return Rational(num.convert_to<std::int64_t>(), den.convert_to<std::int64_t>());
}

/// The real reader: no '.' and no 'e' is an integer (int64, or BigReal past int64's
/// range); otherwise a double, promoted to BigReal when the literal has an exponent
/// and the double came out non-finite, or came out zero although the literal is not
/// itself zero (an underflow, the reason 1e-400 must not collapse to 0.0).
Value parse_real(const std::string &s) {
    const bool has_dot = s.find('.') != std::string::npos;
    const bool has_e = s.find('e') != std::string::npos || s.find('E') != std::string::npos;

    if (!has_dot && !has_e) {
        try {
            std::size_t pos = 0;
            const long long v = std::stoll(s, &pos);
            if (pos == s.size())
                return Value{static_cast<std::int64_t>(v)};
        } catch (const std::exception &) {
            return Value{BigReal(s)}; // too many digits for int64; BigReal holds it
        }
        return Value{BigReal(s)};
    }

    // strtod, not stod: over/underflow must not throw, it must report through the
    // result itself (inf, or a finite zero), the same way Python's float(s) never
    // raises for either case.
    char *end = nullptr;
    const double f = std::strtod(s.c_str(), &end);
    // c_str is null-terminated, so a fully consumed literal leaves end on the '\0'.
    if (*end != '\0')
        return Value{BigReal(s)};

    if (has_e) {
        const bool literal_is_zero = literal_digits_are_zero(s);
        const bool float_ok = std::isfinite(f) && (f != 0.0 || literal_is_zero);
        if (!float_ok) {
            try {
                return Value{BigReal(s)};
            } catch (const std::exception &) {
                return Value{f}; // BigReal could not parse it either; keep the double
            }
        }
    }
    return Value{f};
}

} // namespace

Value literal_value(std::string_view text) {
    std::string s(text);
    if (s.empty())
        return parse_real(s);

    if (is_imag_unit_char(s.front()))
        s = s.substr(1) + s.front();

    if (is_imag_unit_char(s.back())) {
        const std::string real_part = s.substr(0, s.size() - 1);
        double magnitude = 1.0;
        if (!real_part.empty()) {
            // parse_real only ever returns an Int64, Double or BigReal, the arms
            // to_double already has an overload for.
            const Value real = parse_real(real_part);
            if (const auto *i = std::get_if<std::int64_t>(&real))
                magnitude = to_double(*i);
            else if (const auto *d = std::get_if<double>(&real))
                magnitude = to_double(*d);
            else
                magnitude = to_double(std::get<BigReal>(real));
        }
        return Value{Complex(0.0, magnitude)};
    }

    if (s.find('.') == std::string::npos) {
        try {
            std::size_t pos = 0;
            const long long v = std::stoll(s, &pos);
            if (pos == s.size())
                return Value{static_cast<std::int64_t>(v)};
        } catch (const std::exception &) {
            return parse_real(s); // too big for int64; the real reader promotes it
        }
        return parse_real(s);
    }

    if (const auto exact = exact_decimal(s))
        return Value{*exact};
    return parse_real(s);
}

} // namespace tcalc::eval
