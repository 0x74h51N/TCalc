/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

// The frame every native_probe command shares: typed operands, the value texts and the
// rows, in the forms scripts/probes/rows.py writes and the grader reads back.

#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <map>
#include <optional>
#include <ostream>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

#include "value.hpp"

namespace tcalc::probe {

/// A failure the user of the probe can fix; printed as a message, not as a row.
struct ProbeError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

template <class... F> struct Overloads : F... {
    using F::operator()...;
};

/// The whole text as a T, or nullopt when from_chars reads less or nothing.
template <class T> std::optional<T> whole(std::string_view text, auto... format) {
    T value{};
    const auto *end = text.data() + text.size();
    const auto [ptr, ec] = std::from_chars(text.data(), end, value, format...);
    if (ec != std::errc{} || ptr != end) {
        return std::nullopt;
    }
    return value;
}

namespace detail {

inline constexpr std::string_view kHexPrefix = "0x";
inline constexpr char kKindSeparator = ':';
inline constexpr char kFractionBar = '/';
inline constexpr char kPartSeparator = ',';
inline constexpr char kImaginaryUnit = 'i';
inline constexpr char kPythonImaginaryUnit = 'j';
inline constexpr std::size_t kNumberChars = 64;
// the 52 mantissa bits, as float.hex writes them
inline constexpr int kMantissaHexDigits = 13;
// repr writes a double in fixed notation for these decimal exponents, otherwise scientific
inline constexpr int kReprFixedFrom = -4;
inline constexpr int kReprScientificFrom = 16;

/// The decimal or the 0x hexadecimal form; from_chars reads hex only without its prefix.
inline std::optional<double> read_double(std::string_view text) {
    const bool negative = text.starts_with('-');
    const std::string_view body = negative ? text.substr(1) : text;
    if (!body.starts_with(kHexPrefix)) {
        return whole<double>(text);
    }
    const std::string_view digits = body.substr(kHexPrefix.size());
    // from_chars takes a sign of its own here, which would make -0x-1p0 read as 1
    const auto magnitude =
        digits.starts_with('-') ? std::nullopt : whole<double>(digits, std::chars_format::hex);
    if (!magnitude) {
        return std::nullopt;
    }
    return negative ? -*magnitude : *magnitude;
}

inline std::optional<BigReal> read_big(std::string_view text) {
    try {
        return BigReal(std::string(text));
    } catch (const std::runtime_error &) {
        // Boost rejects text that is not a number this way
        return std::nullopt;
    } catch (const std::invalid_argument &) {
        // and an empty one, or a cut exponent (big:, big:1.5e), through std::stol
        return std::nullopt;
    }
}

inline std::optional<Value> int_operand(std::string_view text) {
    const auto value = whole<std::int64_t>(text);
    return value ? std::optional<Value>{*value} : std::nullopt;
}

inline std::optional<Value> double_operand(std::string_view text) {
    const auto value = read_double(text);
    return value ? std::optional<Value>{*value} : std::nullopt;
}

inline std::optional<Value> rational_operand(std::string_view text) {
    const auto bar = text.find(kFractionBar);
    if (bar == std::string_view::npos) {
        return std::nullopt;
    }
    const auto num = whole<std::int64_t>(text.substr(0, bar));
    const auto den = whole<std::int64_t>(text.substr(bar + 1));
    constexpr auto kMin = std::numeric_limits<std::int64_t>::min();
    // boost::rational negates both to put the sign on top, which traps on INT64_MIN
    if (!num || !den || *den == 0 || *den == kMin || (*num == kMin && *den < 0)) {
        return std::nullopt;
    }
    return Value{Rational(*num, *den)};
}

inline std::optional<Value> big_operand(std::string_view text) {
    const auto value = read_big(text);
    return value ? std::optional<Value>{*value} : std::nullopt;
}

inline std::optional<Value> complex_operand(std::string_view text) {
    const auto comma = text.find(kPartSeparator);
    if (comma == std::string_view::npos) {
        return std::nullopt;
    }
    const auto re = read_double(text.substr(0, comma));
    const auto im = read_double(text.substr(comma + 1));
    if (!re || !im) {
        return std::nullopt;
    }
    return Value{Complex(*re, *im)};
}

/// Where the imaginary part starts in decimal_text's RE+IMi: the last sign that is not
/// an exponent's.
inline std::size_t imaginary_start(std::string_view body) {
    for (std::size_t i = body.size(); i-- > 1;) {
        const char prev = body[i - 1];
        if ((body[i] == '+' || body[i] == '-') && prev != 'e' && prev != 'E') {
            return i;
        }
    }
    return 0;
}

/// decimal_text's BigComplex form (value.hpp): RE+IMi, IMi, or RE.
inline std::optional<Value> big_complex_operand(std::string_view text) {
    if (!text.ends_with(kImaginaryUnit)) {
        const auto re = read_big(text);
        return re ? std::optional<Value>{to_big_complex(*re)} : std::nullopt;
    }
    const std::string_view body = text.substr(0, text.size() - 1);
    const std::size_t split = imaginary_start(body);
    const auto re = split == 0 ? std::optional<BigReal>{0} : read_big(body.substr(0, split));
    const auto im = read_big(body.substr(split));
    if (!re || !im) {
        return std::nullopt;
    }
    return Value{BigComplex(
        tcalc::detail::BigComplexComponent(*re), tcalc::detail::BigComplexComponent(*im))};
}

struct OperandKind {
    std::string_view prefix;
    std::optional<Value> (*read)(std::string_view);
};

// The prefixes of OperandKind in scripts/probes/rows.py; list: has no reader here
inline constexpr std::array kOperandKinds{
    OperandKind{"int", int_operand},
    OperandKind{"dbl", double_operand},
    OperandKind{"rat", rational_operand},
    OperandKind{"big", big_operand},
    OperandKind{"cx", complex_operand},
    OperandKind{"bigcx", big_complex_operand},
};

inline std::string prefixes() {
    std::string text;
    for (const auto &kind : kOperandKinds) {
        text += (text.empty() ? "" : ", ") + std::string(kind.prefix) + kKindSeparator;
    }
    return text;
}

inline std::string shortest_in(double d, std::chars_format format) {
    std::array<char, kNumberChars> buf{};
    const auto [ptr, ec] = std::to_chars(buf.begin(), buf.end(), d, format);
    return {buf.begin(), ptr};
}

/// float.hex's form, so a Python row and a native row of one double have one input: every
/// mantissa digit, 0x after the sign, zero as 0x0.0p+0, and inf and nan with no prefix.
inline std::string hex(double d) {
    if (d == 0.0) {
        return std::signbit(d) ? "-0x0.0p+0" : "0x0.0p+0";
    }
    std::array<char, kNumberChars> buf{};
    const auto [ptr, ec] =
        std::to_chars(buf.begin(), buf.end(), d, std::chars_format::hex, kMantissaHexDigits);
    std::string text(buf.begin(), ptr);
    if (std::isfinite(d)) {
        text.insert(std::signbit(d) ? 1 : 0, kHexPrefix);
    }
    return text;
}

inline std::string fraction(const Rational &r) {
    return std::to_string(r.numerator()) + kFractionBar + std::to_string(r.denominator());
}

/// Python's repr of a float: the shortest digits, fixed between 1e-4 and 1e16, and a
/// point added to a whole number unless it is a part of a complex.
inline std::string python_float(double d, bool point) {
    const std::string scientific = shortest_in(d, std::chars_format::scientific);
    if (!std::isfinite(d)) {
        return scientific;
    }
    std::string_view exponent = std::string_view(scientific).substr(scientific.find('e') + 1);
    if (exponent.starts_with('+')) {
        exponent.remove_prefix(1);
    }
    const int power = whole<int>(exponent).value_or(0);
    if (power < kReprFixedFrom || power >= kReprScientificFrom) {
        return scientific;
    }
    std::string fixed = shortest_in(d, std::chars_format::fixed);
    if (point && fixed.find('.') == std::string::npos) {
        fixed += ".0";
    }
    return fixed;
}

/// Python's complex repr: no parentheses and no real part when the real part is +0.
inline std::string python_complex(const Complex &c) {
    const std::string im = python_float(c.imag(), false) + kPythonImaginaryUnit;
    if (c.real() == 0.0 && !std::signbit(c.real())) {
        return im;
    }
    const std::string sign = std::signbit(c.imag()) ? "" : "+";
    return "(" + python_float(c.real(), false) + sign + im + ")";
}

} // namespace detail

/// A typed operand, KIND:TEXT, in the forms the Python probes write it.
inline Value parse_operand(std::string_view text) {
    const auto colon = text.find(detail::kKindSeparator);
    const std::string_view prefix = text.substr(0, colon);
    const auto *kind =
        std::ranges::find(detail::kOperandKinds, prefix, &detail::OperandKind::prefix);
    if (colon == std::string_view::npos || kind == detail::kOperandKinds.end()) {
        throw ProbeError(
            "operand '" + std::string(text) + "' has no kind; the kinds are " + detail::prefixes());
    }
    auto value = kind->read(text.substr(colon + 1));
    if (!value) {
        throw ProbeError(
            "operand '" + std::string(text) + "' does not read as " + std::string(prefix) +
            detail::kKindSeparator);
    }
    return std::move(*value);
}

struct ArmNames {
    // the Python type name, as the e2e tables write it
    std::string_view type;
    // the operand prefix of rows.py's OperandKind
    std::string_view prefix;
};

inline ArmNames arm_names(const Value &v) {
    return std::visit(
        Overloads{
            [](std::int64_t) { return ArmNames{"int", "int"}; },
            [](double) { return ArmNames{"float", "dbl"}; },
            [](const Complex &) { return ArmNames{"complex", "cx"}; },
            [](const BigReal &) { return ArmNames{"BigReal", "big"}; },
            [](const BigComplex &) { return ArmNames{"BigComplex", "bigcx"}; },
            [](const Rational &) { return ArmNames{"Rational", "rat"}; },
            [](const Collection &) { return ArmNames{"Collection", "list"}; },
        },
        v);
}

inline std::string type_name(const Value &v) {
    return std::string(arm_names(v).type);
}

inline std::string collection_text(
    const Collection &c, std::string (*item_text)(const Value &), std::string_view separator) {
    const auto [open, close] = brackets(c.kind);
    std::string text(1, open);
    for (std::size_t i = 0; i < c.items().size(); ++i) {
        text += (i == 0 ? "" : std::string(separator)) + item_text(to_value(c.items()[i]));
    }
    return text + close;
}

/// The value as it is held, so that reading the text back gives the same value.
inline std::string exact_text(const Value &v) {
    return std::visit(
        Overloads{
            [](std::int64_t i) { return std::to_string(i); },
            [](double d) { return detail::hex(d); },
            [](const Complex &c) {
                return detail::hex(c.real()) + detail::kPartSeparator + detail::hex(c.imag());
            },
            [](const BigReal &b) { return decimal_text(b, 0); },
            [](const BigComplex &c) { return decimal_text(c, 0); },
            [](const Rational &r) { return detail::fraction(r); },
            // no space, so the list stays one operand word
            [](const Collection &c) { return collection_text(c, exact_text, ","); },
        },
        v);
}

/// The value as rows.py's value_text writes it: a double as repr, a BigReal at its held digits.
inline std::string value_text(const Value &v) {
    return std::visit(
        Overloads{
            [](std::int64_t i) { return std::to_string(i); },
            [](double d) { return detail::python_float(d, true); },
            [](const Complex &c) { return detail::python_complex(c); },
            [](const BigReal &b) { return decimal_text(b, 0); },
            [](const BigComplex &c) { return decimal_text(c, 0); },
            [](const Rational &r) { return detail::fraction(r); },
            [](const Collection &c) { return collection_text(c, value_text, ", "); },
        },
        v);
}

/// The operand form scripts/probes/rows.py's operand_input writes: pasteable as arguments.
inline std::string operand_text(const Value &v) {
    return std::string(arm_names(v).prefix) + detail::kKindSeparator + exact_text(v);
}

struct Row {
    std::string input, layer, type, value;
    // by column name, in the order they print after the four fixed ones
    std::vector<std::pair<std::string, std::string>> extra;
};

/// Characters, not bytes, as Python counts them: ⌄ is one column and three UTF-8 bytes.
inline std::size_t columns(std::string_view text) {
    constexpr unsigned kContinuationMask = 0xC0U;
    constexpr unsigned kContinuation = 0x80U;
    return static_cast<std::size_t>(std::ranges::count_if(text, [](char c) {
        return (static_cast<unsigned char>(c) & kContinuationMask) != kContinuation;
    }));
}

/// The aligned table of scripts/probes/rows.py's format_rows, which parse_rows reads.
inline void print_rows(std::ostream &out, std::span<const Row> rows) {
    std::vector<std::string> header{"input", "layer", "type", "value"};
    const std::size_t fixed = header.size();
    for (const auto &row : rows) {
        for (const auto &[name, _] : row.extra) {
            if (std::ranges::find(header, name) == header.end()) {
                header.push_back(name);
            }
        }
    }
    std::vector<std::vector<std::string>> table{header};
    for (const auto &row : rows) {
        std::vector<std::string> cells{row.input, row.layer, row.type, row.value};
        for (std::size_t i = fixed; i < header.size(); ++i) {
            const auto cell = std::ranges::find(
                row.extra, header[i], &std::pair<std::string, std::string>::first);
            cells.push_back(cell == row.extra.end() ? "" : cell->second);
        }
        table.push_back(std::move(cells));
    }
    std::vector<std::size_t> widths(header.size());
    for (const auto &line : table) {
        for (std::size_t i = 0; i < line.size(); ++i) {
            widths[i] = std::max(widths[i], columns(line[i]));
        }
    }
    for (const auto &line : table) {
        std::string text;
        for (std::size_t i = 0; i < line.size(); ++i) {
            text += (i == 0 ? "" : "  ") + line[i] + std::string(widths[i] - columns(line[i]), ' ');
        }
        out << text.substr(0, text.find_last_not_of(' ') + 1) << '\n';
    }
}

using Defs = std::map<std::string, std::string, std::less<>>;

inline constexpr char kDefMarker = '@';

/// @NAME for the typed operand text it was defined as; any other operand as it is.
inline std::string substitute(std::string_view operand, const Defs &defs) {
    if (!operand.starts_with(kDefMarker)) {
        return std::string(operand);
    }
    const auto found = defs.find(operand.substr(1));
    if (found == defs.end()) {
        throw ProbeError(
            "'" + std::string(operand) + "' is not defined; define it with --def " +
            std::string(operand.substr(1)) + "=KIND:VALUE");
    }
    return found->second;
}

/// The median of runs calls of fn, in nanoseconds of the steady clock.
template <class Fn> double median_ns(Fn &&fn, int runs) {
    std::vector<double> times;
    times.reserve(static_cast<std::size_t>(runs));
    for (int i = 0; i < runs; ++i) {
        const auto start = std::chrono::steady_clock::now();
        // calc_core is a separate library, so the call is not removed though its value is
        static_cast<void>(fn());
        const auto end = std::chrono::steady_clock::now();
        times.push_back(std::chrono::duration<double, std::nano>(end - start).count());
    }
    const auto middle = times.begin() + static_cast<std::ptrdiff_t>(times.size() / 2);
    std::ranges::nth_element(times, middle);
    return *middle;
}

} // namespace tcalc::probe
