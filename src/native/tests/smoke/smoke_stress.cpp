#include <cmath>
#include <limits>
#include <utility>

#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

template <typename Fn>
static void smoke_allow_math_error(TestContext &ctx, const char *name, Fn &&fn) {
    TEST_CASE(ctx, name, {
        try {
            std::forward<Fn>(fn)();
        } catch (const CalculatorError &) { // allowed
            return;
        } catch (const std::exception &e) {
            EXPECT_MSG(ctx, false, [&](auto &os) { os << "unexpected exception: " << e.what(); });
        } catch (...) {
            EXPECT_TRUE(ctx, false, "unexpected unknown exception");
        }
    });
}

void smoke_stress(TestContext &ctx) {
    Calculator c;
    using BC = BigComplex;
    using BF = boost::multiprecision::cpp_bin_float_50;

    const double inf = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();

    smoke_allow_math_error(ctx, "double :: add inf one", [&] { (void)c.add(inf, 1.0); });
    smoke_allow_math_error(ctx, "double :: mul inf zero", [&] { (void)c.mul(inf, 0.0); });
    smoke_allow_math_error(ctx, "double :: div one inf", [&] { (void)c.div(1.0, inf); });
    smoke_allow_math_error(ctx, "double :: div one zero", [&] { (void)c.div(1.0, 0.0); });

    smoke_allow_math_error(ctx, "double :: pow large exp", [&] { (void)c.pow(10.0, 308.0); });
    smoke_allow_math_error(
        ctx, "double :: pow large base int exp", [&] { (void)c.pow(1e154, 2LL); });

    smoke_allow_math_error(ctx, "double :: sqrt inf", [&] { (void)c.sqrt(inf); });
    smoke_allow_math_error(ctx, "double :: sqrt nan", [&] { (void)c.sqrt(nan); });
    smoke_allow_math_error(ctx, "double :: log inf", [&] { (void)c.log(inf); });
    smoke_allow_math_error(ctx, "double :: log nan", [&] { (void)c.log(nan); });

    smoke_allow_math_error(
        ctx, "double :: sin inf", [&] { (void)c.sin(inf, Calculator::AngleUnit::RAD); });
    smoke_allow_math_error(
        ctx, "double :: cos nan", [&] { (void)c.cos(nan, Calculator::AngleUnit::RAD); });

    smoke_allow_math_error(ctx, "double :: fact large", [&] { (void)c.fact(171.0); });
    smoke_allow_math_error(ctx, "double :: fact huge", [&] { (void)c.fact(1e17); });
    smoke_allow_math_error(ctx, "double :: fact inf", [&] { (void)c.fact(inf); });
    smoke_allow_math_error(ctx, "double :: gamma huge", [&] { (void)c.gamma(1e17); });

    smoke_allow_math_error(ctx, "double :: choose large", [&] { (void)c.choose(500, 250); });

    const BigReal hug = BigReal("1e1000");
    smoke_allow_math_error(ctx, "bigreal :: sqrt huge", [&] { (void)c.sqrt(hug); });
    smoke_allow_math_error(ctx, "bigreal :: log huge", [&] { (void)c.log(hug); });
    smoke_allow_math_error(ctx, "bigreal :: pow huge", [&] { (void)c.pow(hug, BigReal("2.0")); });

    const BigReal hug2 = BigReal("1e20000");
    smoke_allow_math_error(ctx, "bigreal :: sqrt enormous", [&] { (void)c.sqrt(hug2); });
    smoke_allow_math_error(
        ctx, "bigreal :: root enormous", [&] { (void)c.root(hug2, BigReal("7")); });
    smoke_allow_math_error(
        ctx, "bigreal :: pow enormous", [&] { (void)c.pow(hug2, BigReal("3")); });

    const BC z("1e400", "1");
    const BC z_pow = c.pow(z, BC("20000"));
    TEST_CASE(ctx, "bigcomplex :: pow enormous", {
        EXPECT_TRUE(ctx, boost::multiprecision::abs(z_pow) > BF(0));
    });

    const BC z_log = c.log(z);
    TEST_CASE(ctx, "bigcomplex :: log enormous", {
        EXPECT_TRUE(ctx, boost::multiprecision::abs(z_log) > BF(0));
    });

    const BC z_root = c.root(BC("1e400", "1e-50"), BC("3"));
    TEST_CASE(ctx, "bigcomplex :: root enormous", {
        EXPECT_TRUE(ctx, boost::multiprecision::abs(z_root) > BF(0));
    });

    const BC z_pow2 = c.pow(BC("1e200", "1e200"), BC("5000"));
    TEST_CASE(ctx, "bigcomplex :: pow huge", {
        EXPECT_TRUE(ctx, boost::multiprecision::abs(z_pow2) > BF(0));
    });
}
