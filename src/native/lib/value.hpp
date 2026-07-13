/*
 * TCalc - Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <cstdint>
#include <optional>
#include <variant>

#include "calc/pub/errors.hpp"
#include "collection/collection.hpp"
#include "types.hpp"

namespace tcalc {

/// Runtime value: every type an expression can evaluate to.
using Value =
    std::variant<std::int64_t, double, Complex, BigReal, BigComplex, Rational, Collection>;

/// Variant arms, in variant index order.
enum class Arm : std::uint8_t { Int64, Double, Cx, Big, BigCx, Rat, Coll, Count };

/// Arm must name the variant's own index, since arm_of() reads one as the other.
template <Arm A, class T>
inline constexpr bool kArmIs =
    std::is_same_v<std::variant_alternative_t<static_cast<std::size_t>(A), Value>, T>;

static_assert(kArmIs<Arm::Int64, std::int64_t>);
static_assert(kArmIs<Arm::Double, double>);
static_assert(kArmIs<Arm::Cx, Complex>);
static_assert(kArmIs<Arm::Big, BigReal>);
static_assert(kArmIs<Arm::BigCx, BigComplex>);
static_assert(kArmIs<Arm::Rat, Rational>);
static_assert(kArmIs<Arm::Coll, Collection>);
static_assert(std::variant_size_v<Value> == static_cast<std::size_t>(Arm::Count));

using ArmMask = std::uint8_t;

constexpr ArmMask arm_bit(Arm a) {
    return static_cast<ArmMask>(1U << static_cast<unsigned>(a));
}
constexpr Arm arm_of(const Value &v) {
    return static_cast<Arm>(v.index());
}
constexpr bool has_arm(ArmMask m, Arm a) {
    return (m & arm_bit(a)) != 0;
}

/// The real-numeric arms. The lattice only widens these; a complex or a collection
/// argument is routed elsewhere or rejected.
inline bool is_num_or_big(const Value &v) {
    switch (arm_of(v)) {
    case Arm::Int64:
    case Arm::Double:
    case Arm::Big:
    case Arm::Rat:
        return true;
    default:
        return false;
    }
}

/// An exact fraction, if the value is one. A double is never lifted: 0.1 has no exact
/// rational form, and pretending otherwise would fake precision.
inline std::optional<Rational> to_rational(const Value &v) {
    if (const auto *r = std::get_if<Rational>(&v))
        return *r;
    if (const auto *i = std::get_if<std::int64_t>(&v))
        return Rational(*i);
    return std::nullopt;
}

/// Leave the exact domain: an integral fraction becomes an integer, any other becomes
/// a double. Non-rationals pass through.
inline Value rational_downcast(const Value &v) {
    if (const auto *r = std::get_if<Rational>(&v)) {
        if (r->denominator() == 1)
            return Value{r->numerator()};
        return Value{r->to_double()};
    }
    return v;
}

/// Narrow to double. One overload per arm that has a real value; the complex arms and
/// Collection have none, so narrowing one is a compile error rather than a silent 0.0.
inline double to_double(double d) {
    return d;
}
inline double to_double(std::int64_t i) {
    return static_cast<double>(i);
}
inline double to_double(const Rational &r) {
    return r.to_double();
}
inline double to_double(const BigReal &b) {
    return b.convert_to<double>();
}

/// Widen to BigReal. int64 converts exactly through boost's integral ctor; routing it
/// through double would corrupt anything past 2^53. A Rational loses exactness here,
/// since BigReal is not a fraction type. The complex arms have no BigReal form.
inline BigReal to_big(const BigReal &b) {
    return b;
}
inline BigReal to_big(const Rational &r) {
    return BigReal(r.to_double());
}
inline BigReal to_big(std::int64_t i) {
    return BigReal(i);
}
inline BigReal to_big(double d) {
    return BigReal(d);
}

/// Widen to Complex. The real arms embed with a zero imaginary part. BigReal has no
/// overload on purpose: pairing it with a complex must join upward to BigComplex, never
/// narrow the BigReal into a double-precision complex.
inline Complex to_complex(const Complex &c) {
    return c;
}
inline Complex to_complex(std::int64_t i) {
    return Complex(static_cast<double>(i), 0.0);
}
inline Complex to_complex(double d) {
    return Complex(d, 0.0);
}
inline Complex to_complex(const Rational &r) {
    return Complex(r.to_double(), 0.0);
}

namespace detail {
using BigComplexComponent = boost::multiprecision::cpp_bin_float_50;

// BigReal's backend does not interconvert with BigComplex's component type, so the
// real part is wrapped through it explicitly.
inline BigComplex real_to_big_complex(const BigReal &b) {
    return BigComplex(BigComplexComponent(b), BigComplexComponent(0));
}
} // namespace detail

/// Widen to BigComplex, the top of the lattice: every numeric arm converts here.
inline BigComplex to_big_complex(const BigComplex &bc) {
    return bc;
}
inline BigComplex to_big_complex(const Complex &c) {
    return BigComplex(c.real(), c.imag());
}
inline BigComplex to_big_complex(const BigReal &b) {
    return detail::real_to_big_complex(b);
}
inline BigComplex to_big_complex(std::int64_t i) {
    return detail::real_to_big_complex(to_big(i));
}
inline BigComplex to_big_complex(double d) {
    return detail::real_to_big_complex(to_big(d));
}
inline BigComplex to_big_complex(const Rational &r) {
    return detail::real_to_big_complex(to_big(r));
}

/// Wrap a kernel's result into a Value. The reducers return CollectionItem, which is a
/// different variant, so it is unwrapped here.
inline Value to_value(std::int64_t v) {
    return Value{v};
}
/// intdiv returns `long long`, a distinct type from int64_t under LP64. Without this
/// overload the call is ambiguous against the double one.
inline Value to_value(long long v) {
    return Value{static_cast<std::int64_t>(v)};
}
inline Value to_value(double v) {
    return Value{v};
}
inline Value to_value(const Complex &v) {
    return Value{v};
}
inline Value to_value(const BigReal &v) {
    return Value{v};
}
inline Value to_value(const BigComplex &v) {
    return Value{v};
}
inline Value to_value(const Rational &v) {
    return Value{v};
}
inline Value to_value(const Collection &v) {
    return Value{v};
}
inline Value to_value(const Value &v) {
    return v;
}

inline Value to_value(const CollectionItem &it) {
    return std::visit(
        [](const auto &x) -> Value {
            using T = std::decay_t<decltype(x)>;
            if constexpr (std::is_same_v<T, std::shared_ptr<const Collection>>)
                return Value{*x};
            else
                return Value{x};
        },
        it);
}

} // namespace tcalc
