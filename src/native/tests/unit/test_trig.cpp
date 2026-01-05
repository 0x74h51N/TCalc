#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <cmath>
#include <complex>

void unit_trig(TestContext &ctx) {
    Calculator c;
    using U = Calculator::AngleUnit;
    using Z = Calculator::Complex;

    TEST_CASE(
        ctx, "real :: sin degrees", { EXPECT_TRUE(ctx, approx(c.sin(90.0, U::DEG), 1.0, 1e-9)); });
    TEST_CASE(ctx, "real :: cos degrees", {
        EXPECT_TRUE(ctx, approx(c.cos(180.0, U::DEG), -1.0, 1e-9));
    });
    TEST_CASE(
        ctx, "real :: tan degrees", { EXPECT_TRUE(ctx, approx(c.tan(45.0, U::DEG), 1.0, 1e-9)); });

    TEST_CASE(ctx, "real :: asin degrees", {
        EXPECT_TRUE(ctx, approx(c.asin(1.0, U::DEG), 90.0, 1e-9));
    });
    TEST_CASE(ctx, "real :: atan degrees", {
        EXPECT_TRUE(ctx, approx(c.atan(1.0, U::DEG), 45.0, 1e-9));
    });

    TEST_CASE(ctx, "real :: sinh zero", { EXPECT_EQ(ctx, c.sinh(0.0), 0.0); });

    // Complex trig
    const Z i(0.0, 1.0);
    TEST_CASE(ctx, "complex :: sin zero real", {
        EXPECT_TRUE(ctx, approx(c.sin(Z(0.0, 0.0), U::RAD).real(), 0.0));
    });
    TEST_CASE(ctx, "complex :: sin zero imag", {
        EXPECT_TRUE(ctx, approx(c.sin(Z(0.0, 0.0), U::RAD).imag(), 0.0));
    });
    TEST_CASE(ctx, "complex :: cos zero real", {
        EXPECT_TRUE(ctx, approx(c.cos(Z(0.0, 0.0), U::RAD).real(), 1.0));
    });
    TEST_CASE(ctx, "complex :: cos zero imag", {
        EXPECT_TRUE(ctx, approx(c.cos(Z(0.0, 0.0), U::RAD).imag(), 0.0));
    });
    const Z tan_i = c.tan(i, U::RAD);
    TEST_CASE(
        ctx, "complex :: tan i real", { EXPECT_TRUE(ctx, approx(tan_i.real(), 0.0, 1e-12)); });
    TEST_CASE(ctx, "complex :: tan i imag", {
        EXPECT_TRUE(ctx, approx(tan_i.imag(), std::tanh(1.0), 1e-12));
    });

    const Z p = c.polar(90.0, U::DEG);
    TEST_CASE(ctx, "polar :: unit circle", { EXPECT_TRUE(ctx, approx(std::abs(p), 1.0, 1e-12)); });

    const BigReal grad_angle("200");
    TEST_CASE(ctx, "bigreal :: cos grad", {
        EXPECT_TRUE(ctx, approx_big(c.cos(grad_angle, U::GRAD), BigReal("-1"), BigReal("1e-30")));
    });

    const BigComplex bc_z("0", "1");
    const BigComplex bc_tan = c.tan(bc_z, U::RAD);
    TEST_CASE(ctx, "bigcomplex :: tan identity", {
        EXPECT_TRUE(ctx, approx_big(bc_tan, c.sin(bc_z, U::RAD) / c.cos(bc_z, U::RAD)));
    });
    (void)i;
}
