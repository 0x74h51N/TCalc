/*
 *
 *
 * TCalc is a native-powered scientific desktop calculator designed
 *  for high-performance, precision, and a superior user experience.
 *  Copyright (C) 2025 Tahsin Önemli
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#pragma once

#include <complex>
#include <cstdint>
#include <optional>
#include <span>
#include "calc/pub/errors.hpp"
#include "collection/collection.hpp"
#include "types.hpp"

using tcalc::Collection;
using tcalc::CollectionItem;

class Calculator {
  public:
    using Complex = ::Complex;

    enum class AngleUnit : std::uint8_t { DEG, RAD, GRAD };

    Calculator() = default;

    // Real ops
    double add(double a, double b) const { return a + b; }
    double sub(double a, double b) const { return a - b; }
    double mul(double a, double b) const { return a * b; }
    double div(double a, double b) const;
    long long intdiv(double a, double b) const;
    double mod(double a, double b) const;
    double pow(double a, long long b) const;
    double pow(double a, double b) const;
    double sqrt(double a) const;
    double cbrt(double a) const;
    double root(double a, double b) const;
    double trunc(double a) const;
    double floor(double a) const;
    double ceil(double a) const;

    // BigReal ops (real-only, extended range)
    BigReal add(const BigReal &a, const BigReal &b) const { return a + b; }
    BigReal sub(const BigReal &a, const BigReal &b) const { return a - b; }
    BigReal mul(const BigReal &a, const BigReal &b) const { return a * b; }
    BigReal div(const BigReal &a, const BigReal &b) const;
    BigReal pow(const BigReal &a, const BigReal &b) const;
    BigReal intdiv(const BigReal &a, const BigReal &b) const;
    BigReal mod(const BigReal &a, const BigReal &b) const;
    BigReal sqrt(const BigReal &a) const;
    BigReal log(const BigReal &a) const;
    BigReal ln(const BigReal &a) const;
    BigReal root(const BigReal &a, const BigReal &b) const;
    BigReal trunc(const BigReal &a) const;
    BigReal floor(const BigReal &a) const;
    BigReal ceil(const BigReal &a) const;

    // Complex ops
    Complex add(Complex a, Complex b) const { return a + b; }
    Complex sub(Complex a, Complex b) const { return a - b; }
    Complex mul(Complex a, Complex b) const { return a * b; }
    Complex div(Complex a, Complex b) const;
    Complex pow(Complex a, Complex b) const;
    Complex sqrt(Complex a) const;
    Complex root(Complex a, Complex b) const;

    // Rational ops
    Rational add(const Rational &a, const Rational &b) const;
    Rational sub(const Rational &a, const Rational &b) const;
    Rational mul(const Rational &a, const Rational &b) const;
    Rational div(const Rational &a, const Rational &b) const;
    Rational pow(const Rational &base, const Rational &exp) const;
    Rational sqrt(const Rational &a) const;
    Rational cbrt(const Rational &a) const;
    Rational root(const Rational &a, const Rational &b) const;

    /// Which trigonometric function an exact half-turn lookup is for.
    enum class TrigFn : std::uint8_t { Sin, Cos, Tan };

    /// The argument as an exact number of half turns, so the angle is pi*t radians, or nullopt
    /// when it cannot be one. Kept here rather than in eval so the 180 and 200 per half turn
    /// live beside the conversion that already uses them.
    std::optional<Rational> half_turns(const Rational &a, AngleUnit unit) const;

    /// sin/cos/tan of pi*t when that value is rational, nullopt otherwise; raises at a tan pole.
    /// Deliberately not a Calculator arm: an arm can only decline by raising, and declining is
    /// the normal case here, at 1058 ns per throw against 5.7 ns for the sine itself.
    std::optional<Rational> exact_half_turns(TrigFn fn, const Rational &t) const;

    /// sin/cos/tan of pi*t numerically, with t folded into the first quadrant first so only a
    /// small product is formed. For a t that has no exact value but is still known exactly.
    double real_half_turns(TrigFn fn, const Rational &t) const;

    // BigComplex ops
    BigComplex add(const BigComplex &a, const BigComplex &b) const { return a + b; }
    BigComplex sub(const BigComplex &a, const BigComplex &b) const { return a - b; }
    BigComplex mul(const BigComplex &a, const BigComplex &b) const { return a * b; }
    BigComplex div(const BigComplex &a, const BigComplex &b) const;
    BigComplex pow(const BigComplex &a, const BigComplex &b) const;
    BigComplex sqrt(const BigComplex &a) const;
    BigComplex root(const BigComplex &a, const BigComplex &b) const;
    BigComplex log(const BigComplex &a) const;
    BigComplex ln(const BigComplex &a) const;

    // Polar (cis): cos(a) + i*sin(a) using selected angle unit
    Complex polar(double a, AngleUnit unit) const;
    Complex polar(Complex a, AngleUnit unit) const;

    // Trig ops
    double sin(double a, AngleUnit unit) const;
    double cos(double a, AngleUnit unit) const;
    double tan(double a, AngleUnit unit) const;

    Complex sin(Complex a, AngleUnit unit) const;
    Complex cos(Complex a, AngleUnit unit) const;
    Complex tan(Complex a, AngleUnit unit) const;

    BigReal sin(const BigReal &a, AngleUnit unit) const;
    BigReal cos(const BigReal &a, AngleUnit unit) const;
    BigReal tan(const BigReal &a, AngleUnit unit) const;

    BigComplex sin(const BigComplex &a, AngleUnit unit) const;
    BigComplex cos(const BigComplex &a, AngleUnit unit) const;
    BigComplex tan(const BigComplex &a, AngleUnit unit) const;

    // Hyperbolic ops
    double sinh(double a) const;
    double cosh(double a) const;
    double tanh(double a) const;

    Complex sinh(Complex a) const;
    Complex cosh(Complex a) const;
    Complex tanh(Complex a) const;

    // Inverse Trig ops
    double asin(double a, AngleUnit unit) const;
    double acos(double a, AngleUnit unit) const;
    double atan(double a, AngleUnit unit) const;

    Complex asin(Complex a, AngleUnit unit) const;
    Complex acos(Complex a, AngleUnit unit) const;
    Complex atan(Complex a, AngleUnit unit) const;

    // Inverse Trig Hyperbolic ops
    double asinh(double a) const;
    double acosh(double a) const;
    double atanh(double a) const;

    Complex asinh(Complex a) const;
    Complex acosh(Complex a) const;
    Complex atanh(Complex a) const;

    // Log ops
    double log(double a) const;
    double ln(double a) const;

    Complex log(Complex a) const;
    Complex ln(Complex a) const;

    // GCD / LCM (variadic fold over a list of integers)
    CollectionItem gcd(const Collection &a) const;
    CollectionItem lcm(const Collection &a) const;

    // Factorial
    double fact(double a) const;
    double gamma(double a) const;

    BigReal fact(const BigReal &a) const;
    BigReal gamma(const BigReal &a) const;
    // Permute/Choose
    BigReal permute(long long a, long long b) const;
    BigReal choose(long long a, long long b) const;

    // Collection reductions
    CollectionItem mean(const Collection &a) const;
    CollectionItem min(const Collection &a) const;
    CollectionItem max(const Collection &a) const;
    CollectionItem median(const Collection &a) const;
    CollectionItem sum(const Collection &a) const;
    CollectionItem variance(const Collection &a) const;
    CollectionItem variance_pop(const Collection &a) const;
    CollectionItem stddev(const Collection &a) const;
    CollectionItem stddev_pop(const Collection &a) const;

  private:
    template <typename T> CollectionItem mean_scalar(std::span<const CollectionItem> items) const;
    template <typename T, bool IsMax>
    CollectionItem minmax_scalar(std::span<const CollectionItem> items) const;
    template <typename T> CollectionItem median_scalar(std::span<const CollectionItem> items) const;
    template <typename T> CollectionItem sum_scalar(std::span<const CollectionItem> items) const;
    template <typename T, bool Sample>
    CollectionItem variance_scalar(std::span<const CollectionItem> items) const;
    template <typename T, bool Sample>
    CollectionItem stddev_scalar(std::span<const CollectionItem> items) const;
};
