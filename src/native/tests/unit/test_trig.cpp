#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <cmath>
#include <complex>
#include <cstdint>
#include <functional>
#include <limits>
#include <optional>
#include <string>
#include <variant>
#include <vector>

namespace {

/// Generic test-row template: id label, input value, expected value. Mirrors
/// test_eval.cpp's local Case so each shape below drives one table instead of
/// a wall of TEST_CASE blocks.
template <typename InputT, typename ExpectedT> struct Case {
    const char *id;
    InputT input;
    ExpectedT expected;
};

using U = Calculator::AngleUnit;
using F = Calculator::TrigFn;
using Z = Calculator::Complex;

/// A real trig call: which method, the argument, and the unit.
struct UnitArg {
    double (Calculator::*fn)(double, U) const;
    double a;
    U unit;
};
/// Same shape as UnitArg, plus the tolerance to compare within (0.0 means exactly).
struct UnitArgTol {
    double (Calculator::*fn)(double, U) const;
    double a;
    U unit;
    double tol;
};
/// Case row for a real trig call compared within its own row's tolerance.
using RealTolCase = Case<UnitArgTol, double>;
/// Case row for a real trig call that must throw (a tan pole).
using RealThrowCase = Case<UnitArg, std::monostate>;

/// A one-argument call with no shared signature (sinh takes no unit, unlike asin/atan), so
/// the row carries its own invocation and an optional tolerance (nullopt means exact).
struct OneLinerArg {
    std::function<double(const Calculator &)> call;
    std::optional<double> eps;
};
/// Case row for the hyperbolic/inverse one-liners.
using OneLinerCase = Case<OneLinerArg, double>;

/// A complex trig call and which component of the result to read.
struct ComplexArg {
    Z (Calculator::*fn)(Z, U) const;
    Z a;
    bool real_part;
};
/// Case row for complex trig, compared within a shared per-table tolerance.
using ComplexCase = Case<ComplexArg, double>;

/// half_turns's own argument shape: a turns value and the unit it is read in.
struct TurnArg {
    Rational t;
    U unit;
};
/// Case row for half_turns: an exact Rational result, or nullopt when the guard declines.
using HalfTurnCase = Case<TurnArg, std::optional<Rational>>;

/// exact_half_turns/real_half_turns's argument shape: which function, t in half turns, and
/// (for real_half_turns rows only) the row's own tolerance; unused rows leave it zero.
struct FnTurnArg {
    F fn;
    Rational t;
    double eps = 0.0;
};
/// Case row for exact_half_turns: a Rational result, or nullopt when the value is irrational.
using ExactTurnCase = Case<FnTurnArg, std::optional<Rational>>;
/// Case row for exact_half_turns at a tan pole, which raises instead of returning.
using ExactTurnThrowCase = Case<FnTurnArg, std::monostate>;
/// Case row for real_half_turns compared within its own row's tolerance.
using RealTurnCase = Case<FnTurnArg, double>;

} // namespace

