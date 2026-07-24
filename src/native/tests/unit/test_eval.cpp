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

#include "calc/pub/error_messages.hpp"
#include "eval/internal/closed_forms.hpp"
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
/// Case row for a rejected expression: source text -> nothing, it must throw.
using RejectCase = Case<const char *, std::monostate>;
/// Case row for a rejected expression whose message text is part of the contract.
using MsgCase = Case<const char *, const char *>;
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
        EXPECT_EQ(ctx, eval_text(c, "sin(90)", Calculator::AngleUnit::DEG), Value{1.0});
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

    test_detail::with_case(ctx, "closed_forms :: canonicalise polynomial bodies", [&] {
        using tcalc::eval::canonicalise;
        using tcalc::eval::CppRat;
        const auto poly = [](const char *body) {
            return canonicalise(
                tcalc::eval::shunting_yard(tcalc::parser::tokenize(body).tokens), "n");
        };
        EXPECT_EQ(ctx, poly("n").value(), (std::vector<CppRat>{CppRat(0), CppRat(1)}));
        EXPECT_EQ(
            ctx, poly("n^{2}-3n").value(), (std::vector<CppRat>{CppRat(0), CppRat(-3), CppRat(1)}));
        EXPECT_EQ(
            ctx,
            poly("(n^{2}-1)/2").value(),
            (std::vector<CppRat>{CppRat(-1, 2), CppRat(0), CppRat(1, 2)}));
        EXPECT_EQ(ctx, poly("2n").value(), (std::vector<CppRat>{CppRat(0), CppRat(2)}));
        EXPECT_EQ(ctx, poly("5").value(), (std::vector<CppRat>{CppRat(5)}));
        // trailing zero trimmed: (n+1)^2 - n^2 = 2n + 1
        EXPECT_EQ(
            ctx, poly("(n+1)^{2}-n^{2}").value(), (std::vector<CppRat>{CppRat(1), CppRat(2)}));
        // degree exactly at the cap is still accepted
        EXPECT_EQ(ctx, poly("n^{24}").has_value(), true);
    });

    test_detail::with_case(ctx, "closed_forms :: canonicalise rejects non-polynomials", [&] {
        using tcalc::eval::canonicalise;
        const auto poly = [](const char *body) {
            return canonicalise(
                tcalc::eval::shunting_yard(tcalc::parser::tokenize(body).tokens), "n");
        };
        EXPECT_EQ(ctx, poly("sin(n)").has_value(), false);  // a Call
        EXPECT_EQ(ctx, poly("1/n").has_value(), false);     // division by the variable
        EXPECT_EQ(ctx, poly("1/(n-3)").has_value(), false); // divisor depends on the var
        EXPECT_EQ(ctx, poly("2^{n}").has_value(), false);   // variable exponent
        EXPECT_EQ(ctx, poly("\\pi n").has_value(), false);  // irrational coefficient
        EXPECT_EQ(ctx, poly("n^{25}").has_value(), false);  // degree exceeds Bernoulli table
        EXPECT_EQ(ctx, poly("2^{25}").has_value(), false);  // exponent exceeds kMaxDegree
        // a var-free zero divisor always errors, even without a bound loop: it throws the
        // calc's normal division error instead of silently declining to brute force.
        EXPECT_THROWS(ctx, poly("n/0"));          // literal-zero divisor, Op::Div arm
        EXPECT_THROWS(ctx, poly("\\frac{n}{0}")); // literal-zero divisor, Frac arm
    });

    test_detail::with_case(
        ctx, "closed form :: a double-bound session variable falls to brute", [&] {
            // A is bound to a double, not a Rational, so canonicalise's exactness gate rejects
            // the coefficient and the body brute-forces: 0.5 * (1 + 2 + 3) = 3.0, a double.
            session_vars().clear();
            session_vars().set("A", Value{0.5});
            EXPECT_EQ(ctx, eval_text(c, "\\sum_{n=1}^{3} An"), Value{3.0});
            session_vars().clear();
        });

    // Cap-exempt: 54M is far past kMaxIterations; the closed form is instant. The result
    // overflows int64, so it comes back a double (asserted by alternative, not value).
    test_detail::with_case(ctx, "closed form :: is cap-exempt", [&] {
        const Value v = eval_text(c, "\\sum_{n=1}^{54000000} (n^{2} - 3n)");
        EXPECT_EQ(ctx, std::holds_alternative<double>(v), true);
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
        {.id = "var-free product", .input = "\\prod_{n=1}^{5} 3", .expected = Value{Rational(243)}},
        {.id = "var-free fractional product",
         .input = "\\prod_{n=1}^{10} (1/2)",
         .expected = Value{Rational(1, 1024)}},
        {.id = "var-free negative product",
         .input = "\\prod_{n=1}^{5} (-2)",
         .expected = Value{Rational(-32)}},
    };

    for (const auto &tc : iterated_closed_cases) {
        test_detail::with_case(ctx, std::string("closed form :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, eval_text(c, tc.input), tc.expected);
        });
    }

    // Bodies that FALL to brute force (not a polynomial for a sum, degree >= 1 for a product).
    // Brute still computes the correct value; the closed-form matcher just declines.
    const std::vector<EvalCase> iterated_brute_cases = {
        {.id = "sum: division by the variable",
         .input = "\\sum_{n=1}^{4} 1/n",
         .expected = Value{Rational(25, 12)}},
        {.id = "sum: a variable exponent (geometric)",
         .input = "\\sum_{n=1}^{5} 2^{n}",
         .expected = Value{Rational(62)}},
        {.id = "sum: a postfix factorial",
         .input = "\\sum_{n=1}^{4} n!",
         .expected = Value{33.0}}, // factorial has no Rational arm, so this is a double
        {.id = "sum: a nested sum",
         .input = "\\sum_{q=1}^{2} \\sum_{m=1}^{2} qm",
         .expected = Value{Rational(9)}},
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
    };

    for (const auto &tc : iterated_brute_cases) {
        test_detail::with_case(ctx, std::string("iterated brute :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, eval_text(c, tc.input), tc.expected);
        });
    }

    test_detail::with_case(
        ctx, "closed form :: a var-free product over a huge range is still capped", [&] {
            // c^count blows up exponentially, unlike Faulhaber's Sum, and one big-int squaring
            // is a single allocation the deadline cannot interrupt, so the product closed form
            // keeps its own size bound and throws directly over it.
            EXPECT_THROWS(ctx, eval_text(c, "\\prod_{n=1}^{2000000} 3"));
            try {
                eval_text(c, "\\prod_{n=1}^{2000000} 3");
            } catch (const CalculatorError &e) {
                EXPECT_EQ(
                    ctx,
                    std::string(e.what()),
                    std::string("Product range is too large to compute."));
            }
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
        "closed form :: a var-free product at the true INT64_MIN lower bound does not "
        "silently return 1",
        [&] {
            // -9223372036854775807-1 evaluates to exactly INT64_MIN, the true extreme (the
            // test above is off by one, since -9223372036854775807 alone still fits as a
            // positive literal negated). At this span, count = last - first + 1 wraps to 0 in
            // uint64, so a naive count-based cap check would miss it and the exponentiation
            // loop would run 0 iterations, silently returning 1 instead of throwing.
            EXPECT_THROWS(
                ctx, eval_text(c, "\\prod_{n=-9223372036854775807-1}^{9223372036854775807} 3"));
            try {
                eval_text(c, "\\prod_{n=-9223372036854775807-1}^{9223372036854775807} 3");
            } catch (const CalculatorError &e) {
                EXPECT_EQ(
                    ctx,
                    std::string(e.what()),
                    std::string("Product range is too large to compute."));
            }
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
            // canonicalise walks the body before any size check, so a var-free zero divisor
            // surfaces the real div-by-zero error rather than being masked by a range limit.
            EXPECT_THROWS(ctx, eval_text(c, "\\sum_{n=1}^{2000000} n/0"));
            try {
                eval_text(c, "\\sum_{n=1}^{2000000} n/0");
            } catch (const CalculatorError &e) {
                EXPECT_EQ(ctx, std::string(e.what()), std::string("Math error"));
            }
        });
}
