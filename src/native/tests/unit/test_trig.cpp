#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <cmath>
#include <complex>

void unit_trig(TestContext &ctx) {
    Calculator c;
    using U = Calculator::AngleUnit;
    using Z = Calculator::Complex;

    EXPECT_TRUE(ctx, approx(c.sin(90.0, U::DEG), 1.0, 1e-9));
    EXPECT_TRUE(ctx, approx(c.cos(180.0, U::DEG), -1.0, 1e-9));
    EXPECT_TRUE(ctx, approx(c.tan(45.0, U::DEG), 1.0, 1e-9));

    EXPECT_TRUE(ctx, approx(c.asin(1.0, U::DEG), 90.0, 1e-9));
    EXPECT_TRUE(ctx, approx(c.atan(1.0, U::DEG), 45.0, 1e-9));

    EXPECT_EQ(ctx, c.sinh(0.0), 0.0);

    // Complex trig
    const Z i(0.0, 1.0);
    EXPECT_TRUE(ctx, approx(c.sin(Z(0.0, 0.0), U::RAD).real(), 0.0));
    EXPECT_TRUE(ctx, approx(c.sin(Z(0.0, 0.0), U::RAD).imag(), 0.0));
    EXPECT_TRUE(ctx, approx(c.cos(Z(0.0, 0.0), U::RAD).real(), 1.0));
    EXPECT_TRUE(ctx, approx(c.cos(Z(0.0, 0.0), U::RAD).imag(), 0.0));
    const Z tan_i = c.tan(i, U::RAD);
    EXPECT_TRUE(ctx, approx(tan_i.real(), 0.0, 1e-12));
    EXPECT_TRUE(ctx, approx(tan_i.imag(), std::tanh(1.0), 1e-12));

    const Z p = c.polar(90.0, U::DEG);
    EXPECT_TRUE(ctx, approx(std::abs(p), 1.0, 1e-12));

    const BigReal grad_angle("200");
    EXPECT_TRUE(ctx, approx_big(c.cos(grad_angle, U::GRAD), BigReal("-1"), BigReal("1e-30")));

    const BigComplex bc_z("0", "1");
    const BigComplex bc_tan = c.tan(bc_z, U::RAD);
    EXPECT_TRUE(ctx, approx_big(bc_tan, c.sin(bc_z, U::RAD) / c.cos(bc_z, U::RAD)));
    (void)i;
}
