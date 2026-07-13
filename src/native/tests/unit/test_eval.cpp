#include "eval/pub/eval.hpp"
#include "internal/test_helpers.hpp"
#include "value.hpp"

using tcalc::Arm;
using tcalc::arm_of;
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
using tcalc::eval::promote_complex;
using tcalc::ops::OpId;

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

    TEST_CASE(ctx, "coerce :: an op with no Rational arm downcasts (fact of a rational)", {
        const auto out = coerce(OpId::Fact, {Value{Rational(5)}});
        EXPECT_EQ(ctx, arm_of(out[0]), Arm::Int64); // 5/1 -> int64 -> double arm at dispatch
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

    // Do not break the case Task 4 already pinned: a single argument is trivially
    // homogeneous, so a lone rational-downcast-to-int64 must not be forced to double.
    TEST_CASE(ctx, "coerce :: fact of a rational still lands on Int64, not forced to double", {
        const auto out = coerce(OpId::Fact, {Value{Rational(5)}});
        EXPECT_EQ(ctx, arm_of(out[0]), Arm::Int64);
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
}
