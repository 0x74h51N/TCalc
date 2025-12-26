#include <cmath>
#include <iostream>
#include <limits>
#include <utility>

#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

template <typename Fn>
static void smoke_allow_math_error(TestContext &ctx, const char *name, Fn &&fn) {
    ctx.checks += 1;
    try {
        std::forward<Fn>(fn)();
        return;
    } catch (const CalculatorError &) { // allowed
        return;
    } catch (const std::exception &e) {
        ctx.failures += 1;
        std::cerr << "smoke: unexpected exception in " << name << ": " << e.what() << "\n";
    } catch (...) {
        ctx.failures += 1;
        std::cerr << "smoke: unknown exception in " << name << "\n";
    }
}

void smoke_stress(TestContext &ctx) {
    Calculator c;
    using BC = BigComplex;
    using BF = boost::multiprecision::cpp_bin_float_50;

    const double inf = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();

    smoke_allow_math_error(ctx, "add(inf, 1)", [&] { (void)c.add(inf, 1.0); });
    smoke_allow_math_error(ctx, "mul(inf, 0)", [&] { (void)c.mul(inf, 0.0); });
    smoke_allow_math_error(ctx, "div(1, inf)", [&] { (void)c.div(1.0, inf); });
    smoke_allow_math_error(ctx, "div(1, 0)", [&] { (void)c.div(1.0, 0.0); });

    smoke_allow_math_error(ctx, "pow(10, 308)", [&] { (void)c.pow(10.0, 308.0); });
    smoke_allow_math_error(ctx, "pow(1e154, 2)", [&] { (void)c.pow(1e154, 2LL); });

    smoke_allow_math_error(ctx, "sqrt(inf)", [&] { (void)c.sqrt(inf); });
    smoke_allow_math_error(ctx, "sqrt(nan)", [&] { (void)c.sqrt(nan); });
    smoke_allow_math_error(ctx, "log(inf)", [&] { (void)c.log(inf); });
    smoke_allow_math_error(ctx, "log(nan)", [&] { (void)c.log(nan); });

    smoke_allow_math_error(ctx, "sin(inf)", [&] { (void)c.sin(inf, Calculator::AngleUnit::RAD); });
    smoke_allow_math_error(ctx, "cos(nan)", [&] { (void)c.cos(nan, Calculator::AngleUnit::RAD); });

    smoke_allow_math_error(ctx, "fact(171)", [&] { (void)c.fact(171.0); });
    smoke_allow_math_error(ctx, "fact(1e17)", [&] { (void)c.fact(1e17); });
    smoke_allow_math_error(ctx, "fact(inf)", [&] { (void)c.fact(inf); });
    smoke_allow_math_error(ctx, "gamma(1e17)", [&] { (void)c.gamma(1e17); });

    smoke_allow_math_error(ctx, "choose(500, 250)", [&] { (void)c.choose(500, 250); });

    const BigReal hug = BigReal("1e1000");
    smoke_allow_math_error(ctx, "sqrt(hug)", [&] { (void)c.sqrt(hug); });
    smoke_allow_math_error(ctx, "log(hug)", [&] { (void)c.log(hug); });
    smoke_allow_math_error(ctx, "pow(hug, 2)", [&] { (void)c.pow(hug, BigReal("2.0")); });

    const BigReal hug2 = BigReal("1e20000");
    smoke_allow_math_error(ctx, "sqrt(hug2)", [&] { (void)c.sqrt(hug2); });
    smoke_allow_math_error(ctx, "root(hug2, 7)", [&] { (void)c.root(hug2, BigReal("7")); });
    smoke_allow_math_error(ctx, "pow(hug2, 3)", [&] { (void)c.pow(hug2, BigReal("3")); });

    const BC z("1e400", "1");
    const BC z_pow = c.pow(z, BC("20000"));
    EXPECT_TRUE(ctx, boost::multiprecision::abs(z_pow) > BF(0));

    const BC z_log = c.log(z);
    EXPECT_TRUE(ctx, boost::multiprecision::abs(z_log) > BF(0));

    const BC z_root = c.root(BC("1e400", "1e-50"), BC("3"));
    EXPECT_TRUE(ctx, boost::multiprecision::abs(z_root) > BF(0));

    const BC z_pow2 = c.pow(BC("1e200", "1e200"), BC("5000"));
    EXPECT_TRUE(ctx, boost::multiprecision::abs(z_pow2) > BF(0));
}
