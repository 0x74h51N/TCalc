#pragma once

#include "calc/pub/calculator.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <limits>
#include <string>
#include <utility>
#include <vector>

/// Tracks test assertions and verbosity for native test runs.
struct TestContext {
    int failures = 0;
    int checks = 0;
    bool verbose = true;
};

/// Simple test case pairing input data with an expected result.
template <typename InputT, typename ExpectedT> struct Case {
    InputT input;
    ExpectedT expected;
};

constexpr double kDefaultApproxEps = 1e-12;

/// Approximate double comparison with absolute tolerance.
inline bool approx(double a, double b, double eps = kDefaultApproxEps) {
    return std::abs(a - b) <= eps;
}

/// Approximate BigReal comparison with absolute tolerance.
inline bool approx_big(const BigReal &a, const BigReal &b, const BigReal &eps = BigReal("1e-40")) {
    using boost::multiprecision::abs;
    return abs(a - b) <= eps;
}

/// Approximate multiprecision comparison with scaled tolerance.
template <typename T>
inline bool approx_big(
    const T &a,
    const T &b,
    const boost::multiprecision::cpp_bin_float_50 &eps =
        boost::multiprecision::cpp_bin_float_50("1e-30")) {
    using boost::multiprecision::abs;

    const auto diff = abs(a - b);
    auto scale = abs(a);
    const auto bmag = abs(b);

    if (bmag > scale) {
        scale = bmag;
    }
    if (scale < 1) {
        scale = 1;
    }
    return diff <= eps * scale;
}

/// Print a value if streamable, otherwise emit a placeholder.
template <typename T> inline void print_value(std::ostream &os, const T &v) {
    if constexpr (requires(std::ostream &out, const T &value) { out << value; }) {
        os << v;
    } else {
        os << "<unprintable>";
    }
}

/// Print a double with full precision.
inline void print_value(std::ostream &os, double v) {
    os << std::setprecision(std::numeric_limits<double>::max_digits10) << v;
}

/// Print a BigReal with its configured precision.
inline void print_value(std::ostream &os, const BigReal &v) {
    os << std::setprecision(std::numeric_limits<BigReal>::digits10) << v;
}

/// Print vectors by iterating and delegating to print_value.
template <typename T> inline void print_value(std::ostream &os, const std::vector<T> &values) {
    os << "[";
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0) {
            os << ", ";
        }
        print_value(os, values[i]);
    }
    os << "]";
}

/// Assert equality and record failures with optional verbose output.
template <typename A, typename B>
inline void expect_eq(
    TestContext &ctx,
    const A &got,
    const B &expected,
    const char *got_expr,
    const char *expected_expr,
    const char *file,
    int line) {
    ctx.checks += 1;
    if (!(got == expected)) {
        ctx.failures += 1;
        std::cerr << file << ":" << line << " EXPECT_EQ failed: " << got_expr
                  << " == " << expected_expr << "\n";
        if (ctx.verbose) {
            std::cerr << "  got: ";
            print_value(std::cerr, got);
            std::cerr << "\n";
            std::cerr << "  expected: ";
            print_value(std::cerr, expected);
            std::cerr << "\n";
        }
    }
}

/// Assert a boolean expression and record failures.
inline void expect_true(
    TestContext &ctx,
    bool ok,
    const char *expr,
    const char *file,
    int line,
    const char *message = nullptr) {
    ctx.checks += 1;
    if (!ok) {
        ctx.failures += 1;
        if (message) {
            std::cerr << file << ":" << line << " EXPECT_TRUE failed: " << expr << " (" << message
                      << ")\n";
        } else {
            std::cerr << file << ":" << line << " EXPECT_TRUE failed: " << expr << "\n";
        }
    }
}

/// Assert a condition with a lazily-built message.
template <typename Fn>
inline void
expect_msg(TestContext &ctx, bool ok, const char *expr, const char *file, int line, Fn &&builder) {

    std::ostringstream os;
    std::forward<Fn>(builder)(os);
    const std::string msg = os.str();
    expect_true(ctx, ok, expr, file, line, msg.c_str());
}

/// Assert that a callable throws.
template <typename Fn>
inline void expect_throws(TestContext &ctx, Fn &&fn, const char *expr, const char *file, int line) {
    ctx.checks += 1;
    try {
        std::forward<Fn>(fn)();
    } catch (...) { // expected
        return;
    }
    ctx.failures += 1;
    std::cerr << file << ":" << line << " EXPECT_THROWS failed: " << expr << "\n";
}

/// Shorthand for expect_true with source location.
#define EXPECT_TRUE(ctx, expr, ...)                                                                \
    expect_true((ctx), (expr), #expr, __FILE__, __LINE__ __VA_OPT__(, ) __VA_ARGS__)
/// Shorthand for expect_msg with source location.
#define EXPECT_MSG(ctx, expr, builder)                                                             \
    expect_msg((ctx), (expr), #expr, __FILE__, __LINE__, (builder))
/// Shorthand for expect_throws with source location.
#define EXPECT_THROWS(ctx, expr)                                                                   \
    expect_throws((ctx), [&] { (void)(expr); }, #expr, __FILE__, __LINE__)
/// Shorthand for expect_eq with source location.
#define EXPECT_EQ(ctx, got, expected)                                                              \
    expect_eq((ctx), (got), (expected), #got, #expected, __FILE__, __LINE__)
