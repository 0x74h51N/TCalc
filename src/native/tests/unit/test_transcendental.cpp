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
using RatBinFn = Rational (Calculator::*)(const Rational &, const Rational &) const;
using ComplexBinFn =
    Calculator::Complex (Calculator::*)(Calculator::Complex, Calculator::Complex) const;
using BigComplexBinFn = BigComplex (Calculator::*)(const BigComplex &, const BigComplex &) const;

/// Overloaded names need the target signature spelled out to take an address.
#define REAL_FN(name) static_cast<RealFn>(&Calculator::name)
#define REAL_BIN_FN(name) static_cast<RealBinFn>(&Calculator::name)
#define BIG_FN(name) static_cast<BigFn>(&Calculator::name)
#define RAT_BIN_FN(name) static_cast<RatBinFn>(&Calculator::name)
#define COMPLEX_BIN_FN(name) static_cast<ComplexBinFn>(&Calculator::name)
#define BIG_COMPLEX_BIN_FN(name) static_cast<BigComplexBinFn>(&Calculator::name)

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

/// The value, then the base.
struct RatBinCase {
    const char *id;
    RatBinFn fn;
    Rational value;
    Rational base;
    Rational expected;
};

/// A value/base pair that has no exact answer and must throw rather than approximate one.
struct RatRejectCase {
    const char *id;
    RatBinFn fn;
    Rational value;
    Rational base;
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

/// A root whose exact value is a double on both parts; asserted with no tolerance.
struct ComplexRootCase {
    const char *id;
    ComplexBinFn fn = COMPLEX_BIN_FN(root);
    Calculator::Complex x;
    Calculator::Complex y;
    Calculator::Complex expected;
};

/// The same for BigComplex; a result with an irrational part carries `tol` on each part.
struct BigComplexRootCase {
    const char *id;
    BigComplexBinFn fn = BIG_COMPLEX_BIN_FN(root);
    BigComplex x;
    BigComplex y;
    BigComplex expected;
    const char *tol = nullptr;
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

    // These are exact through std::log10 today and wrong through log(a)/log(10).
    const std::vector<RealBinCase> log_double_cases = {
        {.id = "log_10(1e21) is exactly 21",
         .fn = REAL_BIN_FN(log),
         .x = 1e21,
         .y = 10.0,
         .expected = 21.0,
         .tol = 0.0},
        {.id = "log_10(1e23) is exactly 23",
         .fn = REAL_BIN_FN(log),
         .x = 1e23,
         .y = 10.0,
         .expected = 23.0,
         .tol = 0.0},
    };

