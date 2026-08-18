/*
 *
 *  TCalc is a native-powered scientific desktop calculator designed
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

#include <cmath>
#include "calc/internal/helpers.hpp"
#include "calc/pub/error_messages.hpp"
#include "eval/internal/closed_forms.hpp"
#include "eval/internal/scalar.hpp"
#include "eval/pub/eval.hpp"
#include "eval/pub/literal.hpp"
#include "eval/pub/varstore.hpp"
#include "internal/test_helpers.hpp"
#include "internal/token_factories.hpp"
#include "value.hpp"

using tcalc::Arm;
using tcalc::arm_of;
using tcalc::CollectionKind;
using tcalc::is_num_or_big;
using tcalc::rational_downcast;
using tcalc::to_big;
using tcalc::to_big_complex;
using tcalc::to_complex;
using tcalc::to_double;
using tcalc::to_rational;
using tcalc::Value;
using tcalc::eval::apply;
using tcalc::eval::coerce;
using tcalc::eval::eval_row;
using tcalc::eval::evaluate;
using tcalc::eval::literal_value;
using tcalc::eval::promote_complex;
using tcalc::eval::session_vars;
using tcalc::eval::VarStore;
using tcalc::ops::OpId;

namespace {

/// Generic test-row template: id label, input value, expected value. Mirrors
/// test_parser.cpp's local Case so literal_value gets a row table instead of a
/// wall of TEST_CASE blocks.
template <typename InputT, typename ExpectedT> struct Case {
    const char *id;
    InputT input;
    ExpectedT expected;
};

/// Case row for literal_value: literal text -> the value it denotes.
using LitCase = Case<const char *, Value>;
/// Case row for literal_value where only the resulting arm is asserted.
using ArmCase = Case<const char *, Arm>;
/// Case row for the evaluator: source text -> the value it evaluates to.
using EvalCase = Case<const char *, Value>;
/// Operand pair and operation for the symbolic scalar table: `op` is one of * / + -.
struct ScalarOps {
    tcalc::eval::Scalar lhs;
    tcalc::eval::Scalar rhs;
    char op;
};
/// Case row for the scalar algebra: an operation on two scalars -> the scalar it must equal.
using ScalarCase = Case<ScalarOps, tcalc::eval::Scalar>;
/// Case row for a body whose value is irrational: source text -> the real it must land near.
using NearCase = Case<const char *, double>;
/// Case row for a rejected expression: source text -> nothing, it must throw.
using RejectCase = Case<const char *, std::monostate>;
/// Case row for a rejected expression whose message text is part of the contract.
using MsgCase = Case<const char *, const char *>;
/// Source text paired with the angle unit to evaluate it under (EvalCase always uses the
/// default radians, so a degree/grad row needs this instead).
struct SrcUnit {
    const char *src;
    Calculator::AngleUnit unit;
};
/// Case row for the evaluator under an explicit angle unit: source text -> the value it
/// evaluates to.
using UnitEvalCase = Case<SrcUnit, Value>;
/// Case row for an evaluation under an explicit angle unit that must throw.
using UnitRejectCase = Case<SrcUnit, std::monostate>;
/// Case row for an evaluation under an explicit angle unit where only the resulting arm is
/// asserted.
using UnitArmCase = Case<SrcUnit, Arm>;
/// Case row for normalize: input tokens -> normalized tokens.
using NormCase = Case<std::vector<tcalc::parser::Token>, std::vector<tcalc::parser::Token>>;
/// Case row for shunting_yard: infix tokens -> RPN tokens.
using ShuntCase = Case<std::vector<tcalc::parser::Token>, std::vector<tcalc::parser::Token>>;

using tcalc::parser::OpToken;
using tcalc::parser::Token;
using tcalc::parser::TokenKind;
using namespace tcalc::test_tokens;

constexpr auto kRad = Calculator::AngleUnit::RAD;

/// Evaluate a source string the way the application does: tokenize, then eval_row.
Value eval_text(const Calculator &c, const char *src, Calculator::AngleUnit u = kRad) {
    return eval_row(tcalc::parser::tokenize(src).tokens, c, u);
}

/// A whole row, assignment peel included: tokenize, then evaluate.
Value eval_source(const Calculator &c, const char *src, Calculator::AngleUnit u = kRad) {
    return evaluate(tcalc::parser::tokenize(src), c, u);
}

} // namespace

void unit_eval(TestContext &ctx) {
    TEST_CASE(ctx, "arm_of :: matches variant order", {
        EXPECT_EQ(ctx, arm_of(Value{std::int64_t{3}}), Arm::Int64);
        EXPECT_EQ(ctx, arm_of(Value{2.5}), Arm::Double);
        EXPECT_EQ(ctx, arm_of(Value{Rational(1, 2)}), Arm::Rat);
    });

    TEST_CASE(ctx, "to_rational :: int64 lifts, double never does", {
        const auto lifted = to_rational(Value{std::int64_t{5}});
        EXPECT_EQ(ctx, lifted.has_value(), true);
        EXPECT_EQ(ctx, lifted->numerator(), 5LL);
        EXPECT_EQ(ctx, to_rational(Value{2.5}).has_value(), false);
    });

    TEST_CASE(ctx, "rational_downcast :: integral -> int64, fractional -> double", {
        const Value i = rational_downcast(Value{Rational(6, 3)});
        EXPECT_EQ(ctx, arm_of(i), Arm::Int64);
        EXPECT_EQ(ctx, std::get<std::int64_t>(i), 2LL);

        const Value f = rational_downcast(Value{Rational(1, 2)});
        EXPECT_EQ(ctx, arm_of(f), Arm::Double);
        EXPECT_EQ(ctx, std::get<double>(f), 0.5);
    });

    TEST_CASE(ctx, "to_value :: unwraps a CollectionItem", {
        const Value v = tcalc::to_value(CollectionItem{2.5});
        EXPECT_EQ(ctx, arm_of(v), Arm::Double);
        EXPECT_EQ(ctx, std::get<double>(v), 2.5);
    });

    TEST_CASE(ctx, "to_double :: one overload per arm", {
        EXPECT_EQ(ctx, to_double(2.5), 2.5);
        EXPECT_EQ(ctx, to_double(std::int64_t{4}), 4.0);
        EXPECT_EQ(ctx, to_double(Rational(1, 4)), 0.25);
        EXPECT_EQ(ctx, to_double(BigReal("0.5")), 0.5);
    });

    TEST_CASE(ctx, "to_big :: one overload per arm", {
        EXPECT_EQ(ctx, to_big(BigReal("1.5")), BigReal("1.5"));
        EXPECT_EQ(ctx, to_big(Rational(1, 2)), BigReal("0.5"));
        // Exact: must not round-trip through double, which would give ...992.
        EXPECT_EQ(ctx, to_big(std::int64_t{9007199254740993}), BigReal("9007199254740993"));
        EXPECT_EQ(ctx, to_big(2.5), BigReal("2.5"));
    });

    TEST_CASE(ctx, "to_complex :: one overload per arm", {
        EXPECT_EQ(ctx, to_complex(Complex(1.0, 2.0)), Complex(1.0, 2.0));
        EXPECT_EQ(ctx, to_complex(std::int64_t{3}), Complex(3.0, 0.0));
        EXPECT_EQ(ctx, to_complex(2.5), Complex(2.5, 0.0));
        EXPECT_EQ(ctx, to_complex(Rational(1, 2)), Complex(0.5, 0.0));
    });

    TEST_CASE(ctx, "to_big_complex :: one overload per arm", {
        const BigComplex bc(1.0, 2.0);
        EXPECT_EQ(ctx, to_big_complex(bc), bc);
        EXPECT_EQ(ctx, to_big_complex(Complex(1.0, 2.0)), BigComplex(1.0, 2.0));
        EXPECT_EQ(ctx, to_big_complex(BigReal("1.5")), BigComplex(1.5, 0.0));
        EXPECT_EQ(ctx, to_big_complex(std::int64_t{3}), BigComplex(3.0, 0.0));
        EXPECT_EQ(ctx, to_big_complex(2.5), BigComplex(2.5, 0.0));
        EXPECT_EQ(ctx, to_big_complex(Rational(1, 2)), BigComplex(0.5, 0.0));
    });

    TEST_CASE(ctx, "is_num_or_big :: true for int64/double/BigReal/Rational only", {
        EXPECT_EQ(ctx, is_num_or_big(Value{std::int64_t{3}}), true);
        EXPECT_EQ(ctx, is_num_or_big(Value{2.5}), true);
        EXPECT_EQ(ctx, is_num_or_big(Value{BigReal("1.5")}), true);
        EXPECT_EQ(ctx, is_num_or_big(Value{Rational(1, 2)}), true);
        EXPECT_EQ(ctx, is_num_or_big(Value{Complex(1.0, 2.0)}), false);
        EXPECT_EQ(ctx, is_num_or_big(Value{BigComplex(1.0, 2.0)}), false);
        const tcalc::Collection coll(
            tcalc::CollectionKind::List, {CollectionItem{std::int64_t{1}}});
        EXPECT_EQ(ctx, is_num_or_big(Value{coll}), false);
    });

    TEST_CASE(ctx, "coerce :: ints lift to Rational when the op has that arm", {
        const auto out = coerce(OpId::Add, {Value{std::int64_t{2}}, Value{std::int64_t{3}}});
        EXPECT_EQ(ctx, arm_of(out[0]), Arm::Rat);
    });

    // An op with a Big arm lifts its other argument.
    TEST_CASE(ctx, "coerce :: BigReal lifts the other argument", {
        const auto out = coerce(OpId::Add, {Value{BigReal("1")}, Value{std::int64_t{2}}});
        EXPECT_EQ(ctx, arm_of(out[0]), Arm::Big);
        EXPECT_EQ(ctx, arm_of(out[1]), Arm::Big);
    });

    // An op with no Big arm: a BigReal is rejected, never demoted.
    TEST_CASE(ctx, "coerce :: BigReal into an op with no Big arm is an error", {
        EXPECT_THROWS(ctx, coerce(OpId::Cbrt, {Value{BigReal("8")}}));
    });

    // A BigReal paired with a Complex joins upward.
    TEST_CASE(ctx, "coerce :: BigReal + Complex -> BigComplex", {
        const auto out = coerce(OpId::Add, {Value{BigReal("1")}, Value{Complex(2.0, 0.0)}});
        EXPECT_EQ(ctx, arm_of(out[0]), Arm::BigCx);
        EXPECT_EQ(ctx, arm_of(out[1]), Arm::BigCx);
    });

    // A complex operand lifts the other one.
    TEST_CASE(ctx, "coerce :: a Complex argument lifts the other", {
        const auto out = coerce(OpId::Add, {Value{std::int64_t{1}}, Value{Complex(2.0, 0.0)}});
        EXPECT_EQ(ctx, arm_of(out[0]), Arm::Cx);
        EXPECT_EQ(ctx, arm_of(out[1]), Arm::Cx);
    });

    // An existing BigReal is kept, not narrowed.
    TEST_CASE(ctx, "coerce :: pow keeps an existing BigReal", {
        const auto out = coerce(OpId::Pow, {Value{BigReal("2")}, Value{std::int64_t{308}}});
        EXPECT_EQ(ctx, arm_of(out[0]), Arm::Big);
        EXPECT_EQ(ctx, arm_of(out[1]), Arm::Big);
    });

    // An op with no Rational arm downcasts, and then has to land on an arm the op really
    // has. Fact's only real arm is Double, so the integer goes on to double rather than
    // reaching a kernel with no integer overload to take it.
    TEST_CASE(ctx, "coerce :: fact of a rational lands on the Double arm", {
        const auto out = coerce(OpId::Fact, {Value{Rational(5)}});
        EXPECT_EQ(ctx, arm_of(out[0]), Arm::Double);
    });

    TEST_CASE(ctx, "coerce :: permute keeps int64; non-integers are an error", {
        const auto out = coerce(OpId::Permute, {Value{std::int64_t{5}}, Value{std::int64_t{3}}});
        EXPECT_EQ(ctx, arm_of(out[0]), Arm::Int64);
        EXPECT_THROWS(ctx, coerce(OpId::Permute, {Value{1.2}, Value{4.4}}));
    });

    TEST_CASE(ctx, "domain :: sqrt(-1) promotes, sqrt(1) does not", {
        std::vector<Value> neg{Value{std::int64_t{-1}}};
        promote_complex(OpId::Sqrt, neg);
        EXPECT_EQ(ctx, arm_of(neg[0]), Arm::Cx);

        std::vector<Value> pos{Value{std::int64_t{1}}};
        promote_complex(OpId::Sqrt, pos);
        EXPECT_EQ(ctx, arm_of(pos[0]), Arm::Int64);
    });

    TEST_CASE(ctx, "domain :: log(-1) promotes, log(1) does not", {
        std::vector<Value> neg{Value{std::int64_t{-1}}};
        promote_complex(OpId::Log, neg);
        EXPECT_EQ(ctx, arm_of(neg[0]), Arm::Cx);

        std::vector<Value> pos{Value{std::int64_t{1}}};
        promote_complex(OpId::Log, pos);
        EXPECT_EQ(ctx, arm_of(pos[0]), Arm::Int64);
    });

    TEST_CASE(ctx, "domain :: root(-1, 2) promotes; the odd degree does not", {
        std::vector<Value> even{Value{std::int64_t{-1}}, Value{std::int64_t{2}}};
        promote_complex(OpId::Root, even);
        EXPECT_EQ(ctx, arm_of(even[0]), Arm::Cx);
        EXPECT_EQ(ctx, arm_of(even[1]), Arm::Int64); // the degree is never promoted

        std::vector<Value> odd{Value{std::int64_t{-8}}, Value{std::int64_t{3}}};
        promote_complex(OpId::Root, odd);
        EXPECT_EQ(ctx, arm_of(odd[0]), Arm::Int64);
    });

    // A BigReal is never domain-checked: reading it as a double could underflow to 0
    // and force a complex op that is not warranted.
    TEST_CASE(ctx, "domain :: a BigReal argument is never domain-checked", {
        std::vector<Value> args{Value{BigReal("-1")}};
        promote_complex(OpId::Sqrt, args);
        EXPECT_EQ(ctx, arm_of(args[0]), Arm::Big);
    });

    TEST_CASE(ctx, "apply :: int + int stays exact", {
        const Calculator c;
        const Value r = apply(
            c,
            OpId::Add,
            {Value{std::int64_t{2}}, Value{std::int64_t{3}}},
            Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<Rational>(r), Rational(5));
    });

    TEST_CASE(ctx, "apply :: 1/3 stays exact", {
        const Calculator c;
        const Value r = apply(
            c,
            OpId::Div,
            {Value{std::int64_t{1}}, Value{std::int64_t{3}}},
            Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<Rational>(r), Rational(1, 3));
    });

    TEST_CASE(ctx, "apply :: sqrt(-1) comes back Complex", {
        const Calculator c;
        const Value r = apply(c, OpId::Sqrt, {Value{std::int64_t{-1}}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<Complex>(r), Complex(0.0, 1.0));
    });

    TEST_CASE(ctx, "apply :: sqrt(4/9) stays exact", {
        const Calculator c;
        const Value r = apply(c, OpId::Sqrt, {Value{Rational(4, 9)}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<Rational>(r), Rational(2, 3));
    });

    TEST_CASE(ctx, "apply :: sqrt(-1/1) leaves the exact arm, then the real domain", {
        const Calculator c;
        const Value r = apply(c, OpId::Sqrt, {Value{Rational(-1)}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<Complex>(r), Complex(0.0, 1.0));
    });

    TEST_CASE(ctx, "apply :: sqrt(-1/4) promotes the downcast double", {
        const Calculator c;
        const Value r = apply(c, OpId::Sqrt, {Value{Rational(-1, 4)}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<Complex>(r), Complex(0.0, 0.5));
    });

    TEST_CASE(ctx, "apply :: sqrt(2) is not exact, so it falls back to double", {
        const Calculator c;
        const Value r = apply(c, OpId::Sqrt, {Value{Rational(2)}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, arm_of(r), Arm::Double);
        EXPECT_TRUE(ctx, approx(std::get<double>(r), 1.4142135623730951));
    });

    TEST_CASE(ctx, "apply :: pow(10, 400) comes back BigReal", {
        const Calculator c;
        const Value r = apply(
            c,
            OpId::Pow,
            {Value{std::int64_t{10}}, Value{std::int64_t{400}}},
            Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, arm_of(r), Arm::Big);
    });

    TEST_CASE(ctx, "apply :: sqr of a rational stays exact", {
        const Calculator c;
        const Value r = apply(c, OpId::Sqr, {Value{Rational(1, 2)}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<Rational>(r), Rational(1, 4));
    });

    TEST_CASE(ctx, "apply :: fact of a rational downcasts to double", {
        const Calculator c;
        const Value r = apply(c, OpId::Fact, {Value{Rational(5)}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<double>(r), 120.0);
    });

    TEST_CASE(ctx, "apply :: sin honours the angle unit", {
        const Calculator c;
        const Value r = apply(c, OpId::Sin, {Value{std::int64_t{90}}}, Calculator::AngleUnit::DEG);
        EXPECT_EQ(ctx, std::get<double>(r), 1.0);
    });

    TEST_CASE(ctx, "apply :: permute of non-integers reports rather than truncating", {
        const Calculator c;
        EXPECT_THROWS(
            ctx, apply(c, OpId::Permute, {Value{1.2}, Value{4.4}}, Calculator::AngleUnit::RAD));
    });

    TEST_CASE(ctx, "apply :: fact of a complex is an error", {
        const Calculator c;
        EXPECT_THROWS(
            ctx, apply(c, OpId::Fact, {Value{Complex(1.0, 2.0)}}, Calculator::AngleUnit::RAD));
    });

    // Required fix #1's own regression tests: mixed int64/double must homogenise to
    // double so dispatch's same-arm requirement does not throw on ordinary arithmetic.
    TEST_CASE(ctx, "apply :: int64 + double homogenises instead of throwing", {
        const Calculator c;
        const Value r =
            apply(c, OpId::Add, {Value{std::int64_t{2}}, Value{3.5}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<double>(r), 5.5);
    });

    TEST_CASE(ctx, "apply :: int64 * double homogenises instead of throwing", {
        const Calculator c;
        const Value r =
            apply(c, OpId::Mul, {Value{std::int64_t{2}}, Value{0.5}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, std::get<double>(r), 1.0);
    });

    // Range promotion: one rule, after dispatch, for every op. IEEE-754 makes inf, a
    // spurious zero and a subnormal exact detectors, so no magnitude estimate is needed.
    TEST_CASE(ctx, "apply :: pow(1e-200, 3) comes back BigReal", {
        const Calculator c;
        const Value r =
            apply(c, OpId::Pow, {Value{1e-200}, Value{3.0}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, arm_of(r), Arm::Big);
    });

    TEST_CASE(ctx, "apply :: mul(1e200, 1e200) comes back BigReal", {
        const Calculator c;
        const Value r =
            apply(c, OpId::Mul, {Value{1e200}, Value{1e200}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, arm_of(r), Arm::Big);
    });

    // Deliberate divergence: mul(1e-200, 1e-200) returns double 0.0 today (underflow
    // silently collapses); the single post-dispatch rule now promotes it instead.
    TEST_CASE(ctx, "apply :: mul(1e-200, 1e-200) comes back BigReal (deliberate divergence)", {
        const Calculator c;
        const Value r =
            apply(c, OpId::Mul, {Value{1e-200}, Value{1e-200}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, arm_of(r), Arm::Big);
    });

    // Deliberate divergence: pow(2, -1075) returns double 0.0 today, with neither
    // operand zero.
    TEST_CASE(ctx, "apply :: pow(2, -1075) comes back BigReal (deliberate divergence)", {
        const Calculator c;
        const Value r =
            apply(c, OpId::Pow, {Value{2.0}, Value{-1075.0}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, arm_of(r), Arm::Big);
    });

    // Deliberate divergence: this lands in the band below 1e-308 where a double is
    // subnormal and has already lost digits.
    TEST_CASE(ctx, "apply :: pow(2, -1030) comes back BigReal (deliberate divergence)", {
        const Calculator c;
        const Value r =
            apply(c, OpId::Pow, {Value{2.0}, Value{-1030.0}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, arm_of(r), Arm::Big);
    });

    // A legitimate zero must never be promoted.
    TEST_CASE(ctx, "apply :: mul(0, 5) stays double 0.0", {
        const Calculator c;
        const Value r = apply(c, OpId::Mul, {Value{0.0}, Value{5.0}}, Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, arm_of(r), Arm::Double);
        EXPECT_EQ(ctx, std::get<double>(r), 0.0);
    });

    // The Rational kernel throws on overflow (denominator past int64); apply retries
    // in double and the caller gets a value, not an exception.
    TEST_CASE(ctx, "apply :: mul of two small rationals overflows the kernel, recovers as double", {
        const Calculator c;
        const Value r = apply(
            c,
            OpId::Mul,
            {Value{Rational(1, 4000000000)}, Value{Rational(1, 4000000000)}},
            Calculator::AngleUnit::RAD);
        EXPECT_EQ(ctx, arm_of(r), Arm::Double);
        EXPECT_EQ(ctx, std::get<double>(r), 6.25e-20);
    });

    const std::vector<LitCase> literal_cases = {
        {.id = "integer", .input = "123", .expected = Value{std::int64_t{123}}},
        {.id = "decimal is exact", .input = "3.14", .expected = Value{Rational(157, 50)}},
        {.id = "one tenth is exact", .input = "0.1", .expected = Value{Rational(1, 10)}},
        {.id = "scientific is a double", .input = "10e+1", .expected = Value{100.0}},
        {.id = "imaginary unit", .input = "i", .expected = Value{Complex(0.0, 1.0)}},
        {.id = "imaginary suffix", .input = "3i", .expected = Value{Complex(0.0, 3.0)}},
        {.id = "imaginary prefix", .input = "i3", .expected = Value{Complex(0.0, 3.0)}},
        {.id = "negative imaginary", .input = "-2i", .expected = Value{Complex(0.0, -2.0)}},
    };

    for (const auto &tc : literal_cases) {
        test_detail::with_case(ctx, std::string("literal_value :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, literal_value(tc.input), tc.expected);
        });
    }

    // The BigReal cases assert the arm, not the value: the point is that the literal
    // did not collapse into a double.
    const std::vector<ArmCase> literal_arm_cases = {
        {.id = "an exponent past double", .input = "1e309", .expected = Arm::Big},
        {.id = "an underflowing exponent", .input = "1e-400", .expected = Arm::Big},
        {.id = "a huge exponent does not hang", .input = "1e1000000000", .expected = Arm::Big},
    };

    for (const auto &tc : literal_arm_cases) {
        test_detail::with_case(ctx, std::string("literal_value :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, arm_of(literal_value(tc.input)), tc.expected);
        });
    }

    test_detail::with_case(ctx, "literal_value :: text that is not a number is rejected", [&] {
        EXPECT_THROWS(ctx, literal_value("si"));
    });

    test_detail::with_case(ctx, "VarStore :: set, get, overwrite, unset, clear", [&] {
        VarStore env;
        EXPECT_EQ(ctx, env.get("A") == nullptr, true);
        env.set("A", Value{std::int64_t{5}});
        EXPECT_EQ(ctx, std::get<std::int64_t>(*env.get("A")), 5LL);
        env.set("A", Value{std::int64_t{7}});
        EXPECT_EQ(ctx, std::get<std::int64_t>(*env.get("A")), 7LL);
        env.unset("A");
        EXPECT_EQ(ctx, env.get("A") == nullptr, true);
        env.set("A", Value{std::int64_t{7}});
        env.clear();
        EXPECT_EQ(ctx, env.get("A") == nullptr, true);
    });

    const std::vector<EvalCase> rpn_cases = {
        {.id = "a number", .input = "42", .expected = Value{std::int64_t{42}}},
        {.id = "precedence", .input = "2+3*4", .expected = Value{Rational(14)}},
        {.id = "a fraction", .input = "\\frac{1}{3}", .expected = Value{Rational(1, 3)}},
        {.id = "a root with no degree is square",
         .input = "\\root{9}{}",
         .expected = Value{Rational(3)}},
        {.id = "a power", .input = "2^{10}", .expected = Value{Rational(1024)}},
        {.id = "a postfix factorial", .input = "5!", .expected = Value{120.0}},
        // The stack pops right operand first, so a non-commutative op is the only thing
        // that can tell the two apart.
        {.id = "the operands of a subtraction keep their order",
         .input = "41-69",
         .expected = Value{Rational(-28)}},
        {.id = "the operands of a division keep their order",
         .input = "6/2",
         .expected = Value{Rational(3)}},
        {.id = "a postfix feeds a unary", .input = "-50%", .expected = Value{Rational(-1, 2)}},
        {.id = "a chain of unaries", .input = "--5", .expected = Value{Rational(5)}},
        {.id = "a chain of postfixes", .input = "50%%", .expected = Value{Rational(1, 200)}},
        // A fractional exponent is an exact root when the root is rational, and only then.
        {.id = "a rational power that is an exact root",
         .input = "4^{\\frac{1}{2}}",
         .expected = Value{Rational(2)}},
        {.id = "a rational power that is not",
         .input = "2^{\\frac{1}{2}}",
         .expected = Value{1.4142135623730951}},
        // exp builds e in the argument's own type, so it has no integer arm; the integer
        // has to arrive as a double.
        {.id = "exp of an integer", .input = "exp(0)", .expected = Value{1.0}},
        // 1e308 is finite and normal, so nothing about the result betrays what the
        // rounding dropped. The range rule reads the operands instead.
        {.id = "a power at the edge of double's range",
         .input = "10^{308}",
         .expected = Value{BigReal("1e+308")}},
    };

    for (const auto &tc : rpn_cases) {
        test_detail::with_case(ctx, std::string("eval :: ") + tc.id, [&] {
            const Calculator c;
            EXPECT_EQ(ctx, eval_text(c, tc.input), tc.expected);
        });
    }

    const std::vector<RejectCase> rpn_reject_cases = {
        {.id = "an undefined variable", .input = "Z+1", .expected = {}},
        {.id = "a call function typed bare", .input = "mod 5", .expected = {}},
        {.id = "an operator with no kernel", .input = "1==2", .expected = {}},
        // Stack discipline: an op that cannot find its operands.
        {.id = "a binary op missing its second operand", .input = "69+", .expected = {}},
        {.id = "a postfix op with no operand", .input = "%", .expected = {}},
        {.id = "an empty row", .input = "", .expected = {}},
    };

    for (const auto &tc : rpn_reject_cases) {
        test_detail::with_case(ctx, std::string("eval rejects :: ") + tc.id, [&] {
            const Calculator c;
            EXPECT_THROWS(ctx, eval_text(c, tc.input));
        });
    }

    // The env-reading cases need state, so they stand on their own.
    test_detail::with_case(ctx, "eval :: a variable resolves from the store", [&] {
        const Calculator c;
        session_vars().clear();
        session_vars().set("A", Value{std::int64_t{10}});
        EXPECT_EQ(ctx, eval_text(c, "A+5"), Value{Rational(15)});
    });

    // A defined A leaves the misplaced = as the only thing left to reject.
    test_detail::with_case(ctx, "eval rejects :: an assignment inside an expression", [&] {
        const Calculator c;
        session_vars().clear();
        session_vars().set("A", Value{std::int64_t{1}});
        EXPECT_THROWS(ctx, eval_text(c, "1+A=2"));
    });

    test_detail::with_case(ctx, "eval :: a constant", [&] {
        const Calculator c;
        EXPECT_EQ(ctx, arm_of(eval_text(c, "pi")), Arm::Double);
    });

    test_detail::with_case(ctx, "eval :: a subscripted constant", [&] {
        const Calculator c;
        EXPECT_EQ(ctx, arm_of(eval_text(c, "σ_{SB}")), Arm::Double);
    });

    const std::vector<EvalCase> collection_cases = {
        {.id = "arity one is grouping, not a point",
         .input = "(2+3)",
         .expected = Value{Rational(5)}},
        {.id = "implicit multiplication", .input = "2(3)", .expected = Value{Rational(6)}},
        // A bracket wraps only a collection. Around a scalar it groups, so `[5]` is 5, not
        // a one-element list.
        {.id = "a bracket around a scalar groups it",
         .input = "[5]",
         .expected = Value{std::int64_t{5}}},
        {.id = "a variadic reducer over a bracket", .input = "mean[1,2,3]", .expected = Value{2.0}},
        {.id = "a variadic reducer over its args", .input = "mean(1,2,3)", .expected = Value{2.0}},
        {.id = "a reducer over a single value",
         .input = "mean(5)",
         .expected = Value{std::int64_t{5}}},
        {.id = "a fixed-arity call", .input = "gcd(12,8)", .expected = Value{std::int64_t{4}}},
    };

    for (const auto &tc : collection_cases) {
        test_detail::with_case(ctx, std::string("eval :: ") + tc.id, [&] {
            const Calculator c;
            EXPECT_EQ(ctx, eval_text(c, tc.input), tc.expected);
        });
    }

    const std::vector<RejectCase> collection_reject_cases = {
        {.id = "a list of lists", .input = "[[1,2]]", .expected = {}},
        {.id = "a list mixing scalars and points", .input = "[1,(2,3)]", .expected = {}},
        {.id = "an empty point", .input = "()", .expected = {}},
        {.id = "a fixed-arity call with too few args", .input = "mod(5)", .expected = {}},
        {.id = "a fixed-arity call given a collection", .input = "mod([1,2],3)", .expected = {}},
        {.id = "a brace group of arity two", .input = "{1,2}", .expected = {}},
    };

    for (const auto &tc : collection_reject_cases) {
        test_detail::with_case(ctx, std::string("eval rejects :: ") + tc.id, [&] {
            const Calculator c;
            EXPECT_THROWS(ctx, eval_text(c, tc.input));
        });
    }

    // Shape assertions do not fit the value table.
    test_detail::with_case(ctx, "eval :: a list", [&] {
        const Calculator c;
        const Value v = eval_text(c, "[1,2,3]");
        EXPECT_EQ(ctx, arm_of(v), Arm::Coll);
        EXPECT_EQ(ctx, std::get<Collection>(v).items().size(), 3U);
    });

    test_detail::with_case(ctx, "eval :: a point", [&] {
        const Calculator c;
        const Value v = eval_text(c, "(1,2)");
        EXPECT_EQ(ctx, std::get<Collection>(v).kind, CollectionKind::Point);
    });

    test_detail::with_case(ctx, "eval :: an angle-taking call gets the unit", [&] {
        const Calculator c;
        EXPECT_EQ(ctx, eval_text(c, "sin(90)", Calculator::AngleUnit::DEG), Value{Rational(1)});
    });

    // Exact values across all angle units: rational multiples of pi in radians, and Niven
    // angles in degrees/grad, where the double kernel alone would miss (e.g. sin(pi) by ~1.22e-16).
    const auto deg = Calculator::AngleUnit::DEG;
    const auto grad = Calculator::AngleUnit::GRAD;
    const std::vector<UnitEvalCase> exact_trig_cases = {
        {.id = "sin(π)", .input = {"sin(π)", kRad}, .expected = Value{Rational(0)}},
        {.id = "sin π", .input = {"sin π", kRad}, .expected = Value{Rational(0)}},
        {.id = "sin(2π)", .input = {"sin(2π)", kRad}, .expected = Value{Rational(0)}},
        {.id = "cos(π)", .input = {"cos(π)", kRad}, .expected = Value{Rational(-1)}},
        {.id = "cos(π/2)", .input = {"cos(π/2)", kRad}, .expected = Value{Rational(0)}},
        {.id = "sin(π/6)", .input = {"sin(π/6)", kRad}, .expected = Value{Rational(1, 2)}},
        {.id = "sin(\\frac{π}{6})",
         .input = {"sin(\\frac{π}{6})", kRad},
         .expected = Value{Rational(1, 2)}},
        {.id = "cos(π/3)", .input = {"cos(π/3)", kRad}, .expected = Value{Rational(1, 2)}},
        {.id = "tan(π/4)", .input = {"tan(π/4)", kRad}, .expected = Value{Rational(1)}},
        {.id = "sin(1000π)", .input = {"sin(1000π)", kRad}, .expected = Value{Rational(0)}},
        {.id = "2sin(π/6)", .input = {"2sin(π/6)", kRad}, .expected = Value{Rational(1)}},
        {.id = "sin(30)", .input = {"sin(30)", deg}, .expected = Value{Rational(1, 2)}},
        {.id = "sin 30", .input = {"sin 30", deg}, .expected = Value{Rational(1, 2)}},
        {.id = "cos(60)", .input = {"cos(60)", deg}, .expected = Value{Rational(1, 2)}},
        {.id = "cos(120)", .input = {"cos(120)", deg}, .expected = Value{Rational(-1, 2)}},
        {.id = "cos(90)", .input = {"cos(90)", deg}, .expected = Value{Rational(0)}},
        {.id = "tan(45)", .input = {"tan(45)", deg}, .expected = Value{Rational(1)}},
        {.id = "sin(100) grad", .input = {"sin(100)", grad}, .expected = Value{Rational(1)}},
        // The point of an exact result type: the exactness survives into what surrounds it.
        {.id = "2sin(30)", .input = {"2sin(30)", deg}, .expected = Value{Rational(1)}},
    };
    for (const auto &tc : exact_trig_cases) {
        test_detail::with_case(ctx, std::string("exact trig :: ") + tc.id, [&] {
            const Calculator c;
            EXPECT_EQ(ctx, eval_text(c, tc.input.src, tc.input.unit), tc.expected);
        });
    }

    // A rational half-turn with an undefined tangent must still throw, in either unit.
    const std::vector<UnitRejectCase> exact_trig_reject_cases = {
        {.id = "tan(π/2)", .input = {"tan(π/2)", kRad}, .expected = {}},
        {.id = "tan(90)", .input = {"tan(90)", deg}, .expected = {}},
    };
    for (const auto &tc : exact_trig_reject_cases) {
        test_detail::with_case(ctx, std::string("exact trig :: ") + tc.id, [&] {
            const Calculator c;
            EXPECT_THROWS(ctx, eval_text(c, tc.input.src, tc.input.unit));
        });
    }

    // Misses that must still answer, on the double path: no rational half-turn, no constant
    // at all, or (degrees) an argument outside the Niven table.
    const std::vector<UnitArmCase> exact_trig_arm_cases = {
        {.id = "sin(π/5) is not a rational half-turn",
         .input = {"sin(π/5)", kRad},
         .expected = Arm::Double},
        {.id = "sin(2) has no constant at all", .input = {"sin(2)", kRad}, .expected = Arm::Double},
        {.id = "sin(20) misses the Niven table",
         .input = {"sin(20)", deg},
         .expected = Arm::Double},
        // -9223372036854775807-1 lands on an int64 Rational whose numerator is exactly
        // INT64_MIN; that used to reach std::gcd and abort, and must instead decline to the
        // double path.
        {.id = "an INT64_MIN numerator declines, not aborts",
         .input = {"sin(-9223372036854775807-1)", deg},
         .expected = Arm::Double},
    };
    for (const auto &tc : exact_trig_arm_cases) {
        test_detail::with_case(ctx, std::string("exact trig :: ") + tc.id, [&] {
            const Calculator c;
            EXPECT_EQ(ctx, arm_of(eval_text(c, tc.input.src, tc.input.unit)), tc.expected);
        });
    }

    // A constant stored in a variable loses its identity at assignment, because the store holds
    // a Value. Asserted so the limitation is deliberate and visible, not a silent gap.
    test_detail::with_case(ctx, "exact trig :: a stored constant is not symbolic", [&] {
        const Calculator c;
        session_vars().clear();
        session_vars().set("A", tcalc::eval::const_value(tcalc::consts::ConstId::Pi));
        EXPECT_EQ(ctx, std::holds_alternative<double>(eval_text(c, "sin(A)")), true);
        session_vars().clear();
    });

    // evaluate() carries state, so its cases run in sequence rather than from one table.
    test_detail::with_case(ctx, "evaluate :: an assignment stores and returns", [&] {
        const Calculator c;
        session_vars().clear();
        EXPECT_EQ(ctx, eval_source(c, "A=2+3"), Value{Rational(5)});
        EXPECT_EQ(ctx, *session_vars().get("A"), Value{Rational(5)});
    });

    test_detail::with_case(ctx, "evaluate :: a stored variable is readable on the next row", [&] {
        const Calculator c;
        session_vars().clear();
        eval_source(c, "A=10");
        EXPECT_EQ(ctx, eval_source(c, "A*2"), Value{Rational(20)});
    });

    test_detail::with_case(ctx, "evaluate :: a subscripted variable", [&] {
        const Calculator c;
        session_vars().clear();
        eval_source(c, "x_{1}=7");
        EXPECT_EQ(ctx, eval_source(c, "x_{1}+1"), Value{Rational(8)});
    });

    test_detail::with_case(ctx, "evaluate :: a row with no assignment is just evaluated", [&] {
        const Calculator c;
        session_vars().clear();
        EXPECT_EQ(ctx, eval_source(c, "2+3*4"), Value{Rational(14)});
    });

    // The message is the contract: it is what the user reads, and it is asserted verbatim.
    const std::vector<MsgCase> assignment_reject_cases = {
        {.id = "an operator as the target",
         .input = "%=2",
         .expected = "% is an operator, use another letter"},
        {.id = "a call function as the target",
         .input = "sin=2",
         .expected = "sin is an operator, use another letter"},
        {.id = "a constant as the target",
         .input = "π=2",
         .expected = "π is defined as a constant, use another letter"},
        {.id = "a one-letter constant as the target",
         .input = "e=2",
         .expected = "e is defined as a constant, use another letter"},
        {.id = "a subscripted constant as the target",
         .input = "σ_{SB}=1",
         .expected = "σ_SB is defined as a constant, use another letter"},
        {.id = "a subscript over a non-letter",
         .input = "2_{3}=4",
         .expected = "left of = must be a single letter (A-Za-z)"},
        {.id = "an empty right-hand side", .input = "A=", .expected = "assignment has no value"},
    };

    for (const auto &tc : assignment_reject_cases) {
        test_detail::with_case(ctx, std::string("evaluate rejects :: ") + tc.id, [&] {
            const Calculator c;
            session_vars().clear();
            EXPECT_THROWS(ctx, eval_source(c, tc.input));
            try {
                eval_source(c, tc.input);
            } catch (const CalculatorError &e) {
                EXPECT_EQ(ctx, std::string(e.what()), std::string(tc.expected));
                EXPECT_EQ(ctx, e.kind(), ErrorKind::Invalid);
            }
        });
    }

    // An `=` anywhere but second position is not an assignment, so it reaches the walk.
    test_detail::with_case(ctx, "evaluate rejects :: a leading =", [&] {
        const Calculator c;
        session_vars().clear();
        EXPECT_THROWS(ctx, eval_source(c, "=5"));
    });

    // =========================================================================
    // Normalizations
    // =========================================================================
    const std::vector<NormCase> norm_cases = {

        {.id = "double sub to add",
         .input = {N("1"), Op_(OpId::Sub), Op_(OpId::Sub), N("2")},
         .expected = {N("1"), Op_(OpId::Add), N("2")}},

        {.id = "add sub to sub",
         .input = {N("1"), Op_(OpId::Add), Op_(OpId::Sub), N("2")},
         .expected = {N("1"), Op_(OpId::Sub), N("2")}},

        {.id = "mixed sign collapse",
         .input =
             {N("1"),
              Op_(OpId::Add),
              Op_(OpId::Sub),
              Op_(OpId::Sub),
              Op_(OpId::Sub),
              Op_(OpId::Add),
              Op_(OpId::Add),
              Op_(OpId::Sub),
              Op_(OpId::Sub),
              Op_(OpId::Add),
              Op_(OpId::Add),
              N("2")},
         .expected = {N("1"), Op_(OpId::Sub), N("2")}},

        {.id = "add then negate kept",
         .input = {N("1"), Op_(OpId::Add), Op_(OpId::Negate), N("2")},
         .expected = {N("1"), Op_(OpId::Add), Op_(OpId::Negate), N("2")}},

        // Implicit multiplications
        {.id = "implicit mul before paren",
         .input = {N("2"), Pp({EN("3")})},
         .expected = {N("2"), Op_(OpId::Mul), Pp({EN("3")})}},

        {.id = "implicit mul after postfix",
         .input = {N("3"), Op_(OpId::Fact), N("2")},
         .expected = {N("3"), Op_(OpId::Fact), Op_(OpId::Mul), N("2")}}};

    for (std::size_t i = 0; i < norm_cases.size(); ++i) {
        const auto &tc = norm_cases[i];
        test_detail::with_case(ctx, std::string("normalize :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, tcalc::eval::normalize(tc.input), tc.expected);
        });
    }

    test_detail::with_case(ctx, "normalize :: no implicit mult between sum and its body", [&] {
        const auto raw = tcalc::parser::tokenize("\\sum_{n=1}^{3} n").tokens;
        const auto norm = tcalc::eval::normalize(raw);
        const bool has_mul = std::ranges::any_of(norm, [](const Token &t) {
            return t.kind == TokenKind::Op && std::get<OpToken>(t.data).op_id == OpId::Mul;
        });
        EXPECT_EQ(ctx, has_mul, false);
    });

    test_detail::with_case(ctx, "normalize :: implicit mult before a sum", [&] {
        const auto raw = tcalc::parser::tokenize("2\\sum_{n=1}^{3} n").tokens;
        const auto norm = tcalc::eval::normalize(raw);
        // Expect a Mul inserted between N(2) and the Sum: 2 · Σ…
        const bool mul_before_sum = norm.size() >= 2 && norm[1].kind == TokenKind::Op &&
                                    std::get<OpToken>(norm[1].data).op_id == OpId::Mul &&
                                    norm[2].kind == TokenKind::Latex;
        EXPECT_EQ(ctx, mul_before_sum, true);
    });

    test_detail::with_case(ctx, "normalize :: body is the term, not the first operand", [&] {
        // \sum 2n + 5 must group `2n`, never just `2`.
        const auto out =
            tcalc::eval::normalize(tcalc::parser::tokenize("\\sum_{n=1}^{3} 2n + 5").tokens);
        // [Sum, Paren(2 * n), Add, 5]
        EXPECT_EQ(ctx, out.size(), std::size_t{4});
        EXPECT_EQ(ctx, out[1].kind == TokenKind::Paren, true);
        const auto &group = std::get<tcalc::parser::ParenToken>(out[1].data);
        const auto &body = std::get<std::vector<Token>>(group.elements.at(0));
        EXPECT_EQ(ctx, body.size(), std::size_t{3}); // 2 . n
        EXPECT_EQ(ctx, out[2].kind == TokenKind::Op, true);
    });

    test_detail::with_case(ctx, "normalize :: unary and postfix stay inside the body", [&] {
        // -n! is all body; only the + terminates it.
        const auto out =
            tcalc::eval::normalize(tcalc::parser::tokenize("\\sum_{n=1}^{3}-n!+5").tokens);
        EXPECT_EQ(ctx, out.size(), std::size_t{4});
        const auto &group = std::get<tcalc::parser::ParenToken>(out[1].data);
        const auto &body = std::get<std::vector<Token>>(group.elements.at(0));
        EXPECT_EQ(ctx, body.size(), std::size_t{3}); // Negate, n, Fact
    });

    test_detail::with_case(ctx, "normalize :: implicit mult lands before the sum, not inside", [&] {
        const auto out =
            tcalc::eval::normalize(tcalc::parser::tokenize("2\\sum_{n=1}^{3} n").tokens);
        // [2, Mul, Sum, n] : the Mul is between 2 and the sum; n passes through unwrapped
        EXPECT_EQ(ctx, out.size(), std::size_t{4});
        EXPECT_EQ(ctx, out[1].kind == TokenKind::Op, true);
        EXPECT_EQ(ctx, std::get<OpToken>(out[1].data).op_id == OpId::Mul, true);
        EXPECT_EQ(ctx, out[3].kind == TokenKind::Char, true);
    });

    test_detail::with_case(ctx, "normalize :: one plus closes every open body", [&] {
        const auto out = tcalc::eval::normalize(
            tcalc::parser::tokenize("\\sum_{i=1}^{2} \\sum_{j=1}^{2} j + 5").tokens);
        // [Sum_i, Paren([Sum_j, j]), Add, 5]
        EXPECT_EQ(ctx, out.size(), std::size_t{4});
        const auto &outer = std::get<tcalc::parser::ParenToken>(out[1].data);
        const auto &outer_body = std::get<std::vector<Token>>(outer.elements.at(0));
        EXPECT_EQ(ctx, outer_body.size(), std::size_t{2}); // Sum_j, j
        // j is an alias of the imaginary-unit constant, so it tokenizes as Const, not Char;
        // either way it passes through unwrapped, not TokenKind::Paren.
        EXPECT_EQ(ctx, outer_body[1].kind == TokenKind::Const, true);
    });

    test_detail::with_case(
        ctx, "normalize :: a sum with nothing after it gets an empty group", [&] {
            const auto out =
                tcalc::eval::normalize(tcalc::parser::tokenize("\\sum_{n=1}^{5}").tokens);
            EXPECT_EQ(ctx, out.size(), std::size_t{2});
            const auto &group = std::get<tcalc::parser::ParenToken>(out[1].data);
            EXPECT_EQ(ctx, group.elements.empty(), true);
        });

    test_detail::with_case(ctx, "normalize :: a single-token body passes through unwrapped", [&] {
        // A user paren is already one complete token: it passes straight through, not
        // wrapped a second time.
        const auto paren_body =
            tcalc::eval::normalize(tcalc::parser::tokenize("\\sum_{n=1}^{5} (n^{2}+2)").tokens);
        EXPECT_EQ(ctx, paren_body.size(), std::size_t{2});
        EXPECT_EQ(ctx, paren_body[1].kind == TokenKind::Paren, true);
        const auto &group = std::get<tcalc::parser::ParenToken>(paren_body[1].data);
        EXPECT_EQ(ctx, group.elements.size(), std::size_t{1}); // the user's own group
        const auto &row = std::get<std::vector<Token>>(group.elements.at(0));
        EXPECT_EQ(ctx, row.size(), std::size_t{3}); // n^2, +, 2 inside the user's paren

        // n^{2} tokenizes as one Pow LatexToken (the base folds in at tokenize time), so
        // it too passes through unwrapped: no synthetic paren at all.
        const auto pow_body =
            tcalc::eval::normalize(tcalc::parser::tokenize("\\sum_{n=1}^{5} n^{2}").tokens);
        EXPECT_EQ(ctx, pow_body.size(), std::size_t{2});
        EXPECT_EQ(ctx, pow_body[1].kind == TokenKind::Latex, true);

        // A trailing + still closes the body at Add precedence, but the token right after
        // Sum stays the bare Pow, no wrapper introduced just because it once had a +.
        const auto bare =
            tcalc::eval::normalize(tcalc::parser::tokenize("\\sum_{n=1}^{5} n^{2}+2").tokens);
        EXPECT_EQ(ctx, bare.size(), std::size_t{4}); // Sum, n^2, Add, 2
        EXPECT_EQ(ctx, bare[1].kind == TokenKind::Latex, true);
    });

    // Shuntifications
    const std::vector<ShuntCase> shunt_cases = {

        {.id = "basic precedence",
         .input =
             {
                 N("1"),
                 Op_(OpId::Add),
                 N("2"),
                 Op_(OpId::Mul),
                 N("3"),
                 Op_(OpId::Pow),
                 N("4"),
             },
         .expected =
             {
                 N("1"),
                 N("2"),
                 N("3"),
                 N("4"),
                 Op_(OpId::Pow),
                 Op_(OpId::Mul),
                 Op_(OpId::Add),
             }},

        {.id = "pow right assoc",
         .input =
             {
                 N("2"),
                 Op_(OpId::Pow),
                 N("3"),
                 Op_(OpId::Pow),
                 N("4"),
             },
         .expected =
             {
                 N("2"),
                 N("3"),
                 N("4"),
                 Op_(OpId::Pow),
                 Op_(OpId::Pow),
             }},

        {.id = "unary before func",
         .input =
             {
                 Op_(OpId::Sin),
                 Op_(OpId::Negate),
                 N("2"),
             },
         .expected =
             {
                 N("2"),
                 Op_(OpId::Negate),
                 Op_(OpId::Sin),
             }},

        {.id = "implicit mul after paren",
         // Under unified ParenToken model, shunting_yard treats ParenToken as a
         // single opaque operand (push to output). Implicit Mul is inserted by
         // normalize between operand-ending N(2) and operand-starting paren.
         .input =
             {
                 N("2"),
                 Pp({EV({N("3"), Op_(OpId::Add), N("4")})}),
             },
         .expected =
             {
                 N("2"),
                 Pp({EV({N("3"), Op_(OpId::Add), N("4")})}),
                 Op_(OpId::Mul),
             }},

        {.id = "postfix percent precedence",
         .input =
             {
                 N("2"),
                 Op_(OpId::Pow),
                 N("3"),
                 Op_(OpId::Percent),
                 Op_(OpId::Add),
                 N("4"),
             },
         .expected =
             {
                 N("2"),
                 N("3"),
                 Op_(OpId::Percent),
                 Op_(OpId::Pow),
                 N("4"),
                 Op_(OpId::Add),
             }},

        {.id = "2c -> implicit mul",
         .input = {N("2"), Co(tcalc::consts::ConstId::SpeedOfLight)},
         .expected = {N("2"), Co(tcalc::consts::ConstId::SpeedOfLight), Op_(OpId::Mul)}},
        {.id = "implicit mul: 2 pi",
         .input = {N("2"), Co(tcalc::consts::ConstId::Pi)},
         .expected = {N("2"), Co(tcalc::consts::ConstId::Pi), Op_(OpId::Mul)}},
        {.id = "implicit mul: pi e",
         .input = {Co(tcalc::consts::ConstId::Pi), Co(tcalc::consts::ConstId::EulerNumber)},
         .expected =
             {Co(tcalc::consts::ConstId::Pi),
              Co(tcalc::consts::ConstId::EulerNumber),
              Op_(OpId::Mul)}},
        {.id = "implicit mul: a b chars",
         .input = {Ch('a'), Ch('b')},
         .expected = {Ch('a'), Ch('b'), Op_(OpId::Mul)}},
    };

    for (std::size_t i = 0; i < shunt_cases.size(); ++i) {
        const auto &tc = shunt_cases[i];
        test_detail::with_case(ctx, std::string("shunting yard :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, tcalc::eval::shunting_yard(tc.input), tc.expected);
        });
    }

    // Iterated ops: Sum / Prod semantics. Add/Mul have no Int64 arm (see the
    // arms_of static_asserts above), so every result here is Rational, matching every
    // other Add/Mul-driven case in rpn_cases (e.g. "2+3*4" -> Rational(14)).
    const Calculator c;

    test_detail::with_case(ctx, "iterated :: term rule, sum of squares", [&] {
        EXPECT_EQ(ctx, eval_text(c, "2 + \\sum_{n=1}^{5} n^{2} - 4"), Value{Rational(53)});
    });
    test_detail::with_case(ctx, "iterated :: parenthesised body", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{5} (n^{2} - 4)"), Value{Rational(35)});
    });
    test_detail::with_case(ctx, "iterated :: a single-token user paren body", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{5} (n)"), Value{Rational(15)});
    });
    test_detail::with_case(ctx, "iterated :: a user paren body is not double-wrapped", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} (n^{2}+2)"), Value{Rational(20)});
    });
    test_detail::with_case(ctx, "iterated :: a terminator right after a paren body", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} (n^{2}+2) + 5"), Value{Rational(25)});
    });
    // The term rule: a bare + terminates the body and applies to the sum's result, while
    // the same + parenthesised goes inside it and is summed per term.
    test_detail::with_case(ctx, "iterated :: a bare + applies to the sum's result", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} 2n + 5"), Value{Rational(17)});
    });
    test_detail::with_case(ctx, "iterated :: the same + parenthesised goes inside the body", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} (2n+5)"), Value{Rational(27)});
    });
    // A tighter operator (* or !) binds past a paren body into the term, unlike +.
    test_detail::with_case(ctx, "iterated :: * binds past a paren body into the term", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} (n+1)*n"), Value{Rational(20)});
    });
    test_detail::with_case(ctx, "iterated :: ! binds past a paren body into the term", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} (n+1)!"), Value{32.0});
    });
    test_detail::with_case(
        ctx, "iterated :: a comma'd paren body is a point, not a pass-through", [&] {
            EXPECT_THROWS(ctx, eval_text(c, "\\sum_{n=1}^{3} (1,2)"));
            try {
                eval_text(c, "\\sum_{n=1}^{3} (1,2)");
            } catch (const CalculatorError &e) {
                EXPECT_EQ(
                    ctx, std::string(e.what()), std::string("unsupported operand type for add"));
            }
        });
    test_detail::with_case(ctx, "iterated :: an unclosed paren body still gets wrapped", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} (n"), Value{Rational(6)});
    });
    test_detail::with_case(ctx, "iterated :: plain sum and product", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{4} n^{2}"), Value{Rational(30)});
        EXPECT_EQ(ctx, eval_text(c, "\\prod_{m=1}^{4} m"), Value{Rational(24)});
    });
    test_detail::with_case(ctx, "iterated :: leading sign belongs to the body", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} -n"), Value{Rational(-6)});
    });
    test_detail::with_case(ctx, "iterated :: implicit mult before the sum", [&] {
        EXPECT_EQ(ctx, eval_text(c, "2\\sum_{n=1}^{3} n"), Value{Rational(12)});
    });
    // "i" and "j" are aliases of the imaginary-unit constant (parser/pub/consts.hpp), so
    // they tokenize as ConstToken rather than a bindable variable; "n" and "m" stand in.
    test_detail::with_case(ctx, "iterated :: two sums separated by + are independent", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{2} n + \\sum_{m=1}^{2} m"), Value{Rational(6)});
    });
    test_detail::with_case(ctx, "iterated :: adjacent sums nest", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{2} \\sum_{m=1}^{2} nm"), Value{Rational(9)});
    });

    test_detail::with_case(ctx, "iterated :: the loop variable does not leak", [&] {
        session_vars().clear();
        session_vars().set("n", Value{std::int64_t{9}});
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} n"), Value{Rational(6)});
        const Value *after = session_vars().get("n");
        EXPECT_EQ(ctx, after != nullptr && *after == Value{std::int64_t{9}}, true);
    });
    test_detail::with_case(ctx, "iterated :: an unbound loop variable stays unbound", [&] {
        session_vars().unset("q");
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{q=1}^{3} q"), Value{Rational(6)});
        EXPECT_EQ(ctx, session_vars().get("q") == nullptr, true);
    });
    test_detail::with_case(ctx, "iterated :: the body reads other session variables", [&] {
        session_vars().clear();
        session_vars().set("A", Value{std::int64_t{10}});
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} nA"), Value{Rational(60)});
    });
    test_detail::with_case(ctx, "iterated :: empty range yields the identity", [&] {
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=5}^{4} n"), Value{Rational(0)});
        EXPECT_EQ(ctx, eval_text(c, "\\prod_{n=5}^{4} n"), Value{Rational(1)});
    });
    // The message text is the contract, and the Sum/Product parametrization used to be
    // hardcoded to "Sum": pinning both ops on every path catches that regression class.
    const std::vector<MsgCase> iterated_msg_cases = {
        {.id = "sum missing body", .input = "\\sum_{n=1}^{5}", .expected = "Sum has no body."},
        {.id = "product missing body",
         .input = "\\prod_{m=1}^{5}",
         .expected = "Product has no body."},
        {.id = "sum missing upper limit",
         .input = "\\sum_{n=1}^{} n",
         .expected = "Sum has no upper limit."},
        {.id = "product missing upper limit",
         .input = "\\prod_{m=1}^{} m",
         .expected = "Product has no upper limit."},
        {.id = "sum bad lower limit",
         .input = "\\sum_{5}^{4} n",
         .expected = "Sum limit must read variable = start."},
        {.id = "product bad lower limit",
         .input = "\\prod_{5}^{4} m",
         .expected = "Product limit must read variable = start."},
        {.id = "sum non-integer bound",
         .input = "\\sum_{n=1}^{2.5} n",
         .expected = "Sum limits must be whole numbers."},
        {.id = "product non-integer bound",
         .input = "\\prod_{m=1}^{2.5} m",
         .expected = "Product limits must be whole numbers."},
    };

    for (const auto &tc : iterated_msg_cases) {
        test_detail::with_case(ctx, std::string("iterated rejects :: ") + tc.id, [&] {
            EXPECT_THROWS(ctx, eval_text(c, tc.input));
            try {
                eval_text(c, tc.input);
            } catch (const CalculatorError &e) {
                EXPECT_EQ(ctx, std::string(e.what()), std::string(tc.expected));
                EXPECT_EQ(ctx, e.kind(), ErrorKind::Invalid);
            }
        });
    }

    test_detail::with_case(
        ctx, "iterated :: a runaway brute loop early-exits on the time budget", [&] {
            // A body the closed-form matcher declines (2n grows, no polynomial sum for a
            // product) over a range under the iteration cap would run for seconds. With a tiny
            // budget the deadline fires inside the loop and reports "Undefined" instead of
            // freezing. The whole suite otherwise runs unlimited, so this is the only timed case.
            tcalc::eval::set_eval_time_budget_ms(20);
            EXPECT_THROWS(ctx, eval_text(c, "\\prod_{n=1}^{999999} 2n"));
            try {
                eval_text(c, "\\prod_{n=1}^{999999} 2n");
            } catch (const CalculatorError &e) {
                EXPECT_EQ(ctx, std::string(e.what()), std::string(tcalc::errmsg::kEvalTimedOut));
                EXPECT_EQ(ctx, e.kind(), ErrorKind::MathErr);
            }
            tcalc::eval::set_eval_time_budget_ms(0); // restore the unlimited default for the rest
        });

    test_detail::with_case(
        ctx, "iterated :: the loop variable is restored when the body throws", [&] {
            session_vars().clear();
            session_vars().set("n", Value{std::int64_t{9}});
            EXPECT_THROWS(ctx, eval_text(c, "\\sum_{n=1}^{3} \\frac{1}{n-2}"));
            const Value *after = session_vars().get("n");
            EXPECT_EQ(ctx, after != nullptr && *after == Value{std::int64_t{9}}, true);
        });

    test_detail::with_case(
        ctx, "iterated :: a nested sum reusing the caller's name leaves it untouched", [&] {
            session_vars().clear();
            session_vars().set("n", Value{std::int64_t{9}});
            EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{2} \\sum_{n=1}^{2} n"), Value{Rational(6)});
            const Value *after = session_vars().get("n");
            EXPECT_EQ(ctx, after != nullptr && *after == Value{std::int64_t{9}}, true);
        });

    test_detail::with_case(ctx, "closed_forms :: value_from_big_rational lattice", [&] {
        using tcalc::eval::CppRat;
        using tcalc::eval::value_from_big_rational;
        // int64-range integer -> Rational (NOT Int64)
        EXPECT_EQ(ctx, value_from_big_rational(CppRat(15)), Value{Rational(15)});
        // small fraction -> Rational
        EXPECT_EQ(ctx, value_from_big_rational(CppRat(1, 2)), Value{Rational(1, 2)});
        // past int64 -> double (the calc's overflow convention, not BigReal)
        const Value big = value_from_big_rational(CppRat("1000000000000000000000")); // 1e21 > int64
        EXPECT_EQ(ctx, std::holds_alternative<double>(big), true);
    });

    test_detail::with_case(ctx, "closed_forms :: faulhaber sums polynomials exactly", [&] {
        using tcalc::eval::CppRat;
        using tcalc::eval::faulhaber_sum;
        // Sum n over 1..5 = 15
        EXPECT_EQ(ctx, faulhaber_sum({CppRat(0), CppRat(1)}, 1, 5), CppRat(15));
        // Sum n^2 over 1..4 = 30
        EXPECT_EQ(ctx, faulhaber_sum({CppRat(0), CppRat(0), CppRat(1)}, 1, 4), CppRat(30));
        // Sum (n^2 - 3n) over 1..5 = 10
        EXPECT_EQ(ctx, faulhaber_sum({CppRat(0), CppRat(-3), CppRat(1)}, 1, 5), CppRat(10));
        // constant body c0 over a..b = c0*(b-a+1)
        EXPECT_EQ(ctx, faulhaber_sum({CppRat(7)}, 2, 5), CppRat(28));
        // range not starting at 1: Sum n over 3..5 = 12
        EXPECT_EQ(ctx, faulhaber_sum({CppRat(0), CppRat(1)}, 3, 5), CppRat(12));
        // large range stays exact: Sum n^2 over 1..1000000
        EXPECT_EQ(
            ctx,
            faulhaber_sum({CppRat(0), CppRat(0), CppRat(1)}, 1, 1000000),
            CppRat("333333833333500000"));
    });

    // Symbolic scalar algebra, exercised directly rather than through a sum. `sym` builds an
    // expectation from scalar_push, so no row is checked against the operation it is testing.
    {
        using tcalc::consts::ConstId;
        using tcalc::eval::CppRat;
        using tcalc::eval::Scalar;
        const auto sym = [](ConstId id, int exp) {
            Scalar s;
            tcalc::eval::scalar_push(s, static_cast<std::int16_t>(id), exp);
            return s;
        };
        const auto scaled = [](const CppRat &c, Scalar s) {
            s.coeff = c;
            return s;
        };
        const Scalar two = tcalc::eval::scalar_rational(CppRat(2));
        const Scalar pi = sym(ConstId::Pi, 1);
        const Scalar e = sym(ConstId::EulerNumber, 1);

        const std::vector<ScalarCase> scalar_cases = {
            {.id = "a symbol times itself raises its exponent",
             .input = {pi, pi, '*'},
             .expected = sym(ConstId::Pi, 2)},
            {.id = "a symbol over itself is exactly one",
             .input = {pi, pi, '/'},
             .expected = tcalc::eval::scalar_rational(CppRat(1))},
            {.id = "a squared symbol over itself is exactly the symbol",
             .input = {sym(ConstId::Pi, 2), pi, '/'},
             .expected = pi},
            {.id = "like terms add exactly",
             .input = {pi, pi, '+'},
             .expected = scaled(CppRat(2), pi)},
            {.id = "like terms cancel exactly",
             .input = {pi, pi, '-'},
             .expected = scaled(CppRat(0), pi)},
            {.id = "two symbols take two slots",
             .input = {pi, e, '*'},
             .expected = tcalc::eval::scalar_mul(sym(ConstId::Pi, 1), sym(ConstId::EulerNumber, 1))
                             .value()},
            {.id = "a symbol divides back out of a product",
             .input = {tcalc::eval::scalar_mul(pi, e).value(), e, '/'},
             .expected = pi},
        };

        for (const auto &tc : scalar_cases) {
            test_detail::with_case(ctx, std::string("scalar :: ") + tc.id, [&] {
                const auto got = tc.input.op == '*'
                                     ? tcalc::eval::scalar_mul(tc.input.lhs, tc.input.rhs)
                                 : tc.input.op == '/'
                                     ? tcalc::eval::scalar_div(tc.input.lhs, tc.input.rhs)
                                     : tcalc::eval::scalar_add(
                                           tc.input.lhs, tc.input.rhs, tc.input.op == '+' ? 1 : -1);
                EXPECT_EQ(ctx, got.has_value(), true);
                EXPECT_EQ(ctx, tcalc::eval::scalar_equal(*got, tc.expected), true);
            });
        }

        // Predicates and the opaque fall-back do not fit a two-operand row.
        test_detail::with_case(ctx, "scalar :: predicates and the opaque fall-back", [&] {
            EXPECT_EQ(ctx, tcalc::eval::scalar_is_rational(two), true);
            EXPECT_EQ(ctx, tcalc::eval::scalar_is_rational(pi), false);
            EXPECT_EQ(
                ctx,
                tcalc::eval::scalar_is_rational(tcalc::eval::scalar_div(pi, pi).value()),
                true);
            EXPECT_EQ(
                ctx,
                tcalc::eval::scalar_is_zero(tcalc::eval::scalar_add(pi, pi, -1).value()),
                true);
            // Unlike terms leave the symbolic world; the value survives, the identity does not.
            const Scalar sum = tcalc::eval::scalar_add(two, pi, 1).value();
            EXPECT_EQ(ctx, tcalc::eval::scalar_is_rational(sum), false);
            EXPECT_EQ(ctx, tcalc::eval::scalar_equal(sum, pi), false);
            const double want = 2.0 + tcalc::eval::scalar_eval(pi).value();
            EXPECT_EQ(ctx, tcalc::eval::scalar_eval(sum).value() == want, true);
        });
    }

    // The same walk the closed forms use, with no bound variable, so every token folds into the
    // var-free arm and the result is the span's Scalar. This is what lets the radian trig path
    // see that an argument was a rational multiple of pi after the Value has lost it.
    test_detail::with_case(ctx, "scalar_of_tokens :: reads a var-free span", [&] {
        using tcalc::eval::CppRat;
        const auto of = [&](const char *src) {
            return tcalc::eval::scalar_of_tokens(
                tcalc::eval::shunting_yard(tcalc::parser::tokenize(src).tokens));
        };
        const auto pi_coeff = [&](const char *src) -> std::optional<CppRat> {
            const auto s = of(src);
            if (!s || s->n_syms != 1 || s->real != 1.0 || s->syms[0].exp != 1)
                return std::nullopt;
            if (s->syms[0].id != tcalc::eval::const_sym(tcalc::consts::ConstId::Pi))
                return std::nullopt;
            return s->coeff;
        };
        EXPECT_EQ(ctx, pi_coeff("π").has_value(), true);
        EXPECT_EQ(ctx, *pi_coeff("π"), CppRat(1));
        EXPECT_EQ(ctx, *pi_coeff("2π"), CppRat(2));
        EXPECT_EQ(ctx, *pi_coeff("π/6"), CppRat(1, 6));
        EXPECT_EQ(ctx, *pi_coeff("\\frac{π}{6}"), CppRat(1, 6));
        EXPECT_EQ(ctx, *pi_coeff("3π/2"), CppRat(3, 2));
        // A plain rational is still a Scalar, just not a pi-carrying one.
        EXPECT_EQ(ctx, pi_coeff("30").has_value(), false);
        EXPECT_EQ(ctx, of("30")->coeff, CppRat(30));
        // pi squared is not a rational multiple of a half turn.
        EXPECT_EQ(ctx, pi_coeff("π^{2}").has_value(), false);
    });

    test_detail::with_case(ctx, "closed_forms :: exact_rational_root finds exact roots", [&] {
        using tcalc::eval::CppRat;
        using calc_detail::exact_rational_root;
        EXPECT_EQ(ctx, exact_rational_root(CppRat(4), 2).value(), CppRat(2));
        EXPECT_EQ(ctx, exact_rational_root(CppRat(9), 2).value(), CppRat(3));
        EXPECT_EQ(ctx, exact_rational_root(CppRat(8), 3).value(), CppRat(2));
        EXPECT_EQ(ctx, exact_rational_root(CppRat(4, 9), 2).value(), CppRat(2, 3));
        EXPECT_EQ(ctx, exact_rational_root(CppRat(-8), 3).value(), CppRat(-2));
        // q == 1 is the identity
        EXPECT_EQ(ctx, exact_rational_root(CppRat(5, 7), 1).value(), CppRat(5, 7));
        // Larger and composite q, so Newton's convergence loop is exercised past q = 3.
        EXPECT_EQ(ctx, exact_rational_root(CppRat(27), 3).value(), CppRat(3));
        EXPECT_EQ(ctx, exact_rational_root(CppRat(16), 4).value(), CppRat(2));
        EXPECT_EQ(ctx, exact_rational_root(CppRat(1024), 10).value(), CppRat(2));
        EXPECT_EQ(ctx, exact_rational_root(CppRat(8, 27), 3).value(), CppRat(2, 3));
    });

    test_detail::with_case(ctx, "closed_forms :: exact_rational_root declines non-roots", [&] {
        using tcalc::eval::CppRat;
        using calc_detail::exact_rational_root;
        EXPECT_EQ(ctx, exact_rational_root(CppRat(2), 2).has_value(), false);
        EXPECT_EQ(ctx, exact_rational_root(CppRat(3), 3).has_value(), false);
        EXPECT_EQ(ctx, exact_rational_root(CppRat(-4), 2).has_value(), false); // even, negative
        EXPECT_EQ(ctx, exact_rational_root(CppRat(2, 3), 2).has_value(), false);
        // q > log2(n): the only candidate root is 1, declines fast without Newton
        EXPECT_EQ(ctx, exact_rational_root(CppRat(2), 100).has_value(), false);
        // q <= 0 is not a root degree at all; the function declines rather than trusting the
        // caller (G1 never passes one: a CppRat's denominator is always positive).
        EXPECT_EQ(ctx, exact_rational_root(CppRat(4), 0).has_value(), false);
        EXPECT_EQ(ctx, exact_rational_root(CppRat(4), -2).has_value(), false);
    });

    // Relative comparison with an absolute floor, so a reference of 0 still has slack.
    // 1e-9 is what the trig cases already use.
    const auto near_rel = [](double got, double want) {
        return std::abs(got - want) <= 1e-9 * std::max(1.0, std::abs(want));
    };

    test_detail::with_case(
        ctx, "closed form :: a double-bound session variable falls to brute", [&] {
            // A is bound to a double, not a Rational, so classify_walk's exactness gate rejects
            // the coefficient and the body brute-forces: 0.5 * (1 + 2 + 3) = 3.0, a double.
            session_vars().clear();
            session_vars().set("A", Value{0.5});
            EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} An"), Value{3.0});
            session_vars().clear();
        });

    // Each body's true value is astronomically large and cannot be written as a literal, so
    // the assertion is by alternative, not value.
    const std::vector<ArmCase> iterated_closed_arm_cases = {
        // Cap-exempt: 54M is far past kMaxIterations; the closed form is instant. The result
        // overflows int64, so it comes back a double.
        {.id = "is cap-exempt",
         .input = "\\sum_{n=1}^{54000000} (n^{2} - 3n)",
         .expected = Arm::Double},
        // The geometric closed form is O(log range): a 54M range that a brute loop could never
        // finish inside a test returns instantly, proving the geometric path handled it (not
        // the loop). 2^n overflows int64, and the geometric path uses BigReal (not double)
        // past that.
        {.id = "geometric is O(log range), not a loop",
         .input = "\\sum_{n=1}^{54000000} 2^{n}",
         .expected = Arm::Big},
        // G1's ratio = c^a is built by rat_pow (binary exponentiation), not a loop over the
        // range, so a huge range with a large (but not absurd) slope a still returns
        // instantly: proof the affine exponent closes rather than declining to brute (54M
        // terms brute could never finish).
        {.id = "affine exponent closes over a huge range",
         .input = "\\sum_{n=1}^{54000000} 2^{100n}",
         .expected = Arm::Big},
        // a = 1000000 makes the ratio c^a itself a ~1,000,000-bit number, still inside
        // kMaxRatioBits (8M): constructing it via rat_pow is fast (O(log a) squarings), and it
        // is far past kExactPowerBits, so the geometric sum lands in the BigReal branch, not a
        // Rational. Also the fence on the cap's lower end: this body closes today and must
        // keep closing, so the cap can never be tightened below it.
        {.id = "a large slope still returns a BigReal value",
         .input = "\\sum_{n=1}^{3} 2^{1000000n}",
         .expected = Arm::Big},
    };

    for (const auto &tc : iterated_closed_arm_cases) {
        test_detail::with_case(ctx, std::string("closed form :: ") + tc.id, [&] {
            tcalc::eval::reset_closed_form_taken();
            EXPECT_EQ(ctx, arm_of(eval_text(c, tc.input)), tc.expected);
            EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
        });
    }

    // The message text is the contract: it is asserted verbatim, and only after confirming
    // the body actually threw (a bare try/catch with no throw would otherwise let the message
    // assertion silently pass).
    const std::vector<MsgCase> iterated_closed_absurd_slope_cases = {
        // The throw fires from a bit-length estimate before any big computation runs, so
        // tripping it does not need a truly huge exponent: a = 5000000 puts the ratio past
        // kMaxRatioBits (8M, counted as base_bits * |a|), mirroring the var-free product's own
        // cap. Closing this body would mean a multi-minute exact -> BigReal conversion, so an
        // error is the honest answer, not a decline to a brute loop that cannot compute it
        // either.
        {.id = "an absurd slope throws, never declines",
         .input = "\\sum_{n=1}^{3} 2^{5000000n}",
         .expected = "Sum range is too large to compute."},
        // classify_walk serves both \sum and \prod, so the ratio-size cap must name whichever
        // operator called it: a \prod hitting the same cap reports "Product", not "Sum".
        {.id = "a prod's absurd slope throws with the product wording",
         .input = "\\prod_{n=1}^{3} 2^{5000000n}",
         .expected = "Product range is too large to compute."},
    };

    for (const auto &tc : iterated_closed_absurd_slope_cases) {
        test_detail::with_case(ctx, std::string("closed form :: ") + tc.id, [&] {
            EXPECT_THROWS(ctx, eval_text(c, tc.input));
            bool threw = false;
            try {
                eval_text(c, tc.input);
            } catch (const CalculatorError &e) {
                threw = true;
                EXPECT_EQ(ctx, std::string(e.what()), std::string(tc.expected));
            }
            EXPECT_EQ(ctx, threw, true);
        });
    }

    // Product-specific size guards, distinct from the shared ratio-size cap above: three
    // independent checks -- E's int64 overflow, count's uint64 wrap, and the var-free
    // product's kMaxIterations cap -- each proven with the exact range that trips it and no
    // other. All report the same message because the calling site is what differs, not the
    // wording.
    const std::vector<MsgCase> iterated_closed_product_guard_cases = {
        // E is quadratic in the range, so it overflows int64 long before a loop could finish.
        {.id = "geometric product's E overflowing int64 throws, not declines",
         .input = "\\prod_{n=1}^{5000000000} 2^{n}",
         .expected = "Product range is too large to compute."},
        // Here count = span + 1 wraps to 0, making c^count into 1, so the product would
        // silently return r^E. The coefficient is what exposes it: with c == 1 the wrong
        // answer equals the right one.
        {.id = "geometric product's count wrapping at the int64 extremes throws, not 0",
         .input = "\\prod_{n=-9223372036854775807-1}^{9223372036854775807} 3*2^{n}",
         .expected = "Product range is too large to compute."},
        // The var-free path raises c^count exactly, and one big-int squaring is a single
        // allocation the deadline cannot interrupt, so it keeps a size bound of its own.
        {.id = "a var-free product over a huge range is still capped",
         .input = "\\prod_{n=1}^{2000000} 3",
         .expected = "Product range is too large to compute."},
        // -...807-1 is exactly INT64_MIN; without the -1 the literal is off by one and the
        // span never reaches the wrap this pins.
        {.id = "a var-free product at the true INT64_MIN lower bound does not silently return 1",
         .input = "\\prod_{n=-9223372036854775807-1}^{9223372036854775807} 3",
         .expected = "Product range is too large to compute."},
        // base_bits <= 1 (root is 1) skips the bit-length check above; the slope's own
        // magnitude, built by exact multiplication of three int64 literals, still throws.
        {.id = "a trivial base under an absurd slope still throws",
         .input = "\\sum_{n=1}^{3} 1^{100000000*100000000*100000000n}",
         .expected = "Sum range is too large to compute."},
    };

    for (const auto &tc : iterated_closed_product_guard_cases) {
        test_detail::with_case(ctx, std::string("closed form :: ") + tc.id, [&] {
            EXPECT_THROWS(ctx, eval_text(c, tc.input));
            bool threw = false;
            try {
                eval_text(c, tc.input);
            } catch (const CalculatorError &e) {
                threw = true;
                EXPECT_EQ(ctx, std::string(e.what()), std::string(tc.expected));
            }
            EXPECT_EQ(ctx, threw, true);
        });
    }

    // Budget-gated proofs that a body closes instead of falling to brute: a huge range under a
    // 20 ms budget would blow straight through it if brute ran, so a returned value proves the
    // closed form short-circuited before the loop ever started (not a bare 54M call, so a
    // regression fails fast instead of hanging the suite). The shared wrapper -- set the
    // budget, run inside a try/catch, restore the budget even if the body throws, then assert
    // no throw fired -- is the whole point of this table. Both rows here are asserted by
    // alternative (sharing the Arm representation above) because the true result is
    // astronomically large and cannot be written as a literal; the G4 zero-coefficient proof
    // below is not, since its whole point is a specific value, so it keeps its own
    // `with_case` rather than being forced into this table.
    const std::vector<ArmCase> iterated_closed_budget_cases = {
        // G2 proof of closing, not brute: pre-G2 a Geo base under a literal power declined and
        // the brute loop hit the budget; G2 folds (2^n)^2 into one Geo term via ct_mul before
        // the loop ever starts, so it returns well inside the budget.
        {.id = "G2 closes a geo base under a literal power, not a loop",
         .input = "\\sum_{n=1}^{54000000} (2^{n})^{2}",
         .expected = Arm::Big},
        // Fix round 1 proof: a negative literal power on a Geo base closes too (the widened
        // guard), not just a positive one. Pre-fix this declines (Geo base + negative
        // exponent) and the brute loop over 54M terms hits the budget; post-fix ct_div inverts
        // the positive-power Geo term before the loop ever starts.
        {.id = "G2 closes a negative literal power on a geo base, not a loop",
         .input = "\\sum_{n=1}^{54000000} (2^{n})^{-1}",
         .expected = Arm::Big},
    };

    for (const auto &tc : iterated_closed_budget_cases) {
        test_detail::with_case(ctx, std::string("closed form :: ") + tc.id, [&] {
            tcalc::eval::set_eval_time_budget_ms(20);
            bool threw = false;
            std::optional<Value> v;
            try {
                v = eval_text(c, tc.input);
            } catch (const CalculatorError &) {
                threw = true;
            }
            tcalc::eval::set_eval_time_budget_ms(0); // restore the unlimited default
            EXPECT_EQ(ctx, threw, false);
            EXPECT_EQ(ctx, v.has_value() && arm_of(*v) == tc.expected, true);
        });
    }

    // G4 proof: 0*2^n folds ct_geo(0, 2) to Const(0), not a Geo term, so it now composes into
    // the var-free Prod arm (which only accepts Const) and closes over a huge range instead of
    // declining to brute. Budget-gated for the same reason as the two proofs above, but kept
    // out of that table: unlike those, the point here is a specific value (zero), not merely
    // an alternative, so the assertion stays an exact Value comparison.
    test_detail::with_case(
        ctx, "closed form :: G4 zero-coefficient geo term composes into the Prod arm", [&] {
            tcalc::eval::set_eval_time_budget_ms(20);
            bool threw = false;
            std::optional<Value> v;
            try {
                v = eval_text(c, "\\prod_{n=1}^{999999} 0*2^{n}");
            } catch (const CalculatorError &) {
                threw = true;
            }
            tcalc::eval::set_eval_time_budget_ms(0); // restore the unlimited default
            EXPECT_EQ(ctx, threw, false);
            EXPECT_EQ(ctx, v.has_value() && *v == Value{Rational(0)}, true);
        });

    // G1 declines when the coefficient's root is irrational, even though the ratio side would
    // have been exact (2^{n+1/2} = sqrt(2) * 2^n): the whole term is declined, not approximated,
    // so brute runs unchanged and closed-forms-enabled must match closed-forms-disabled exactly.
    test_detail::with_case(ctx, "closed form :: G1 declines an irrational coefficient", [&] {
        constexpr double eps = 1e-9;
        const char *bodies[] = {
            "\\sum_{n=1}^{4} 2^{n/2}",   // ratio itself irrational (sqrt(2))
            "\\sum_{n=1}^{4} 2^{n+1/2}", // ratio exact (2), coefficient sqrt(2) irrational
        };
        for (const char *body : bodies) {
            tcalc::eval::set_closed_forms_enabled(false);
            const Value brute = eval_text(c, body);
            tcalc::eval::set_closed_forms_enabled(true);
            const Value closed = eval_text(c, body);
            EXPECT_EQ(ctx, std::holds_alternative<double>(closed), true);
            EXPECT_EQ(ctx, std::holds_alternative<double>(brute), true);
            EXPECT_EQ(
                ctx, std::abs(std::get<double>(closed) - std::get<double>(brute)) < eps, true);
        }
    });

    // (-4)^{n/2} has no real even root at odd n (a domain error, not a rational-vs-irrational
    // question); G1 declines via exact_rational_root's own negative-even-root guard, and the
    // real evaluator's own fallback path is what actually runs either way, landing on NaN.
    test_detail::with_case(
        ctx, "closed form :: G1 declines a negative base under a fractional exponent", [&] {
            tcalc::eval::set_closed_forms_enabled(true);
            const Value v = eval_text(c, "\\sum_{n=1}^{3} (-4)^{n/2}");
            EXPECT_EQ(ctx, std::holds_alternative<double>(v), true);
            EXPECT_EQ(ctx, std::isnan(std::get<double>(v)), true);
        });

    // The fence holding Task 3 (G1, affine exponent) and Task 4 (G2, geo base under a literal
    // power) together: three different spellings of 4^n must all fold to the same value. All
    // three land on the same Rational, not just "closed independently".
    test_detail::with_case(ctx, "closed form :: three spellings of 4^n agree", [&] {
        const Value implicit_mul = eval_text(c, "\\sum_{n=1}^{4} 2^{n}2^{n}");
        const Value affine_exp = eval_text(c, "\\sum_{n=1}^{4} 2^{2n}");
        const Value geo_pow = eval_text(c, "\\sum_{n=1}^{4} (2^{n})^{2}");
        EXPECT_EQ(ctx, implicit_mul, Value{Rational(340)});
        EXPECT_EQ(ctx, affine_exp, Value{Rational(340)});
        EXPECT_EQ(ctx, geo_pow, Value{Rational(340)});
    });

    // G2, negative literal power: (2^n)^-1 is the reciprocal term (1/2)^n. Anchored to the same
    // known value both ways, not to a bare "it closed".
    test_detail::with_case(
        ctx, "closed form :: negative literal power on a geo base reciprocates", [&] {
            const Value geo_pow = eval_text(c, "\\sum_{n=1}^{5} (2^{n})^{-1}");
            const Value direct = eval_text(c, "\\sum_{n=1}^{5} (1/2)^{n}");
            EXPECT_EQ(ctx, geo_pow, Value{Rational(31, 32)});
            EXPECT_EQ(ctx, direct, Value{Rational(31, 32)});
        });

    // G3's headline case: (2^n - 2^n) is a like-term subtraction to zero. ct_add routes the
    // result through ct_geo, which folds a zero coefficient to Const(0) (Task 4), so this closes
    // to exactly Rational(0) via Faulhaber's O(1) formula -- not the Geo branch (which would
    // promote a huge range to BigReal) and not a brute loop (a 54,000,000-term range building
    // 2^n each step would never finish inside a test).
    test_detail::with_case(
        ctx, "closed form :: G3 folds 2^n - 2^n to exactly 0, closes not loops", [&] {
            const Value small = eval_text(c, "\\sum_{n=1}^{4} (2^{n}-2^{n})");
            EXPECT_EQ(ctx, small, Value{Rational(0)});
            // Budget-gated like the other G-proofs above: a 54,000,000-term range building 2^n
            // each step would blow well past 20ms if this fell to the brute loop, so a fast,
            // non-throwing, exactly-zero result proves the like-term fold ran, not a loop.
            tcalc::eval::set_eval_time_budget_ms(20);
            bool threw = false;
            std::optional<Value> huge;
            try {
                huge = eval_text(c, "\\sum_{n=1}^{54000000} (2^{n}-2^{n})");
            } catch (const CalculatorError &) {
                threw = true;
            }
            tcalc::eval::set_eval_time_budget_ms(0); // restore the unlimited default
            EXPECT_EQ(ctx, threw, false);
            EXPECT_EQ(ctx, huge.has_value() && *huge == Value{Rational(0)}, true);
            EXPECT_EQ(ctx, huge.has_value() && std::holds_alternative<Rational>(*huge), true);
        });

    // G3 declines a trig like term: sin(n)+sin(n) would need a structural equality on the
    // argument token vectors and the sampled k/phi, which classify_walk cannot do (no Calculator/
    // AngleUnit). It still brute-forces to the correct value.
    test_detail::with_case(
        ctx, "closed form :: G3 declines a trig like term, brute-forces correctly", [&] {
            const char *body = "\\sum_{n=1}^{5} (sin(n)+sin(n))";
            tcalc::eval::set_closed_forms_enabled(false);
            const Value brute = eval_text(c, body);
            tcalc::eval::set_closed_forms_enabled(true);
            const Value closed = eval_text(c, body);
            EXPECT_EQ(ctx, std::holds_alternative<double>(closed), true);
            EXPECT_EQ(ctx, std::holds_alternative<double>(brute), true);
            EXPECT_EQ(ctx, std::get<double>(closed), std::get<double>(brute));
        });

    // Trig sums close: differential closed-vs-brute (float, tolerance), plus an O(1) path proof
    // over a range no brute loop could finish, proving the closed path (not the loop) ran.
    test_detail::with_case(ctx, "closed form :: trig single term (radians)", [&] {
        constexpr double eps = 1e-9;
        const char *bodies[] = {
            "\\sum_{n=1}^{50} sin(n)",
            "\\sum_{n=1}^{50} cos(n)",
            "\\sum_{n=1}^{50} sin(2n)",
            "\\sum_{n=1}^{40} cos(3n)",
            "\\sum_{n=1}^{60} sin(n/2)",
            "\\sum_{n=1}^{50} 3sin(n)",
            "\\sum_{n=1}^{40} -cos(4n)",
            "\\sum_{n=1}^{50} sin(n+1)",
            "\\sum_{n=1}^{40} cos(2n+1)",
            "\\sum_{n=7}^{30} sin(n)",
            "\\sum_{n=0}^{25} cos(n)",
            "\\sum_{n=1}^{40} 2sin(3n+1)"};
        for (const char *body : bodies) {
            tcalc::eval::set_closed_forms_enabled(false);
            const Value brute = eval_text(c, body);
            tcalc::eval::set_closed_forms_enabled(true);
            const Value closed = eval_text(c, body);
            EXPECT_EQ(ctx, std::holds_alternative<double>(closed), true);
            EXPECT_EQ(ctx, std::holds_alternative<double>(brute), true);
            EXPECT_EQ(
                ctx, std::abs(std::get<double>(closed) - std::get<double>(brute)) < eps, true);
        }
        // Path proof: 54M terms return instantly and stay within the Dirichlet bound (~2.09).
        const Value big = eval_text(c, "\\sum_{n=1}^{54000000} sin(n)");
        EXPECT_EQ(ctx, std::holds_alternative<double>(big), true);
        EXPECT_EQ(ctx, std::abs(std::get<double>(big)) < 3.0, true);
    });

    // k and phi are sampled from the argument by point-eval, so a pi-based argument (irrational
    // in CppRat) still closes. A constant-argument body (k = 0) is the degenerate branch:
    // sum = count * trig(phi), O(1) over any range.
    test_detail::with_case(ctx, "closed form :: trig with π and constant bodies", [&] {
        constexpr double eps = 1e-9;
        const auto near = [&](const char *body, double want) {
            const Value v = eval_text(c, body);
            return std::holds_alternative<double>(v) && std::abs(std::get<double>(v) - want) < eps;
        };
        EXPECT_EQ(ctx, near("\\sum_{n=1}^{10} sin(π n)", 0.0), true);
        EXPECT_EQ(ctx, near("\\sum_{n=1}^{5} cos(π n)", -1.0), true);
        EXPECT_EQ(ctx, near("\\sum_{n=1}^{6} cos(π n)", 0.0), true);
        EXPECT_EQ(ctx, near("\\sum_{n=1}^{4} sin(π n/2)", 0.0), true);
        EXPECT_EQ(ctx, near("\\sum_{n=1}^{2} sin(π n/2)", 1.0), true);
        EXPECT_EQ(ctx, near("\\sum_{n=1}^{4} cos(π n/2)", 0.0), true);
        EXPECT_EQ(ctx, near("\\sum_{n=1}^{3} cos(π n/2)", -1.0), true);
        const auto val = [&](const char *bd) { return std::get<double>(eval_text(c, bd)); };
        EXPECT_EQ(
            ctx,
            std::abs(val("\\sum_{n=1}^{20} sin(n + pi/2)") - val("\\sum_{n=1}^{20} cos(n)")) < eps,
            true);
        EXPECT_EQ(
            ctx,
            std::abs(val("\\sum_{n=1}^{20} cos(n + pi)") + val("\\sum_{n=1}^{20} cos(n)")) < eps,
            true);
        // A π frequency that is a full turn (2 pi) hits the degenerate branch: closed, O(1).
        EXPECT_EQ(ctx, near("\\sum_{n=1}^{1000000000} sin(2π n)", 0.0), true);
        EXPECT_EQ(ctx, near("\\sum_{n=1}^{1000000000} sin(2)", 1e9 * std::sin(2.0)), true);
        // extreme bounds: b - a + 1 overflows int64 if computed there; must stay finite and
        // signed like sin(2)
        const Value big_count = eval_text(c, "\\sum_{n=-1}^{9223372036854775807} sin(2)");
        EXPECT_EQ(ctx, std::holds_alternative<double>(big_count), true);
        EXPECT_EQ(
            ctx,
            std::isfinite(std::get<double>(big_count)) && std::get<double>(big_count) > 0.0,
            true);
    });

    // The closed form must agree with brute in every angle unit, since the argument's radian
    // conversion is the calc's own (sin(n) means sin of n degrees in DEG).
    test_detail::with_case(ctx, "closed form :: trig honours the angle unit", [&] {
        constexpr double eps = 1e-9;
        const char *bodies[] = {"\\sum_{n=1}^{40} sin(n)", "\\sum_{n=1}^{40} cos(2n+1)"};
        for (auto unit : {Calculator::AngleUnit::DEG, Calculator::AngleUnit::GRAD}) {
            for (const char *body : bodies) {
                tcalc::eval::set_closed_forms_enabled(false);
                const double brute = std::get<double>(eval_text(c, body, unit));
                tcalc::eval::set_closed_forms_enabled(true);
                const double closed = std::get<double>(eval_text(c, body, unit));
                EXPECT_EQ(ctx, std::abs(closed - brute) < eps, true);
            }
        }
    });

    // Bodies that STAY in closed form (sums go through Faulhaber, var-free products through
    // c^count). The value is exact and equals brute force for these int64-range results.
    const std::vector<EvalCase> iterated_closed_cases = {
        {.id = "sum of squares, term rule",
         .input = "\\sum_{n=1}^{4} n^{2}",
         .expected = Value{Rational(30)}},
        {.id = "term rule with surrounding terms",
         .input = "2 + \\sum_{n=1}^{5} n^{2} - 4",
         .expected = Value{Rational(53)}},
        {.id = "parenthesised polynomial body",
         .input = "\\sum_{n=1}^{5} (n^{2} - 3n)",
         .expected = Value{Rational(10)}},
        {.id = "power of a binomial base",
         .input = "\\sum_{n=1}^{5} (n+2)^{3}",
         .expected = Value{Rational(775)}},
        {.id = "canonicalises to a lower degree",
         .input = "\\sum_{n=1}^{5} ((n+1)^{2} - n^{2})", // = sum of 2n+1
         .expected = Value{Rational(35)}},
        {.id = "full multi-term polynomial",
         .input = "\\sum_{n=1}^{4} (n^{3} + 2n^{2} - n + 5)",
         .expected = Value{Rational(170)}},
        {.id = "fraction with rational coefficients",
         .input = "\\sum_{n=1}^{6} \\frac{n^{2} - 1}{2}",
         .expected = Value{Rational(85, 2)}},
        {.id = "exact division n^2/n reduces to n",
         .input = "\\sum_{n=1}^{4} n^{2}/n", // = sum of n = 10
         .expected = Value{Rational(10)}},
        {.id = "exact division fills the hole (brute would 0/0 at n=1, so a value proves closed)",
         .input = "\\sum_{n=1}^{4} \\frac{n^{3}-1}{n-1}", // = sum of n^2+n+1 = 3+7+13+21
         .expected = Value{Rational(44)}},
        {.id = "product of factors convolved out",
         .input = "\\sum_{n=1}^{5} n(n+1)(n+2)",
         .expected = Value{Rational(420)}},
        {.id = "degree 4 exercises B_4",
         .input = "\\sum_{n=1}^{4} n^{4}",
         .expected = Value{Rational(354)}},
        {.id = "degree 5", .input = "\\sum_{n=1}^{4} n^{5}", .expected = Value{Rational(1300)}},
        {.id = "degree 6 exercises B_6",
         .input = "\\sum_{n=1}^{3} n^{6}",
         .expected = Value{Rational(794)}},
        {.id = "degree 20 stays closed (raised cap)",
         .input = "\\sum_{n=1}^{3} (n+1)^{10}(n-1)^{10}",
         .expected = Value{Rational(1073800873)}},
        {.id = "degree 24 exercises B_24 at the cap",
         .input = "\\sum_{n=1}^{3} (n+1)^{12}(n-1)^{12}",
         .expected = Value{Rational(68720008177)}},
        {.id = "geometric sum 2^n",
         .input = "\\sum_{n=1}^{5} 2^{n}", // 2+4+8+16+32
         .expected = Value{Rational(62)}},
        {.id = "geometric sum 3^n",
         .input = "\\sum_{n=1}^{4} 3^{n}", // 3+9+27+81
         .expected = Value{Rational(120)}},
        {.id = "geometric sum with a fractional ratio",
         .input = "\\sum_{n=1}^{5} (1/2)^{n}", // 1/2+1/4+1/8+1/16+1/32
         .expected = Value{Rational(31, 32)}},
        {.id = "geometric sum with a leading coefficient",
         .input = "\\sum_{n=1}^{4} 3*2^{n}", // 3*(2+4+8+16)
         .expected = Value{Rational(90)}},
        {.id = "geometric sum with a negative ratio",
         .input = "\\sum_{n=1}^{4} (-2)^{n}", // -2+4-8+16
         .expected = Value{Rational(10)}},
        {.id = "geometric sum over a range not starting at 1",
         .input = "\\sum_{n=2}^{4} 2^{n}", // 4+8+16
         .expected = Value{Rational(28)}},
        // G1: an affine exponent a*n + b is still geometric, ratio = c^a, coeff = c^b.
        {.id = "affine exponent, a=2",
         .input = "\\sum_{n=1}^{4} 2^{2n}", // 4+16+64+256
         .expected = Value{Rational(340)}},
        {.id = "affine exponent, a=3",
         .input = "\\sum_{n=1}^{3} 2^{3n}", // 8+64+512
         .expected = Value{Rational(584)}},
        {.id = "affine exponent, b=+1",
         .input = "\\sum_{n=1}^{4} 2^{n+1}", // 4+8+16+32
         .expected = Value{Rational(60)}},
        {.id = "affine exponent, b=-1",
         .input = "\\sum_{n=1}^{4} 2^{n-1}", // 1+2+4+8
         .expected = Value{Rational(15)}},
        {.id = "affine exponent, negated bare variable",
         .input = "\\sum_{n=1}^{4} 2^{-n}", // 1/2+1/4+1/8+1/16
         .expected = Value{Rational(15, 16)}},
        {.id = "affine exponent, a=2 and b=1",
         .input = "\\sum_{n=1}^{3} 2^{2n+1}", // 8+32+128
         .expected = Value{Rational(168)}},
        {.id = "affine exponent, negative integer a on a fractional base",
         .input = "\\sum_{n=1}^{4} (1/2)^{-n}", // 2+4+8+16
         .expected = Value{Rational(30)}},
        {.id = "affine exponent, a=2 on a negative base",
         .input = "\\sum_{n=1}^{3} (-2)^{2n}", // 4+16+64
         .expected = Value{Rational(84)}},
        {.id = "affine exponent, b=+1 on a negative base",
         .input = "\\sum_{n=1}^{4} (-2)^{n+1}", // 4-8+16-32
         .expected = Value{Rational(-20)}},
        {.id = "affine exponent, fractional a=1/2 with an exact root",
         .input = "\\sum_{n=1}^{4} 4^{n/2}", // 2+4+8+16
         .expected = Value{Rational(30)}},
        {.id = "affine exponent, fractional a=1/2, base 9",
         .input = "\\sum_{n=1}^{4} 9^{n/2}", // 3+9+27+81
         .expected = Value{Rational(120)}},
        {.id = "affine exponent, fractional a=1/3, base 8",
         .input = "\\sum_{n=1}^{4} 8^{n/3}", // 2+4+8+16
         .expected = Value{Rational(30)}},
        // (-8)^{n/3} = (-2)^n exactly (odd root of a negative base is fine), so this closes to
        // Rational 2796202. Brute disagrees: its int64 exact path gives up by n=22 and the
        // double retry evaluates std::pow(-8.0, 7.333...), a fractional power of a negative
        // base, landing on nan. The closed answer is the correct one -- do not "fix" it to
        // match brute's nan.
        {.id = "affine exponent, fractional a=1/3 on a negative base: exact where brute NaNs",
         .input = "\\sum_{n=1}^{22} (-8)^{n/3}",
         .expected = Value{Rational(2796202)}},
        {.id = "G1 composes with ct_div",
         .input = "\\sum_{n=1}^{3} \\frac{2^{2n}}{3^{n}}", // (4/3)+(16/9)+(64/27) = 148/27
         .expected = Value{Rational(148, 27)}},
        // G2: a Geo base under a literal integer power, (c r^n)^k = c^k (r^k)^n.
        {.id = "G2 geo base squared: (2^n)^2 = 4^n",
         .input = "\\sum_{n=1}^{4} (2^{n})^{2}", // 4+16+64+256
         .expected = Value{Rational(340)}},
        {.id = "G2 geo base cubed: (2^n)^3 = 8^n",
         .input = "\\sum_{n=1}^{3} (2^{n})^{3}", // 8+64+512
         .expected = Value{Rational(584)}},
        {.id = "G2 geo base to the zeroth power is 1",
         .input = "\\sum_{n=1}^{5} (2^{n})^{0}", // 1+1+1+1+1
         .expected = Value{Rational(5)}},
        {.id = "G2 fractional geo base squared: ((1/2)^n)^2 = (1/4)^n",
         .input = "\\sum_{n=1}^{5} ((1/2)^{n})^{2}", // 1/4+1/16+1/64+1/256+1/1024
         .expected = Value{Rational(341, 1024)}},
        // G2, negative literal power on a Geo base: (c r^n)^-k = (1/c^k)(1/r^k)^n, still
        // geometric. (2^n)^-2 = (1/4)^n, the same value as ((1/2)^n)^2 above.
        {.id = "G2 negative literal power squared on a geo base",
         .input = "\\sum_{n=1}^{5} (2^{n})^{-2}", // 1/4+1/16+1/64+1/256+1/1024
         .expected = Value{Rational(341, 1024)}},
        // G2 on a fractional-ratio base: ((1/2)^n)^-1 = 2^n, the same value as the plain
        // "geometric sum 2^n" case above.
        {.id = "G2 negative literal power on a fractional-ratio geo base",
         .input = "\\sum_{n=1}^{5} ((1/2)^{n})^{-1}", // 2+4+8+16+32
         .expected = Value{Rational(62)}},
        {.id = "var-free product", .input = "\\prod_{n=1}^{5} 3", .expected = Value{Rational(243)}},
        {.id = "var-free fractional product",
         .input = "\\prod_{n=1}^{10} (1/2)",
         .expected = Value{Rational(1, 1024)}},
        {.id = "var-free negative product",
         .input = "\\prod_{n=1}^{5} (-2)",
         .expected = Value{Rational(-32)}},
        // G3: like-term folding, c1 r^n + c2 r^n = (c1+c2) r^n, for equal ratios.
        {.id = "G3 like term: 2^n + 2^n doubles the coefficient",
         .input = "\\sum_{n=1}^{4} (2^{n}+2^{n})", // 2*(2+4+8+16)
         .expected = Value{Rational(60)}},
        {.id = "G3 like term: 3*2^n + 2^n combines to 4*2^n",
         .input = "\\sum_{n=1}^{4} (3*2^{n}+2^{n})", // 4*(2+4+8+16)
         .expected = Value{Rational(120)}},
        {.id = "G3 like term: 2^n/2 + 2^n combines to (3/2)*2^n",
         .input = "\\sum_{n=1}^{4} (2^{n}/2+2^{n})", // (3/2)*(2+4+8+16)
         .expected = Value{Rational(45)}},
        // Geometric product: exponents add across a product, c^count * r^E where
        // E = sum_{n=a}^{b} n.
        {.id = "geometric product 2^n",
         .input = "\\prod_{n=1}^{5} 2^{n}", // 2*4*8*16*32
         .expected = Value{Rational(32768)}},
        {.id = "geometric product with a leading coefficient",
         .input = "\\prod_{n=1}^{4} 3*2^{n}", // (3*2)*(3*4)*(3*8)*(3*16)
         .expected = Value{Rational(82944)}},
        {.id = "geometric product with a fractional ratio",
         .input = "\\prod_{n=1}^{4} (1/2)^{n}", // (1/2)*(1/4)*(1/8)*(1/16)
         .expected = Value{Rational(1, 1024)}},
        {.id = "geometric product over a range straddling zero, E == 0",
         .input = "\\prod_{n=-2}^{2} 2^{n}", // 2^-2 * 2^-1 * 2^0 * 2^1 * 2^2, E = 0
         .expected = Value{Rational(1)}},
        {.id = "geometric product with a negative E gives a reciprocal",
         .input = "\\prod_{n=-3}^{-1} 2^{n}", // 2^-3 * 2^-2 * 2^-1, E = -6
         .expected = Value{Rational(1, 64)}},
        {.id = "geometric product with a negative ratio, E even",
         .input = "\\prod_{n=1}^{4} (-2)^{n}", // E = 10
         .expected = Value{Rational(1024)}},
        {.id = "geometric product with a negative ratio, E odd",
         .input = "\\prod_{n=1}^{5} (-2)^{n}", // E = 15
         .expected = Value{Rational(-32768)}},
        // Range 4..6 throughout below: it clears 1/(n-3)'s and n/(n-2)'s poles in the sibling
        // brute table, so one range serves every body.
        {.id = "bare variable body", .input = "\\sum_{n=4}^{6} n", .expected = Value{Rational(15)}},
        // The parens are load-bearing: bare, the top-level `-` would end the sum body.
        {.id = "quadratic minus linear",
         .input = "\\sum_{n=4}^{6} (n^{2}-3n)",
         .expected = Value{Rational(32)}},
        {.id = "polynomial over a constant divisor, Op arm",
         .input = "\\sum_{n=4}^{6} (n^{2}-1)/2",
         .expected = Value{Rational(37)}},
        {.id = "linear with a coefficient",
         .input = "\\sum_{n=4}^{6} 2n",
         .expected = Value{Rational(30)}},
        {.id = "a rational var-free constant body",
         .input = "\\sum_{n=4}^{6} 5",
         .expected = Value{Rational(15)}},
        {.id = "trailing zero coefficient trimmed",
         .input = "\\sum_{n=4}^{6} ((n+1)^{2}-n^{2})", // = sum of 2n+1
         .expected = Value{Rational(33)}},
        {.id = "degree 24 monomial at the cap",
         .input = "\\sum_{n=4}^{6} n^{24}",
         .expected = Value{Rational(4798267458073718177)}},
        {.id = "exact division by the variable, Op arm",
         .input = "\\sum_{n=4}^{6} n^{2}/n",
         .expected = Value{Rational(15)}},
        {.id = "exact division by a linear divisor, Frac arm",
         .input = "\\sum_{n=4}^{6} \\frac{n^{3}-1}{n-1}", // = sum of n^2+n+1
         .expected = Value{Rational(95)}},
        {.id = "a var-free power folds to a constant",
         .input = "\\sum_{n=4}^{6} 2^{-3}",
         .expected = Value{Rational(3, 8)}},
        {.id = "an exponent expression folding to an integer",
         .input = "\\sum_{n=4}^{6} n^{3-1}", // = n^2
         .expected = Value{Rational(77)}},
        {.id = "geometric body over a shifted range",
         .input = "\\sum_{n=4}^{6} 2^{n}", // 16+32+64
         .expected = Value{Rational(112)}},
        {.id = "G2 geo base squared over a shifted range",
         .input = "\\sum_{n=4}^{6} (2^{n})^{2}",
         .expected = Value{Rational(5376)}},
        {.id = "G1 affine exponent over a shifted range",
         .input = "\\sum_{n=4}^{6} 2^{2n}",
         .expected = Value{Rational(5376)}},
    };

    // Each row asserts both the value and that the closed-form path is the one that produced it.
    for (const auto &tc : iterated_closed_cases) {
        test_detail::with_case(ctx, std::string("closed form :: ") + tc.id, [&] {
            tcalc::eval::reset_closed_form_taken();
            EXPECT_EQ(ctx, eval_text(c, tc.input), tc.expected);
            EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
        });
    }

    // Bodies carrying an irrational constant: the walk keeps the constant's identity, so these
    // close symbolically and only become a double at the end.
    const auto real_of = [&](const char *body) { return std::get<double>(eval_text(c, body)); };
    const double pi = real_of("π");
    const double euler = real_of("e");
    const double boltzmann = real_of("k");
    const double sin_sum = real_of("\\sum_{n=1}^{10} sin(n)");

    const std::vector<NearCase> iterated_symbolic_cases = {
        {.id = "a bare constant body", .input = "\\sum_{n=1}^{4} π", .expected = 4 * pi},
        {.id = "scaled polynomial", .input = "\\sum_{n=1}^{4} π n", .expected = 10 * pi},
        {.id = "scaled square", .input = "\\sum_{n=1}^{4} π n^{2}", .expected = 30 * pi},
        {.id = "scaled geometric", .input = "\\sum_{n=1}^{5} π 2^{n}", .expected = 62 * pi},
        {.id = "polynomial over a constant", .input = "\\sum_{n=1}^{4} n/π", .expected = 10 / pi},
        {.id = "a constant other than pi", .input = "\\sum_{n=1}^{4} e n", .expected = 10 * euler},
        {.id = "scaled trig", .input = "\\sum_{n=1}^{10} π sin(n)", .expected = pi * sin_sum},
        {.id = "trig over a constant",
         .input = "\\sum_{n=1}^{10} sin(n)/π",
         .expected = sin_sum / pi},
        {.id = "a measured physics constant",
         .input = "\\sum_{n=1}^{10} k sin(n)",
         .expected = boltzmann * sin_sum},
        {.id = "equal symbols add",
         .input = "\\sum_{n=1}^{4} (π n^{2} + π n)",
         .expected = 40 * pi},
        {.id = "a literal power raises the symbol",
         .input = "\\sum_{n=1}^{4} (π n)^{2}",
         .expected = 30 * pi * pi},
        {.id = "two constants in one product",
         .input = "\\sum_{n=1}^{4} π e n",
         .expected = 10 * pi * euler},
        {.id = "unlike symbols still close, as one number",
         .input = "\\sum_{n=1}^{4} (5 + π)",
         .expected = 4 * (5 + pi)},
        {.id = "unlike symbols on a polynomial",
         .input = "\\sum_{n=1}^{4} (π n^{2} + n)",
         .expected = 30 * pi + 10},
    };

    for (const auto &tc : iterated_symbolic_cases) {
        test_detail::with_case(ctx, std::string("iterated symbolic :: ") + tc.id, [&] {
            tcalc::eval::reset_closed_form_taken();
            const Value v = eval_text(c, tc.input);
            EXPECT_EQ(ctx, std::holds_alternative<double>(v), true);
            EXPECT_EQ(ctx, near_rel(std::get<double>(v), tc.expected), true);
            EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
        });
    }

    // Every pi cancels at the coefficient level, so this is 2n^2 - n and never becomes a double.
    test_detail::with_case(ctx, "iterated symbolic :: a body whose constants cancel exactly", [&] {
        tcalc::eval::reset_closed_form_taken();
        EXPECT_EQ(
            ctx,
            eval_text(c, "\\sum_{n=1}^{4} ((π-n)^{2} - π^{2} + n^{2} + 2π n - n)"),
            Value{Rational(50)});
        EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
    });

    // A double-bound variable is a symbol too, so it cancels the same way.
    test_detail::with_case(ctx, "iterated symbolic :: a double-bound variable cancels", [&] {
        session_vars().clear();
        session_vars().set("A", Value{0.3});
        tcalc::eval::reset_closed_form_taken();
        EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{4} (A n - A n + n)"), Value{Rational(10)});
        EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
        session_vars().clear();
    });

    // The exponent side keeps its guard: n^{pi} has no closed form, and without the guard the
    // walk reads the exponent's rational part as 1 and answers `sum n`.
    test_detail::with_case(ctx, "iterated symbolic :: a symbol in an exponent declines", [&] {
        tcalc::eval::reset_closed_form_taken();
        const Value v = eval_text(c, "\\sum_{n=1}^{4} n^{π}");
        const double want =
            std::pow(1.0, pi) + std::pow(2.0, pi) + std::pow(3.0, pi) + std::pow(4.0, pi);
        EXPECT_EQ(ctx, near_rel(std::get<double>(v), want), true);
        EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), false);
    });

    // A constant in the RATIO, not the coefficient: the ratio cannot factor out of the sum, so
    // these resolve to a double before the geometric formula runs.
    const auto powers = [](double base) {
        double acc = 0.0;
        for (int m = 1; m <= 4; ++m)
            acc += std::pow(base, m);
        return acc;
    };

    const std::vector<NearCase> iterated_symbolic_ratio_cases = {
        {.id = "a constant as the ratio", .input = "\\sum_{n=1}^{4} π^{n}", .expected = powers(pi)},
        {.id = "a constant inside the base",
         .input = "\\sum_{n=1}^{4} (2π)^{n}",
         .expected = powers(2 * pi)},
        {.id = "a constant in an affine exponent",
         .input = "\\sum_{n=1}^{4} 2^{π n}",
         .expected = powers(std::pow(2.0, pi))},
    };

    for (const auto &tc : iterated_symbolic_ratio_cases) {
        test_detail::with_case(ctx, std::string("iterated symbolic ratio :: ") + tc.id, [&] {
            tcalc::eval::reset_closed_form_taken();
            const Value v = eval_text(c, tc.input);
            EXPECT_EQ(ctx, std::holds_alternative<double>(v), true);
            EXPECT_EQ(ctx, near_rel(std::get<double>(v), tc.expected), true);
            EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
        });
    }

    // A zero-valued symbol is a zero divisor whatever the coefficient says.
    test_detail::with_case(
        ctx, "iterated symbolic :: a zero-valued variable is a zero divisor", [&] {
            session_vars().clear();
            session_vars().set("Z", Value{0.0});
            EXPECT_THROWS(ctx, eval_text(c, "\\sum_{n=1}^{3} n/Z"));
            EXPECT_THROWS(ctx, eval_text(c, "\\sum_{n=1}^{3} sin(n)/Z"));
            session_vars().clear();
        });

    // Arm-ladder agreement, the point of the geometric-product approach: closed and brute must
    // land in the very same arm (Rational/double/BigReal) at every range, not merely the same
    // numeric value. Compared live against brute (not a hardcoded literal) so a future rewrite
    // that reintroduces a hand-rolled exactness gate fails here the moment it diverges. A BigReal
    // compares at its documented 50 significant digits, not raw variant equality: brute's
    // incremental multiply and the closed form's direct r^E squaring take different rounding
    // paths through cpp_dec_float's undocumented guard digits past that precision, which is
    // noise, not a real divergence -- Rational and double agree bit-for-bit at every range here.
    test_detail::with_case(
        ctx, "closed form :: geometric product arm ladder matches brute at every range", [&] {
            const char *bodies[] = {
                "\\prod_{n=1}^{5} 2^{n}",
                "\\prod_{n=1}^{10} 2^{n}",
                "\\prod_{n=1}^{20} 2^{n}",
                "\\prod_{n=1}^{60} 2^{n}",
            };
            for (const char *body : bodies) {
                tcalc::eval::set_closed_forms_enabled(false);
                const Value brute = eval_text(c, body);
                tcalc::eval::set_closed_forms_enabled(true);
                tcalc::eval::reset_closed_form_taken();
                const Value closed = eval_text(c, body);
                EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
                EXPECT_EQ(ctx, arm_of(closed), arm_of(brute));
                if (const auto *b = std::get_if<BigReal>(&brute)) {
                    // Deliberately NOT `closed == brute` here: raw variant equality on two
                    // independently-computed BigReals compares cpp_dec_float's full internal
                    // digit count, which exceeds the type's documented 50-significant-digit
                    // precision. Brute's incremental multiply and the closed form's direct r^E
                    // squaring take different rounding paths through those extra undocumented
                    // guard digits and disagree there even though both are correct to 50
                    // significant digits -- measured, not assumed: raw `==` fails here today. Do
                    // not "tighten" this back to `==`; compare at the documented precision.
                    const auto *cl = std::get_if<BigReal>(&closed);
                    const bool same_at_precision =
                        cl != nullptr && cl->str(50, std::ios_base::scientific) ==
                                             b->str(50, std::ios_base::scientific);
                    EXPECT_EQ(ctx, same_at_precision, true);
                } else {
                    // Rational and double DO agree bit-for-bit at these ranges (verified), so
                    // exact equality is the right, stronger check for those two arms.
                    EXPECT_EQ(ctx, closed, brute);
                }
            }
        });

    // Composition with the normalisation rules already on this branch (G1's affine exponent,
    // G2's geo base under a literal power): all three spellings of 4^n must land on the same
    // value once the product side closes them too.
    test_detail::with_case(
        ctx, "closed form :: geometric product composes with affine exponent and geo-base G2", [&] {
            tcalc::eval::set_closed_forms_enabled(false);
            const Value brute = eval_text(c, "\\prod_{n=1}^{10} 4^{n}");
            tcalc::eval::set_closed_forms_enabled(true);
            // Reset and check around each call, not once across all three: the flag is a
            // single yes/no, so only a per-call check can prove each of the three spellings
            // closed rather than just one of them.
            tcalc::eval::reset_closed_form_taken();
            const Value affine_exp = eval_text(c, "\\prod_{n=1}^{10} 2^{2n}");
            EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
            tcalc::eval::reset_closed_form_taken();
            const Value geo_pow = eval_text(c, "\\prod_{n=1}^{10} (2^{n})^{2}");
            EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
            tcalc::eval::reset_closed_form_taken();
            const Value plain = eval_text(c, "\\prod_{n=1}^{10} 4^{n}");
            EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
            EXPECT_EQ(ctx, affine_exp, brute);
            EXPECT_EQ(ctx, geo_pow, brute);
            EXPECT_EQ(ctx, plain, brute);
        });

    // Closes rather than loops: a million-term range under a 20 ms budget would blow straight
    // through it if brute ran, so a returned value (not a timeout) proves the closed form
    // short-circuited before the loop ever started.
    test_detail::with_case(
        ctx, "closed form :: geometric product over a million terms closes, not loops", [&] {
            tcalc::eval::set_eval_time_budget_ms(20);
            bool threw = false;
            std::optional<Value> v;
            try {
                v = eval_text(c, "\\prod_{n=1}^{1000000} 2^{n}");
            } catch (const CalculatorError &) {
                threw = true;
            }
            tcalc::eval::set_eval_time_budget_ms(0); // restore the unlimited default
            EXPECT_EQ(ctx, threw, false);
            EXPECT_EQ(ctx, v.has_value() && arm_of(*v) == Arm::Big, true);
        });

    // Unsimplifiable rational bodies (nonzero remainder) whose divisor hits zero inside the
    // range: they decline the closed form, brute-force, and raise the calc's math error at the
    // zero point. The point is that the app errors gracefully, not that it crashes or loops.
    const std::vector<const char *> brute_zero_divisor_cases = {
        "\\sum_{n=1}^{5} 1/(n-3)",        // 1/(n-3): brute, n=3 -> 1/0
        "\\sum_{n=1}^{5} \\frac{n}{n-2}", // n/(n-2): remainder 2, brute, n=2 -> n/0
    };
    for (const char *s : brute_zero_divisor_cases) {
        test_detail::with_case(
            ctx, std::string("iterated brute :: unsimplifiable zero divisor errors :: ") + s, [&] {
                EXPECT_THROWS(ctx, eval_text(c, s));
                try {
                    eval_text(c, s);
                } catch (const CalculatorError &e) {
                    EXPECT_EQ(ctx, std::string(e.what()), std::string("Math error"));
                }
            });
    }

    // Bodies that FALL to brute force (not a polynomial for a sum, degree >= 1 for a product).
    // Brute still computes the correct value; the closed-form matcher just declines.
    const std::vector<EvalCase> iterated_brute_cases = {
        {.id = "sum: division by the variable",
         .input = "\\sum_{n=1}^{4} 1/n",
         .expected = Value{Rational(25, 12)}},
        {.id = "sum: a postfix factorial",
         .input = "\\sum_{n=1}^{4} n!",
         .expected = Value{33.0}}, // factorial has no Rational arm, so this is a double
        {.id = "sum: a function-call mask",
         .input = "\\sum_{n=1}^{3} n(1-mod(n,2))",
         .expected = Value{BigReal("2")}}, // mod has no Rational kernel, promotes to BigReal
        {.id = "sum: a divisor containing the variable",
         .input = "\\sum_{n=1}^{3} \\frac{n^{2}}{n+1}",
         .expected = Value{Rational(49, 12)}},
        {.id = "product: degree-1 body",
         .input = "\\prod_{n=1}^{4} n",
         .expected = Value{Rational(24)}},
        {.id = "product: a shifted linear body",
         .input = "\\prod_{n=1}^{4} (n+1)",
         .expected = Value{Rational(120)}},
        {.id = "product: squares",
         .input = "\\prod_{n=1}^{3} n^{2}",
         .expected = Value{Rational(36)}},
        {.id = "product: a body with a coefficient",
         .input = "\\prod_{n=1}^{4} 2n",
         .expected = Value{Rational(384)}},
        {.id = "product: a non-monomial body",
         .input = "\\prod_{n=1}^{3} (n^{2}+1)",
         .expected = Value{Rational(100)}},
        // G3 still declines: different ratios are genuinely two terms (splitting's job, not
        // this task's), and mixed shapes (Geo + Const, Geo + Poly) are not like terms at all.
        {.id = "G3 declines different ratios: 2^n + 3^n",
         .input = "\\sum_{n=1}^{4} (2^{n}+3^{n})", // (2+4+8+16) + (3+9+27+81)
         .expected = Value{Rational(150)}},
        {.id = "G3 declines mixed shape: 2^n + 5",
         .input = "\\sum_{n=1}^{4} (2^{n}+5)", // (2+4+8+16) + 4*5
         .expected = Value{Rational(50)}},
        {.id = "G3 declines mixed shape: 2^n + n^2",
         .input = "\\sum_{n=1}^{4} (2^{n}+n^{2})", // (2+4+8+16) + (1+4+9+16)
         .expected = Value{Rational(60)}},
        // degree 2 exponent: G1 is degree-1 only, so this declines and brute-forces, proving
        // 2^{2n}'s sibling with a nonlinear exponent stays correct (not widened too).
        {.id = "quadratic exponent still brute-forces correctly",
         .input = "\\sum_{n=1}^{3} 2^{n^{2}}", // 2+16+512
         .expected = Value{Rational(530)}},
        // G2 must still decline a variable power on a Geo base: (2^n)^n is 2^(n^2), no closed
        // form. Same value as the quadratic-exponent case above, written the Geo-base way.
        {.id = "G2 declines a variable power on a geo base, brute-forces correctly",
         .input = "\\sum_{n=1}^{3} (2^{n})^{n}", // 2+16+512
         .expected = Value{Rational(530)}},
        // G4's r == 0 decline stays load-bearing: 0^0 == 1 in this calc, so a range starting at
        // n=0 differs from one that does not, even though both bodies are "0^n". Both brute
        // through a zero base, which promotes to BigReal (not the type, the number is what
        // matters here: 1 vs 0).
        {.id = "G4 guard: 0^n range including n=0 is 1 (0^0 == 1)",
         .input = "\\sum_{n=0}^{2} 0^{n}",
         .expected = Value{BigReal("1")}},
        {.id = "G4 guard: 0^n range excluding n=0 is 0",
         .input = "\\sum_{n=1}^{3} 0^{n}",
         .expected = Value{BigReal("0")}},
        // ct_geo declines a zero ratio, so the product branch never sees a Geo term here; the
        // range avoids 0^0, which would make the body's value depend on the bound, not the ratio.
        {.id = "geometric product declines a zero ratio, brute-forces to 0",
         .input = "\\prod_{n=1}^{3} 0^{n}",
         .expected = Value{BigReal("0")}},
        {.id = "sum: 1/n over a shifted range",
         .input = "\\sum_{n=4}^{6} 1/n",
         .expected = Value{Rational(37, 60)}},
        {.id = "sum: a divisor depending on the variable",
         .input = "\\sum_{n=4}^{6} 1/(n-3)",
         .expected = Value{Rational(11, 6)}},
        {.id = "sum: an exponent past kMaxDegree on a const base",
         .input = "\\sum_{n=4}^{6} 2^{25}",
         .expected = Value{Rational(100663296)}},
        {.id = "sum: a poly base under a negative exponent",
         .input = "\\sum_{n=4}^{6} n^{-2}",
         .expected = Value{Rational(469, 3600)}},
        {.id = "sum: a nonzero division remainder, Op arm",
         .input = "\\sum_{n=4}^{6} n^{2}/(n+1)",
         .expected = Value{Rational(2627, 210)}},
        {.id = "sum: a nonzero division remainder, Frac arm",
         .input = "\\sum_{n=4}^{6} \\frac{n}{n-2}",
         .expected = Value{Rational(31, 6)}},
    };

    for (const auto &tc : iterated_brute_cases) {
        test_detail::with_case(ctx, std::string("iterated brute :: ") + tc.id, [&] {
            tcalc::eval::reset_closed_form_taken();
            EXPECT_EQ(ctx, eval_text(c, tc.input), tc.expected);
            EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), false);
        });
    }

    // The same 4..6 range as the tables above, for bodies whose value cannot be an EvalCase:
    // a Value compares exactly and these are irrational, overflowed or throwing.
    test_detail::with_case(ctx, "closed form :: a trig body over a shifted range", [&] {
        tcalc::eval::reset_closed_form_taken();
        const Value v = eval_text(c, "\\sum_{n=4}^{6} sin(n)");
        EXPECT_EQ(ctx, near_rel(std::get<double>(v), -1.9951422681699926), true);
        EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
    });

    test_detail::with_case(ctx, "iterated brute :: degree 25 is one past the Bernoulli table", [&] {
        // The exact sum overflows int64, so brute lands on a double.
        tcalc::eval::reset_closed_form_taken();
        const Value v = eval_text(c, "\\sum_{n=4}^{6} n^{25}");
        EXPECT_EQ(ctx, near_rel(std::get<double>(v), 2.8729437153713496e+19), true);
        EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), false);
    });

    test_detail::with_case(ctx, "iterated brute :: a const exponent that is not an integer", [&] {
        tcalc::eval::reset_closed_form_taken();
        const Value v = eval_text(c, "\\sum_{n=4}^{6} 2^{1/2}"); // 3*sqrt(2)
        EXPECT_EQ(ctx, near_rel(std::get<double>(v), 4.242640687119286), true);
        EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), false);
    });

    test_detail::with_case(
        ctx, "closed_forms :: a literal-zero divisor throws in both spellings", [&] {
            for (const char *s : {"\\sum_{n=4}^{6} n/0", "\\sum_{n=4}^{6} \\frac{n}{0}"}) {
                EXPECT_THROWS(ctx, eval_text(c, s));
                try {
                    eval_text(c, s);
                } catch (const CalculatorError &e) {
                    EXPECT_EQ(ctx, std::string(e.what()), std::string("Math error"));
                }
            }
        });

    // Neither purely closed nor purely brute: the outer sum's body is the inner \sum token
    // itself, not a polynomial in q, so the outer level declines and brute-forces over q = 1, 2.
    // But each of those two outer iterations binds q to a concrete value before evaluating the
    // inner sum, and qm is then a degree-1 polynomial in m (coefficient q), so the inner level
    // closes on every one of those outer steps.
    test_detail::with_case(
        ctx, "iterated mixed :: nested sum, outer declines, inner closes on every outer step", [&] {
            tcalc::eval::reset_closed_form_taken();
            EXPECT_EQ(ctx, eval_text(c, "\\sum_{q=1}^{2} \\sum_{m=1}^{2} qm"), Value{Rational(9)});
            EXPECT_EQ(ctx, tcalc::eval::closed_form_taken(), true);
        });

    test_detail::with_case(
        ctx, "closed form :: a var-free product at the int64 extremes does not overflow", [&] {
            // first and last sit near the int64 extremes: last - first overflows a signed
            // 64-bit subtraction. The count must be computed in uint64 (matching the
            // Sum extreme-bounds test above), so this throws range-too-large instead of
            // silently wrapping to a near-zero count and returning 1.
            EXPECT_THROWS(
                ctx, eval_text(c, "\\prod_{n=-9223372036854775807}^{9223372036854775807} 3"));
        });

    test_detail::with_case(
        ctx,
        "closed_forms :: division by a literal-zero divisor raises the div-by-zero error",
        [&] {
            // A var-free zero divisor is caught by the matcher itself and throws the calc's
            // normal division error, matching what brute force would have raised anyway.
            EXPECT_THROWS(ctx, eval_text(c, "\\sum_{n=1}^{3} n/0"));
            try {
                eval_text(c, "\\sum_{n=1}^{3} n/0");
            } catch (const CalculatorError &e) {
                EXPECT_EQ(ctx, std::string(e.what()), std::string("Math error"));
            }
        });

    test_detail::with_case(
        ctx,
        "closed_forms :: a huge div-by-zero range reports the math error, not range-too-large",
        [&] {
            // classify_walk walks the body before any size check, so a var-free zero divisor
            // surfaces the real div-by-zero error rather than being masked by a range limit.
            EXPECT_THROWS(ctx, eval_text(c, "\\sum_{n=1}^{2000000} n/0"));
            try {
                eval_text(c, "\\sum_{n=1}^{2000000} n/0");
            } catch (const CalculatorError &e) {
                EXPECT_EQ(ctx, std::string(e.what()), std::string("Math error"));
            }
        });

    // A zero base under a negative affine exponent (0^{-n}) is a division by zero, not a ratio:
    // affine_pow must decline it explicitly rather than letting rat_pow divide by zero, which
    // would otherwise escape as a raw boost exception instead of the calc's own math error.
    test_detail::with_case(
        ctx, "closed form :: a zero base under a negative exponent raises the math error", [&] {
            EXPECT_THROWS(ctx, eval_text(c, "\\sum_{n=1}^{3} 0^{-n}"));
            try {
                eval_text(c, "\\sum_{n=1}^{3} 0^{-n}");
            } catch (const CalculatorError &e) {
                EXPECT_EQ(ctx, std::string(e.what()), std::string("Math error"));
            }
        });
}
