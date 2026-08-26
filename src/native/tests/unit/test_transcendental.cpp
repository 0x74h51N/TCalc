#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

#include <boost/math/constants/constants.hpp>
#include <cmath>
#include <limits>
#include <string>
#include <vector>

namespace {

/// Rows carry the call they exercise as a member pointer, so every same-shaped call
/// shares one table instead of one loop each. `tol` of 0 asserts exact equality.
using RealFn = double (Calculator::*)(double) const;
using RealBinFn = double (Calculator::*)(double, double) const;
using BigFn = BigReal (Calculator::*)(const BigReal &) const;

/// Overloaded names need the target signature spelled out to take an address.
#define REAL_FN(name) static_cast<RealFn>(&Calculator::name)
#define REAL_BIN_FN(name) static_cast<RealBinFn>(&Calculator::name)
#define BIG_FN(name) static_cast<BigFn>(&Calculator::name)

struct RealCase {
    const char *id;
    RealFn fn;
    double input;
    double expected;
    double tol;
};

struct RealBinCase {
    const char *id;
    RealBinFn fn;
    double x;
    double y;
    double expected;
    double tol;
};

/// BigReal rows carry decimal text so no double sneaks into an input or an expectation.
/// A null tol asserts exact equality.
struct BigCase {
    const char *id;
    BigFn fn;
    const char *input;
    const char *expected;
    const char *tol;
};

} // namespace