void unit_trig(TestContext &ctx) {
    Calculator c;

    // A real trig call compared against a reference: well-known-angle sanity checks and
    // turn-boundary drift checks are the same measurement, so they share one table. Each row
    // states its own tolerance; 0.0 means the comparison is exact (approx(a, b, 0.0) is
    // abs(a - b) <= 0.0, i.e. bit-exact, not a small epsilon).
    constexpr double kDegTol = 1e-9;
    constexpr double kDriftTol = 1e-15;
    const std::vector<RealTolCase> trig_tol_cases = {
        {.id = "sin degrees", .input = {&Calculator::sin, 90.0, U::DEG, kDegTol}, .expected = 1.0},
        {.id = "cos degrees",
         .input = {&Calculator::cos, 180.0, U::DEG, kDegTol},
         .expected = -1.0},
        {.id = "tan degrees", .input = {&Calculator::tan, 45.0, U::DEG, kDegTol}, .expected = 1.0},
        // to_radians scales by an inexact pi/180, so the absolute error grows with the argument:
        // sin(1e15 + 45) in degrees was wrong by 8.9e-4. Reducing modulo a full turn first is
        // exact, since 360 is an exact double and fmod is exact for finite operands. References
        // computed at 60 digits; the drift rows' tolerance below is a few ULP, not a fudge factor.
        {.id = "sin at an exact multiple of a turn (deg)",
         .input = {&Calculator::sin, 360000.0, U::DEG, 0.0},
         .expected = 0.0},
        {.id = "cos at an exact multiple of a turn (grad)",
         .input = {&Calculator::cos, 360000.0, U::GRAD, 0.0},
         .expected = 1.0},
        {.id = "sin near a turn boundary",
         .input = {&Calculator::sin, 360020.0, U::DEG, kDriftTol},
         .expected = 0.34202014332566871},
        {.id = "sin of a large degree argument",
         .input = {&Calculator::sin, 123456789.0, U::DEG, kDriftTol},
         .expected = -0.15643446504023087},
        {.id = "sin of an argument past 1e15",
         .input = {&Calculator::sin, 1e15 + 45.0, U::DEG, kDriftTol},
         .expected = -0.57357643635104605},
    };
    for (const auto &tc : trig_tol_cases) {
        test_detail::with_case(ctx, std::string("real :: ") + tc.id, [&] {
            EXPECT_TRUE(
                ctx,
                approx((c.*tc.input.fn)(tc.input.a, tc.input.unit), tc.expected, tc.input.tol));
        });
    }

    // tan is undefined at every odd quarter turn. In degrees and grads that point is an exact
    // double (90, 100), so returning 1.633e16 for it is a wrong answer rather than an imprecise
    // one. In radians pi/2 is not representable, so no double argument lands on the pole and
    // there is nothing to detect here; the radian case is Task 4.
    // (tan(45, DEG) itself is already covered by the "tan degrees" row above.)
    const std::vector<RealThrowCase> tan_pole_cases = {
        {.id = "tan raises at a degree pole",
         .input = {&Calculator::tan, 90.0, U::DEG},
         .expected = {}},
        {.id = "tan raises at 270 degrees",
         .input = {&Calculator::tan, 270.0, U::DEG},
         .expected = {}},
        {.id = "tan raises at -90 degrees",
         .input = {&Calculator::tan, -90.0, U::DEG},
         .expected = {}},
        {.id = "tan raises past many full turns",
         .input = {&Calculator::tan, 360090.0, U::DEG},
         .expected = {}},
        {.id = "tan raises at a grad pole",
         .input = {&Calculator::tan, 100.0, U::GRAD},
         .expected = {}},
    };
    for (const auto &tc : tan_pole_cases) {
        test_detail::with_case(ctx, std::string("real :: ") + tc.id, [&] {
            EXPECT_THROWS(ctx, (c.*tc.input.fn)(tc.input.a, tc.input.unit));
        });
    }

    // Hyperbolic and inverse one-liners: no shared call signature (sinh takes no unit), so
    // each row supplies its own invocation.
    const std::vector<OneLinerCase> one_liner_cases = {
        {.id = "sinh zero",
         .input = {[](const Calculator &cc) { return cc.sinh(0.0); }, std::nullopt},
         .expected = 0.0},
        {.id = "asin degrees",
         .input = {[](const Calculator &cc) { return cc.asin(1.0, U::DEG); }, kDegTol},
         .expected = 90.0},
        {.id = "atan degrees",
         .input = {[](const Calculator &cc) { return cc.atan(1.0, U::DEG); }, kDegTol},
         .expected = 45.0},
    };
    for (const auto &tc : one_liner_cases) {
        test_detail::with_case(ctx, std::string("real :: ") + tc.id, [&] {
            const double got = tc.input.call(c);
            if (tc.input.eps) {
                EXPECT_TRUE(ctx, approx(got, tc.expected, *tc.input.eps));
            } else {
                EXPECT_EQ(ctx, got, tc.expected);
            }
        });
    }

    // Complex trig: the same tolerance whether approx()'s default was relied on or passed
    // explicitly, since kDefaultApproxEps already is 1e-12.
    constexpr double kComplexTol = 1e-12;
    const Z i(0.0, 1.0);
    const std::vector<ComplexCase> complex_cases = {
        {.id = "sin zero real", .input = {&Calculator::sin, Z(0.0, 0.0), true}, .expected = 0.0},
        {.id = "sin zero imag", .input = {&Calculator::sin, Z(0.0, 0.0), false}, .expected = 0.0},
        {.id = "cos zero real", .input = {&Calculator::cos, Z(0.0, 0.0), true}, .expected = 1.0},
        {.id = "cos zero imag", .input = {&Calculator::cos, Z(0.0, 0.0), false}, .expected = 0.0},
        {.id = "tan i real", .input = {&Calculator::tan, i, true}, .expected = 0.0},
        {.id = "tan i imag", .input = {&Calculator::tan, i, false}, .expected = std::tanh(1.0)},
    };
    for (const auto &tc : complex_cases) {
        test_detail::with_case(ctx, std::string("complex :: ") + tc.id, [&] {
            const Z got = (c.*tc.input.fn)(tc.input.a, U::RAD);
            const double part = tc.input.real_part ? got.real() : got.imag();
            EXPECT_TRUE(ctx, approx(part, tc.expected, kComplexTol));
        });
    }

    // Single-instance calls: each is its own kernel with no sibling of the same shape, so a
    // table would only add indirection.
    test_detail::with_case(ctx, "polar :: unit circle", [&] {
        const Z p = c.polar(90.0, U::DEG);
        EXPECT_TRUE(ctx, approx(std::abs(p), 1.0, 1e-12));
    });
    test_detail::with_case(ctx, "bigreal :: cos grad", [&] {
        EXPECT_TRUE(
            ctx, approx_big(c.cos(BigReal("200"), U::GRAD), BigReal("-1"), BigReal("1e-30")));
    });
    test_detail::with_case(ctx, "bigcomplex :: tan identity", [&] {
        const BigComplex bc_z("0", "1");
        EXPECT_TRUE(
            ctx, approx_big(c.tan(bc_z, U::RAD), c.sin(bc_z, U::RAD) / c.cos(bc_z, U::RAD)));
    });

    // half_turns: the argument in half turns, so the angle is pi*t. A rational number of
    // radians is a/pi half turns, irrational unless a is zero, so radians have exactly one
    // exact case (the "zero radians" row below).
    constexpr std::int64_t kMin = (std::numeric_limits<std::int64_t>::min)();
    const std::vector<HalfTurnCase> half_turn_cases = {
        {.id = "30 degrees", .input = {Rational(30), U::DEG}, .expected = Rational(1, 6)},
        {.id = "180 degrees", .input = {Rational(180), U::DEG}, .expected = Rational(1)},
        {.id = "50 grad", .input = {Rational(50), U::GRAD}, .expected = Rational(1, 4)},
        {.id = "zero radians", .input = {Rational(0), U::RAD}, .expected = Rational(0)},
        {.id = "one radian has no exact case",
         .input = {Rational(1), U::RAD},
         .expected = std::nullopt},
        // A denominator this large, coprime to 180, would overflow int64 in the reduction; the
        // guard must decline instead of dividing into undefined behaviour.
        {.id = "a denominator too large to reduce declines",
         .input = {Rational(7, 51240955760304311), U::DEG},
         .expected = std::nullopt},
        // A large numerator alone is fine: the guard must not be over-broad.
        {.id = "a large numerator alone is fine",
         .input = {Rational(360000), U::DEG},
         .expected = Rational(2000)},
        // rational_div_overflows used to hand an INT64_MIN numerator straight to std::gcd,
        // which is UB there (libstdc++ asserts and aborts the process); it must decline
        // instead, since there is no exact quotient to report for a numerator this size anyway.
        {.id = "an INT64_MIN numerator declines in degrees",
         .input = {Rational(kMin), U::DEG},
         .expected = std::nullopt},
        {.id = "an INT64_MIN numerator declines in grad",
         .input = {Rational(kMin), U::GRAD},
         .expected = std::nullopt},
    };
    for (const auto &tc : half_turn_cases) {
        test_detail::with_case(ctx, std::string("half_turns :: ") + tc.id, [&] {
            const auto got = c.half_turns(tc.input.t, tc.input.unit);
            EXPECT_EQ(ctx, got.has_value(), tc.expected.has_value());
            if (tc.expected.has_value()) {
                EXPECT_EQ(ctx, *got, *tc.expected);
            }
        });
    }

    // Niven's theorem: at a rational multiple of pi, sine and cosine are rational only at
    // 0, +-1/2, +-1. The value rows below are that theorem, and are all of its points.
    const std::vector<ExactTurnCase> exact_turn_cases = {
        {.id = "sin at 1/6", .input = {F::Sin, Rational(1, 6)}, .expected = Rational(1, 2)},
        {.id = "sin at 5/6", .input = {F::Sin, Rational(5, 6)}, .expected = Rational(1, 2)},
        {.id = "sin at 7/6", .input = {F::Sin, Rational(7, 6)}, .expected = Rational(-1, 2)},
        {.id = "sin at 11/6", .input = {F::Sin, Rational(11, 6)}, .expected = Rational(-1, 2)},
        {.id = "sin at 1/2", .input = {F::Sin, Rational(1, 2)}, .expected = Rational(1)},
        {.id = "sin at 3/2", .input = {F::Sin, Rational(3, 2)}, .expected = Rational(-1)},
        {.id = "sin at 1", .input = {F::Sin, Rational(1)}, .expected = Rational(0)},
        {.id = "sin at 2000", .input = {F::Sin, Rational(2000)}, .expected = Rational(0)},
        {.id = "cos at 1", .input = {F::Cos, Rational(1)}, .expected = Rational(-1)},
        {.id = "cos at 0", .input = {F::Cos, Rational(0)}, .expected = Rational(1)},
        {.id = "cos at 1/2", .input = {F::Cos, Rational(1, 2)}, .expected = Rational(0)},
        {.id = "cos at 1/3", .input = {F::Cos, Rational(1, 3)}, .expected = Rational(1, 2)},
        {.id = "cos at 2/3", .input = {F::Cos, Rational(2, 3)}, .expected = Rational(-1, 2)},
        {.id = "tan at 1/4", .input = {F::Tan, Rational(1, 4)}, .expected = Rational(1)},
        {.id = "tan at 3/4", .input = {F::Tan, Rational(3, 4)}, .expected = Rational(-1)},
        {.id = "tan at 1", .input = {F::Tan, Rational(1)}, .expected = Rational(0)},
        // Irrational values are absent by design: sine at q=4 is sqrt(2)/2, cosine at q=6 is
        // sqrt(3)/2. A miss is nullopt, not a raise, so the caller can simply fall through.
        {.id = "sin at 1/4 is irrational",
         .input = {F::Sin, Rational(1, 4)},
         .expected = std::nullopt},
        {.id = "cos at 1/6 is irrational",
         .input = {F::Cos, Rational(1, 6)},
         .expected = std::nullopt},
        {.id = "sin at 1/9 is irrational",
         .input = {F::Sin, Rational(1, 9)},
         .expected = std::nullopt},
    };
    for (const auto &tc : exact_turn_cases) {
        test_detail::with_case(ctx, std::string("exact_half_turns :: ") + tc.id, [&] {
            const auto got = c.exact_half_turns(tc.input.fn, tc.input.t);
            EXPECT_EQ(ctx, got.has_value(), tc.expected.has_value());
            if (tc.expected.has_value()) {
                EXPECT_EQ(ctx, *got, *tc.expected);
            }
        });
    }

    // A tan pole is the one case that raises: it has no value at all.
    const std::vector<ExactTurnThrowCase> exact_turn_throw_cases = {
        {.id = "tan at 1/2", .input = {F::Tan, Rational(1, 2)}, .expected = {}},
        {.id = "tan at 3/2", .input = {F::Tan, Rational(3, 2)}, .expected = {}},
    };
    for (const auto &tc : exact_turn_throw_cases) {
        test_detail::with_case(ctx, std::string("exact_half_turns :: ") + tc.id, [&] {
            EXPECT_THROWS(ctx, c.exact_half_turns(tc.input.fn, tc.input.t));
        });
    }

    // A large multiple of pi has no Niven value, but it is the product pi*t that drifts, not the
    // sine. Folding t into the first quadrant first is exact rational arithmetic, so only a
    // small product is ever formed. References computed at 60 digits.
    //
    // The headroom rows below push the same fold past calc_detail::half_turn_fold_overflows's
    // bound (a quarter of int64's range): the int64 fold would form 2*p near 2*INT64_MAX here and
    // wrap. This is the scale the int256_t fallback exists for; without it these cases would fail
    // silently if the fold were ever "simplified" back to plain int64. References computed with
    // mpmath at 60 digits (sin/cos of pi/INT64_MAX and pi*(INT64_MAX-1)/INT64_MAX), not derived
    // from this implementation. The cos rows land on an exact double, hence eps 0.
    constexpr double kFoldTol = 1e-15;
    constexpr std::int64_t kMax = (std::numeric_limits<std::int64_t>::max)();
    // t = 1/INT64_MAX: numerator small, denominator at the very top of int64's range.
    const Rational tiny(1, kMax);
    // t = (INT64_MAX - 1)/INT64_MAX: numerator and denominator both near INT64_MAX, and still
    // coprime since they are consecutive integers, so the denominator survives Rational's own
    // reduction. This is pi minus the same tiny angle, so sin agrees with tiny's and cos flips
    // sign.
    const Rational near_pi(kMax - 1, kMax);
    const std::vector<RealTurnCase> real_turn_cases = {
        {.id = "sin at 1/5",
         .input = {F::Sin, Rational(1, 5), kFoldTol},
         .expected = 0.58778525229247313},
        {.id = "sin at 2001/5 folds the same as 1/5",
         .input = {F::Sin, Rational(2001, 5), kFoldTol},
         .expected = 0.58778525229247313},
        {.id = "cos at 1/5",
         .input = {F::Cos, Rational(1, 5), kFoldTol},
         .expected = 0.80901699437494742},
        {.id = "sin at 4/5",
         .input = {F::Sin, Rational(4, 5), kFoldTol},
         .expected = 0.58778525229247313},
        {.id = "sin at 6/5",
         .input = {F::Sin, Rational(6, 5), kFoldTol},
         .expected = -0.58778525229247313},
        {.id = "tan at 1/5",
         .input = {F::Tan, Rational(1, 5), kFoldTol},
         .expected = 0.72654252800536088},
        {.id = "sin at the tiny end of headroom",
         .input = {F::Sin, tiny, 1e-33},
         .expected = 3.4061215800865545e-19},
        {.id = "cos at the tiny end of headroom", .input = {F::Cos, tiny, 0.0}, .expected = 1.0},
        {.id = "sin near pi at the far end of headroom",
         .input = {F::Sin, near_pi, 1e-33},
         .expected = 3.4061215800865545e-19},
        {.id = "cos near pi at the far end of headroom",
         .input = {F::Cos, near_pi, 0.0},
         .expected = -1.0},
    };
    for (const auto &tc : real_turn_cases) {
        test_detail::with_case(ctx, std::string("real_half_turns :: ") + tc.id, [&] {
            EXPECT_TRUE(
                ctx, approx(c.real_half_turns(tc.input.fn, tc.input.t), tc.expected, tc.input.eps));
        });
    }
}