    for (const auto &tc : log_double_cases) {
        test_detail::with_case(ctx, std::string("real :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, (c.*tc.fn)(tc.x, tc.y), tc.expected);
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

    // Base 1 makes the ratio x/0. Without the guard, promote_range sees the resulting
    // infinity and widens the call into BigReal instead of raising.
    TEST_CASE(ctx, "real :: log base one throws", { EXPECT_THROWS(ctx, c.log(8.0, 1.0)); });
    TEST_CASE(ctx, "real :: log base zero throws", { EXPECT_THROWS(ctx, c.log(8.0, 0.0)); });

    // The Rational arm answers exactly or raises, and apply retries in double. This is root's
    // mechanism, and it is why log_3(243) is 5 rather than 4.999999999999999.
    const std::vector<RatBinCase> log_base_cases = {
        {.id = "log_2(8) is exactly 3",
         .fn = RAT_BIN_FN(log),
         .value = Rational(8),
         .base = Rational(2),
         .expected = Rational(3)},
        {.id = "log_3(243) is exactly 5",
         .fn = RAT_BIN_FN(log),
         .value = Rational(243),
         .base = Rational(3),
         .expected = Rational(5)},
        {.id = "log_2(1/8) is exactly -3",
         .fn = RAT_BIN_FN(log),
         .value = Rational(1, 8),
         .base = Rational(2),
         .expected = Rational(-3)},
        {.id = "log_{1/2}(8) is exactly -3",
         .fn = RAT_BIN_FN(log),
         .value = Rational(8),
         .base = Rational(1, 2),
         .expected = Rational(-3)},
    };

    for (const auto &tc : log_base_cases) {
        test_detail::with_case(ctx, std::string("rational :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, (c.*tc.fn)(tc.value, tc.base), tc.expected);
        });
    }

    // None of these has an integer answer, or a base that could produce one; all three raise
    // rather than approximate.
    const std::vector<RatRejectCase> log_reject_cases = {
        {.id = "log_2(10) has no integer answer",
         .fn = RAT_BIN_FN(log),
         .value = Rational(10),
         .base = Rational(2)},
        {.id = "log base one has no answer",
         .fn = RAT_BIN_FN(log),
         .value = Rational(8),
         .base = Rational(1)},
        {.id = "log of zero has no answer",
         .fn = RAT_BIN_FN(log),
         .value = Rational(0),
         .base = Rational(2)},
    };

    for (const auto &tc : log_reject_cases) {
        test_detail::with_case(ctx, std::string("rational :: ") + tc.id, [&] {
            EXPECT_THROWS(ctx, (c.*tc.fn)(tc.value, tc.base));
        });
    }

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

    // A BigReal is never domain-checked ahead of the kernel (unlike double, whose non-positive
    // value is caught by promotion before this arm ever runs), so it needs its own guards.
    TEST_CASE(ctx, "bigreal :: log_2(8)", {
        EXPECT_TRUE(
            ctx, approx_big(c.log(BigReal("8"), BigReal("2")), BigReal("3"), BigReal("1e-40")));
    });
    TEST_CASE(ctx, "bigreal :: log of a non-positive value throws", {
        EXPECT_THROWS(ctx, c.log(BigReal("-1"), BigReal("2")));
    });
    TEST_CASE(ctx, "bigreal :: log base one throws", {
        EXPECT_THROWS(ctx, c.log(BigReal("8"), BigReal("1")));
    });
    TEST_CASE(ctx, "bigreal :: log base zero throws", {
        EXPECT_THROWS(ctx, c.log(BigReal("8"), BigReal("0")));
    });

    // ----
    // Complex
    // ----
    TEST_CASE(ctx, "complex :: log domain throws", { EXPECT_THROWS(ctx, c.log(Z(0.0, 0.0))); });
    TEST_CASE(ctx, "complex :: ln domain throws", { EXPECT_THROWS(ctx, c.ln(Z(0.0, 0.0))); });

    // A complex base has no ordering, so only what the type can express is guarded: zero,
    // the same as the unary overload.
    TEST_CASE(ctx, "complex :: binary log of zero value throws", {
        EXPECT_THROWS(ctx, c.log(Z(0.0, 0.0), Z(2.0, 0.0)));
    });
    TEST_CASE(ctx, "complex :: binary log of zero base throws", {
        EXPECT_THROWS(ctx, c.log(Z(2.0, 0.0), Z(0.0, 0.0)));
    });
    const Z log_binary = c.log(Z(100.0, 0.0), Z(10.0, 0.0));
    TEST_CASE(ctx, "complex :: log_10(100) real part", {
        EXPECT_TRUE(ctx, approx(log_binary.real(), 2.0, 1e-12));
    });
    TEST_CASE(ctx, "complex :: log_10(100) imag part", {
        EXPECT_TRUE(ctx, approx(log_binary.imag(), 0.0, 1e-12));
    });

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

    // Each expected value is the exact principal root rounded to double, computed at 400 bits.
    // pow goes through exp(log) and leaves its rounding in both parts:
    // (-4) root 2 has 1.2246467991473532e-16 as its real part.
    constexpr double kInf = std::numeric_limits<double>::infinity();
    const std::vector<ComplexRootCase> complex_root_cases = {
        {.id = "root :: negative, degree 2",
         .x = Z(-4.0, 0.0),
         .y = Z(2.0, 0.0),
         .expected = Z(0.0, 2.0)},
        {.id = "root :: minus one, degree 2",
         .x = Z(-1.0, 0.0),
         .y = Z(2.0, 0.0),
         .expected = Z(0.0, 1.0)},
        {.id = "root :: irrational negative, degree 2",
         .x = Z(-2.0, 0.0),
         .y = Z(2.0, 0.0),
         .expected = Z(0.0, 1.4142135623730951)},
        {.id = "root :: large negative, degree 2",
         .x = Z(-1e20, 0.0),
         .y = Z(2.0, 0.0),
         .expected = Z(0.0, 1e10)},
        {.id = "root :: huge negative, degree 2",
         .x = Z(-1e300, 0.0),
         .y = Z(2.0, 0.0),
         .expected = Z(0.0, 1e150)},
        {.id = "root :: tiny negative, degree 2",
         .x = Z(-1e-300, 0.0),
         .y = Z(2.0, 0.0),
         .expected = Z(0.0, 1e-150)},
        {.id = "root :: gaussian square",
         .x = Z(-7.0, 24.0),
         .y = Z(2.0, 0.0),
         .expected = Z(3.0, 4.0)},
        {.id = "root :: imaginary, degree 2",
         .x = Z(0.0, 2.0),
         .y = Z(2.0, 0.0),
         .expected = Z(1.0, 1.0)},
        {.id = "root :: negative imaginary, degree 2",
         .x = Z(0.0, -2.0),
         .y = Z(2.0, 0.0),
         .expected = Z(1.0, -1.0)},
        {.id = "root :: large gaussian square",
         .x = Z(3298534883328.0, 4398046511104.0),
         .y = Z(2.0, 0.0),
         .expected = Z(2097152.0, 1048576.0)},
        {.id = "root :: positive real, degree 3",
         .x = Z(8.0, 0.0),
         .y = Z(3.0, 0.0),
         .expected = Z(2.0, 0.0)},
        {.id = "root :: huge positive real, degree 3",
         .x = Z(1e300, 0.0),
         .y = Z(3.0, 0.0),
         .expected = Z(1e100, 0.0)},
        {.id = "root :: no exact root, degree 3",
         .x = Z(2.0, 0.0),
         .y = Z(3.0, 0.0),
         .expected = Z(1.2599210498948732, 0.0)},
        {.id = "root :: negative, degree 3",
         .x = Z(-8.0, 0.0),
         .y = Z(3.0, 0.0),
         .expected = Z(1.0, 1.7320508075688772)},
        {.id = "root :: minus one, degree 3",
         .x = Z(-1.0, 0.0),
         .y = Z(3.0, 0.0),
         .expected = Z(0.5, 0.8660254037844386)},
        {.id = "root :: imaginary, degree 3",
         .x = Z(0.0, 8.0),
         .y = Z(3.0, 0.0),
         .expected = Z(1.7320508075688772, 1.0)},
        {.id = "root :: negative imaginary, degree 3",
         .x = Z(0.0, -8.0),
         .y = Z(3.0, 0.0),
         .expected = Z(1.7320508075688772, -1.0)},
        {.id = "root :: gaussian cube",
         .x = Z(-117.0, 44.0),
         .y = Z(3.0, 0.0),
         .expected = Z(3.0, 4.0)},
        {.id = "root :: large gaussian cube",
         .x = Z(2.305843009213694e18, 1.2682136550675317e19),
         .y = Z(3.0, 0.0),
         .expected = Z(2097152.0, 1048576.0)},
        {.id = "root :: minus one, degree 4",
         .x = Z(-1.0, 0.0),
         .y = Z(4.0, 0.0),
         .expected = Z(0.7071067811865476, 0.7071067811865476)},
        {.id = "root :: negative, degree 4",
         .x = Z(-16.0, 0.0),
         .y = Z(4.0, 0.0),
         .expected = Z(1.4142135623730951, 1.4142135623730951)},
        {.id = "root :: gaussian fourth power",
         .x = Z(-527.0, -336.0),
         .y = Z(4.0, 0.0),
         .expected = Z(4.0, -3.0)},
        {.id = "root :: minus one, degree 5",
         .x = Z(-1.0, 0.0),
         .y = Z(5.0, 0.0),
         .expected = Z(0.8090169943749475, 0.5877852522924731)},
        {.id = "root :: gaussian fifth power",
         .x = Z(404.0, 1121.0),
         .y = Z(5.0, 0.0),
         .expected = Z(4.0, 1.0)},
        {.id = "root :: negative, degree 6",
         .x = Z(-64.0, 0.0),
         .y = Z(6.0, 0.0),
         .expected = Z(1.7320508075688772, 1.0)},
        {.id = "root :: minus one, degree 1000",
         .x = Z(-1.0, 0.0),
         .y = Z(1000.0, 0.0),
         .expected = Z(0.9999950652018582, 0.0031415874858795635)},
        // One ulp from the correctly rounded value: 1/1e30 is not exact in double. Accepted by the
        // human agent, 2026-11-11.
        {.id = "root :: minus one, degree 1e30",
         .x = Z(-1.0, 0.0),
         .y = Z(1e30, 0.0),
         .expected = Z(1.0, 3.1415926535897927e-30)},
        {.id = "root :: negative degree",
         .x = Z(-4.0, 0.0),
         .y = Z(-2.0, 0.0),
         .expected = Z(0.0, -0.5)},
        {.id = "root :: fractional degree",
         .x = Z(-4.0, 0.0),
         .y = Z(0.5, 0.0),
         .expected = Z(16.0, 0.0)},
        {.id = "root :: huge negative, degree -2",
         .x = Z(-1e300, 0.0),
         .y = Z(-2.0, 0.0),
         .expected = Z(0.0, -1e-150)},
        {.id = "root :: tiny negative, degree -2",
         .x = Z(-1e-300, 0.0),
         .y = Z(-2.0, 0.0),
         .expected = Z(0.0, -1e150)},
        {.id = "root :: minus one, degree -3",
         .x = Z(-1.0, 0.0),
         .y = Z(-3.0, 0.0),
         .expected = Z(0.5, -0.8660254037844386)},
        {.id = "root :: negative, degree -3",
         .x = Z(-8.0, 0.0),
         .y = Z(-3.0, 0.0),
         .expected = Z(0.25, -0.4330127018922193)},
        {.id = "root :: gaussian, degree -3",
         .x = Z(-117.0, 44.0),
         .y = Z(-3.0, 0.0),
         .expected = Z(0.12, -0.16)},
        {.id = "root :: minus one, degree -4",
         .x = Z(-1.0, 0.0),
         .y = Z(-4.0, 0.0),
         .expected = Z(0.7071067811865476, -0.7071067811865476)},
        {.id = "root :: zero radicand, degree 3",
         .x = Z(0.0, 0.0),
         .y = Z(3.0, 0.0),
         .expected = Z(0.0, 0.0)},
        {.id = "root :: gaussian, degree 1",
         .x = Z(-7.0, 24.0),
         .y = Z(1.0, 0.0),
         .expected = Z(-7.0, 24.0)},
        {.id = "root :: gaussian, degree -1",
         .x = Z(-7.0, 24.0),
         .y = Z(-1.0, 0.0),
         .expected = Z(-0.0112, -0.0384)},
        {.id = "root :: gaussian, degree 0.25",
         .x = Z(-7.0, 24.0),
         .y = Z(0.25, 0.0),
         .expected = Z(164833.0, 354144.0)},
        {.id = "root :: gaussian, degree -0.5",
         .x = Z(-7.0, 24.0),
         .y = Z(-0.5, 0.0),
         .expected = Z(-0.00134912, 0.00086016)},
        // A power past double range keeps pow's inf, not the NaN of inf * inf in a complex product.
        {.id = "root :: overflowing power",
         .x = Z(1.0, 1.0),
         .y = Z(1.0 / 3000.0, 0.0),
         .expected = Z(kInf, -kInf)},
        {.id = "root :: underflowing power",
         .x = Z(1.0, 1.0),
         .y = Z(-1.0 / 3000.0, 0.0),
         .expected = Z(0.0, 0.0)},
        {.id = "pow :: long integer power",
         .fn = COMPLEX_BIN_FN(pow),
         .x = Z(1.001, 0.001),
         .y = Z(100.0, 0.0),
         .expected = Z(1.0996606140809762, 0.11022308918547011)},
        {.id = "root :: degree whose reciprocal is a long integer",
         .x = Z(1.001, 0.001),
         .y = Z(0.01, 0.0),
         .expected = Z(1.0996606140809762, 0.11022308918547011)},
        {.id = "pow :: negative, half",
         .fn = COMPLEX_BIN_FN(pow),
         .x = Z(-4.0, 0.0),
         .y = Z(0.5, 0.0),
         .expected = Z(0.0, 2.0)},
        {.id = "pow :: huge negative, half",
         .fn = COMPLEX_BIN_FN(pow),
         .x = Z(-1e20, 0.0),
         .y = Z(0.5, 0.0),
         .expected = Z(0.0, 1e10)},
        {.id = "pow :: negative, minus half",
         .fn = COMPLEX_BIN_FN(pow),
         .x = Z(-4.0, 0.0),
         .y = Z(-0.5, 0.0),
         .expected = Z(0.0, -0.5)},
        {.id = "pow :: gaussian square",
         .fn = COMPLEX_BIN_FN(pow),
         .x = Z(3.0, 4.0),
         .y = Z(2.0, 0.0),
         .expected = Z(-7.0, 24.0)},
        {.id = "pow :: one plus i squared",
         .fn = COMPLEX_BIN_FN(pow),
         .x = Z(1.0, 1.0),
         .y = Z(2.0, 0.0),
         .expected = Z(0.0, 2.0)},
        {.id = "pow :: gaussian, minus two",
         .fn = COMPLEX_BIN_FN(pow),
         .x = Z(3.0, 4.0),
         .y = Z(-2.0, 0.0),
         .expected = Z(-0.0112, -0.0384)},
        {.id = "pow :: zero base, half",
         .fn = COMPLEX_BIN_FN(pow),
         .x = Z(0.0, 0.0),
         .y = Z(0.5, 0.0),
         .expected = Z(0.0, 0.0)},
    };
    for (const auto &tc : complex_root_cases) {
        test_detail::with_case(ctx, std::string("complex :: ") + tc.id, [&] {
            const Z got = (c.*tc.fn)(tc.x, tc.y);
            EXPECT_EQ(ctx, got.real(), tc.expected.real());
            EXPECT_EQ(ctx, got.imag(), tc.expected.imag());
        });
    }

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

    // pow leaves its rounding in both parts here too: (-4) root 2 has 4.3e-51 as its real part.
    const BC::value_type kBigInf = std::numeric_limits<BC::value_type>::infinity();
    const std::vector<BigComplexRootCase> big_complex_root_cases = {
        {.id = "root :: negative, degree 2", .x = BC(-4, 0), .y = BC(2), .expected = BC(0, 2)},
        {.id = "root :: minus one, degree 2", .x = BC(-1, 0), .y = BC(2), .expected = BC(0, 1)},
        {.id = "root :: huge negative, degree 2",
         .x = BC("-4e400", "0"),
         .y = BC(2),
         .expected = BC("0", "2e200")},
        {.id = "root :: gaussian square", .x = BC(-7, 24), .y = BC(2), .expected = BC(3, 4)},
        {.id = "root :: positive real, degree 3", .x = BC(8, 0), .y = BC(3), .expected = BC(2, 0)},
        {.id = "root :: gaussian cube", .x = BC(-117, 44), .y = BC(3), .expected = BC(3, 4)},
        {.id = "root :: gaussian fourth power",
         .x = BC(-527, -336),
         .y = BC(4),
         .expected = BC(4, -3)},
        {.id = "root :: gaussian fifth power",
         .x = BC(404, 1121),
         .y = BC(5),
         .expected = BC(4, 1)},
        {.id = "root :: negative degree", .x = BC(-4, 0), .y = BC(-2), .expected = BC("0", "-0.5")},
        {.id = "root :: fractional degree", .x = BC(-4, 0), .y = BC("0.5"), .expected = BC(16, 0)},
        {.id = "root :: zero radicand, degree 3", .x = BC(0, 0), .y = BC(3), .expected = BC(0, 0)},
        {.id = "root :: overflowing power",
         .x = BC("-4e400", "0"),
         .y = BC(1) / BC("2147483648"),
         .expected = BC(kBigInf, -kBigInf)},
        {.id = "root :: underflowing power",
         .x = BC("-4e400", "0"),
         .y = BC(-1) / BC("2147483648"),
         .expected = BC(0, 0)},
        {.id = "pow :: huge negative, half",
         .fn = BIG_COMPLEX_BIN_FN(pow),
         .x = BC("-4e400", "0"),
         .y = BC("0.5"),
         .expected = BC("0", "2e200")},
        {.id = "pow :: gaussian square",
         .fn = BIG_COMPLEX_BIN_FN(pow),
         .x = BC(3, 4),
         .y = BC(2),
         .expected = BC(-7, 24)},
        {.id = "pow :: negative, quarter",
         .fn = BIG_COMPLEX_BIN_FN(pow),
         .x = BC(-4, 0),
         .y = BC("0.25"),
         .expected = BC(1, 1)},
        {.id = "root :: degree past the double range",
         .x = BC(-8, 0),
         .y = BC("1e400"),
         .expected = BC("1", "3.1415926535897932384626433832795028841971693993751e-400"),
         .tol = "1e-449"},
    };
    for (const auto &tc : big_complex_root_cases) {
        test_detail::with_case(ctx, std::string("bigcomplex :: ") + tc.id, [&] {
            const BC got = (c.*tc.fn)(tc.x, tc.y);
            if (tc.tol == nullptr) {
                EXPECT_EQ(ctx, got.real(), tc.expected.real());
                EXPECT_EQ(ctx, got.imag(), tc.expected.imag());
            } else {
                EXPECT_TRUE(ctx, approx_big(got.real(), tc.expected.real(), BF(tc.tol)));
                EXPECT_TRUE(ctx, approx_big(got.imag(), tc.expected.imag(), BF(tc.tol)));
            }
        });
    }

    const BC z_log = c.log(z);
    TEST_CASE(ctx, "bigcomplex :: log pow roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.pow(BC("10"), z_log), z, BF("1e-20")));
    });

    // A complex base has no ordering, so only what the type can express is guarded: zero,
    // the same as the unary overload.
    TEST_CASE(ctx, "bigcomplex :: binary log of zero value throws", {
        EXPECT_THROWS(ctx, c.log(BC("0"), BC("2")));
    });
    TEST_CASE(ctx, "bigcomplex :: binary log of zero base throws", {
        EXPECT_THROWS(ctx, c.log(BC("2"), BC("0")));
    });
    const BC z_log_base2 = c.log(z, BC("2"));
    TEST_CASE(ctx, "bigcomplex :: binary log pow roundtrip", {
        EXPECT_TRUE(ctx, approx_big(c.pow(BC("2"), z_log_base2), z, BF("1e-20")));
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