void unit_transcendental(TestContext &ctx) {
    Calculator c;
    using Z = Calculator::Complex;
    using BC = BigComplex;
    using BF = boost::multiprecision::cpp_bin_float_50;

    // ----
    // Real
    // ----
    // exp is its own primitive, not pow(e, x). The detour through log(e) shifted the last
    // digit, so its rows are exact where the old spelling was an ulp out.
    const std::vector<RealCase> real_cases = {
        {.id = "exp :: zero", .fn = REAL_FN(exp), .input = 0.0, .expected = 1.0, .tol = 0.0},
        {.id = "exp :: one",
         .fn = REAL_FN(exp),
         .input = 1.0,
         .expected = 2.718281828459045,
         .tol = 0.0},
        {.id = "exp :: ln two",
         .fn = REAL_FN(exp),
         .input = std::log(2.0),
         .expected = 2.0,
         .tol = 0.0},
        {.id = "exp :: minus ln two",
         .fn = REAL_FN(exp),
         .input = -std::log(2.0),
         .expected = 0.5,
         .tol = 0.0},
        {.id = "exp :: two",
         .fn = REAL_FN(exp),
         .input = 2.0,
         .expected = 7.38905609893065,
         .tol = 0.0},
        {.id = "exp :: negative",
         .fn = REAL_FN(exp),
         .input = -3.0,
         .expected = 0.049787068367863944,
         .tol = 0.0},
        {.id = "sqrt :: four", .fn = REAL_FN(sqrt), .input = 4.0, .expected = 2.0, .tol = 0.0},
        {.id = "sqrt :: zero", .fn = REAL_FN(sqrt), .input = 0.0, .expected = 0.0, .tol = 0.0},
        {.id = "cbrt :: twenty seven",
         .fn = REAL_FN(cbrt),
         .input = 27.0,
         .expected = 3.0,
         .tol = 1e-12},
        {.id = "cbrt :: negative eight",
         .fn = REAL_FN(cbrt),
         .input = -8.0,
         .expected = -2.0,
         .tol = 1e-12},
        {.id = "log :: hundred",
         .fn = REAL_FN(log),
         .input = 100.0,
         .expected = 2.0,
         .tol = kDefaultApproxEps},
        {.id = "log :: one",
         .fn = REAL_FN(log),
         .input = 1.0,
         .expected = 0.0,
         .tol = kDefaultApproxEps},
        {.id = "ln :: e",
         .fn = REAL_FN(ln),
         .input = std::exp(1.0),
         .expected = 1.0,
         .tol = kDefaultApproxEps},
        {.id = "ln :: one",
         .fn = REAL_FN(ln),
         .input = 1.0,
         .expected = 0.0,
         .tol = kDefaultApproxEps},
    };

    for (const auto &tc : real_cases) {
        test_detail::with_case(ctx, std::string("real :: ") + tc.id, [&] {
            const double got = (c.*tc.fn)(tc.input);
            if (tc.tol == 0.0)
                EXPECT_EQ(ctx, got, tc.expected);
            else
                EXPECT_TRUE(ctx, approx(got, tc.expected, tc.tol));
        });
    }

    const std::vector<RealBinCase> real_bin_cases = {
        {.id = "root :: cube",
         .fn = REAL_BIN_FN(root),
         .x = 27.0,
         .y = 3.0,
         .expected = 3.0,
         .tol = kDefaultApproxEps},
        {.id = "root :: negative at an odd degree",
         .fn = REAL_BIN_FN(root),
         .x = -8.0,
         .y = 3.0,
         .expected = -2.0,
         .tol = kDefaultApproxEps},
        {.id = "pow :: fractional exponent",
         .fn = REAL_BIN_FN(pow),
         .x = 9.0,
         .y = 0.5,
         .expected = 3.0,
         .tol = kDefaultApproxEps},
    };

    for (const auto &tc : real_bin_cases) {
        test_detail::with_case(ctx, std::string("real :: ") + tc.id, [&] {
            const double got = (c.*tc.fn)(tc.x, tc.y);
            if (tc.tol == 0.0)
                EXPECT_EQ(ctx, got, tc.expected);
            else
                EXPECT_TRUE(ctx, approx(got, tc.expected, tc.tol));
        });
    }

    // pow's integer exponent is a separate overload, so it cannot join the table above.
    TEST_CASE(
        ctx, "real :: pow :: integer exponent", { EXPECT_EQ(ctx, c.pow(2.0, 10LL), 1024.0); });
    TEST_CASE(ctx, "real :: pow :: negative integer exponent", {
        EXPECT_EQ(ctx, c.pow(2.0, -3LL), 0.125);
    });

    // Each of these raises from a different call, so there is no shared row to tabulate.
    TEST_CASE(ctx, "real :: sqrt of a negative throws", { EXPECT_THROWS(ctx, c.sqrt(-1.0)); });
    TEST_CASE(ctx, "real :: log of zero throws", { EXPECT_THROWS(ctx, c.log(0.0)); });
    TEST_CASE(ctx, "real :: ln of zero throws", { EXPECT_THROWS(ctx, c.ln(0.0)); });
    TEST_CASE(ctx, "real :: root of a negative at an even degree throws", {
        EXPECT_THROWS(ctx, c.root(-8.0, 2.0));
    });
    TEST_CASE(
        ctx, "real :: zero to a negative power throws", { EXPECT_THROWS(ctx, c.pow(0.0, -1LL)); });

    // ----
    // BigReal
    // ----
    // The old spelling raised the double-precision e to a BigReal power, so exp carried
    // about sixteen correct digits on this arm. A real exp carries the type's own fifty.
    const std::vector<BigCase> big_cases = {
        {.id = "exp :: one",
         .fn = BIG_FN(exp),
         .input = "1",
         .expected = "2.71828182845904523536028747135266249775724709369996",
         .tol = "1e-40"},
        {.id = "exp :: zero", .fn = BIG_FN(exp), .input = "0", .expected = "1", .tol = "1e-40"},
        {.id = "exp :: negative",
         .fn = BIG_FN(exp),
         .input = "-1",
         .expected = "0.36787944117144232159552377016146086744581113103177",
         .tol = "1e-40"},
        {.id = "log :: underflow range",
         .fn = BIG_FN(log),
         .input = "1e-100000000",
         .expected = "-100000000",
         .tol = "1e-30"},
        {.id = "log :: overflow range",
         .fn = BIG_FN(log),
         .input = "1e100000000",
         .expected = "100000000",
         .tol = "1e-30"},
        {.id = "ln :: one", .fn = BIG_FN(ln), .input = "1", .expected = "0", .tol = "1e-40"},
        {.id = "sqrt :: four",
         .fn = BIG_FN(sqrt),
         .input = "4.0",
         .expected = "2.0",
         .tol = nullptr},
    };

    for (const auto &tc : big_cases) {
        test_detail::with_case(ctx, std::string("bigreal :: ") + tc.id, [&] {
            const BigReal got = (c.*tc.fn)(BigReal(tc.input));
            if (tc.tol == nullptr)
                EXPECT_EQ(ctx, got, BigReal(tc.expected));
            else
                EXPECT_TRUE(ctx, approx_big(got, BigReal(tc.expected), BigReal(tc.tol)));
        });
    }

    TEST_CASE(ctx, "bigreal :: exp of ln two", {
        EXPECT_TRUE(ctx, approx_big(c.exp(c.ln(BigReal("2"))), BigReal("2"), BigReal("1e-45")));
    });

    TEST_CASE(ctx, "bigreal :: root negative odd degree", {
        EXPECT_TRUE(
            ctx, approx_big(c.root(BigReal("-27"), BigReal("3")), BigReal("-3"), BigReal("1e-30")));
    });
    // An odd degree reached through a division that leaves a guard-digit residue is still
    // odd, so this must compute rather than reject.
    TEST_CASE(ctx, "bigreal :: root of a negative takes a quotient degree", {
        EXPECT_TRUE(
            ctx,
            approx_big(
                c.root(BigReal("-8"), BigReal("9e400") / BigReal("3e400")),
                BigReal("-2"),
                BigReal("1e-40")));
    });

    TEST_CASE(
        ctx, "bigreal :: sqrt domain throws", { EXPECT_THROWS(ctx, c.sqrt(BigReal("-1.0"))); });

    // Ordering, not a value: these carry no expected result to tabulate.
    TEST_CASE(ctx, "bigreal :: ln negative", {
        EXPECT_TRUE(ctx, c.ln(BigReal("1e-100000000")) < BigReal("0"));
    });
    TEST_CASE(ctx, "bigreal :: ln ordering", {
        EXPECT_TRUE(ctx, c.ln(BigReal("1e-100000000")) < c.ln(BigReal("1e-1")));
    });

    // ----
    // Complex
    // ----
    TEST_CASE(ctx, "complex :: log domain throws", { EXPECT_THROWS(ctx, c.log(Z(0.0, 0.0))); });
    TEST_CASE(ctx, "complex :: ln domain throws", { EXPECT_THROWS(ctx, c.ln(Z(0.0, 0.0))); });

    const Z i(0.0, 1.0);
    const Z i_pow = c.pow(i, Z(2.0, 0.0));
    TEST_CASE(ctx, "complex :: pow i squared real", {
        EXPECT_TRUE(ctx, approx(i_pow.real(), -1.0, 1e-12));
    });
    TEST_CASE(ctx, "complex :: pow i squared imag", {
        EXPECT_TRUE(ctx, approx(i_pow.imag(), 0.0, 1e-12));
    });

    const Z z_sqrt = c.sqrt(Z(-4.0, 0.0));
    TEST_CASE(ctx, "complex :: sqrt negative real", {
        EXPECT_TRUE(ctx, approx(z_sqrt.real(), 0.0, 1e-12));
    });
    TEST_CASE(ctx, "complex :: sqrt negative imag", {
        EXPECT_TRUE(ctx, approx(z_sqrt.imag(), 2.0, 1e-12));
    });

    // Euler's identity is the shortest statement that exp is not pow(e, x) here.
    const Z euler = c.exp(Z(0.0, boost::math::constants::pi<double>()));
    TEST_CASE(ctx, "complex :: exp of i pi real", {
        EXPECT_TRUE(ctx, approx(euler.real(), -1.0, 1e-15));
    });
    TEST_CASE(ctx, "complex :: exp of i pi imag", {
        EXPECT_TRUE(ctx, approx(euler.imag(), 0.0, 1e-15));
    });

    // ----
    // BigComplex
    // ----
    const BC z("1e400", "1");
    const BC z_pow2 = c.pow(z, BC("2"));
    TEST_CASE(
        ctx, "bigcomplex :: pow square", { EXPECT_TRUE(ctx, approx_big(z_pow2, c.mul(z, z))); });

    const BC z_sqrt_bc = c.sqrt(z);
    TEST_CASE(ctx, "bigcomplex :: sqrt roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.mul(z_sqrt_bc, z_sqrt_bc), z));
    });

    const BC z_root = c.root(z, BC("2"));
    TEST_CASE(ctx, "bigcomplex :: root roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.pow(z_root, BC("2")), z));
    });

    const BC z_log = c.log(z);
    TEST_CASE(ctx, "bigcomplex :: log pow roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.pow(BC("10"), z_log), z, BF("1e-20")));
    });

    const BC z_ln("1e10", "1e-5");
    const BF &ln_ten = boost::math::constants::ln_ten<BF>();
    const BC ln_from_log = c.log(z_ln) * BC(ln_ten, BF(0));
    TEST_CASE(ctx, "bigcomplex :: ln matches log", {
        EXPECT_TRUE(ctx, approx_big(c.ln(z_ln), ln_from_log, BF("1e-20")));
    });

    // exp and ln are inverses on the big complex arm too. The magnitude stays small
    // here: exp of z_ln above would overflow the type outright.
    const BC z_small("1.5", "0.5");
    TEST_CASE(ctx, "bigcomplex :: ln exp roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.ln(c.exp(z_small)), z_small, BF("1e-20")));
    });
}
