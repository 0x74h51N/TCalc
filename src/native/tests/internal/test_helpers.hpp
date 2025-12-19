#pragma once

#include "calculator.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>

struct TestContext {
    int failures = 0;
    int checks = 0;
    bool verbose = true;
};

inline bool approx(double a, double b, double eps = 1e-12) {
    return std::abs(a - b) <= eps;
}

inline bool approx_big(const BigReal& a, const BigReal& b, const BigReal& eps = BigReal("1e-40")) {
    using boost::multiprecision::abs;
    return abs(a - b) <= eps;
}

template <typename T>
inline void print_value(std::ostream& os, const T& v) {
    os << v;
}

inline void print_value(std::ostream& os, double v) {
    os << std::setprecision(17) << v;
}

inline void print_value(std::ostream& os, const BigReal& v) {
    os << std::setprecision(std::numeric_limits<BigReal>::digits10) << v;
}

template <typename A, typename B>
inline void expect_eq(
    TestContext& ctx,
    const A& got,
    const B& expected,
    const char* got_expr,
    const char* expected_expr,
    const char* file,
    int line
) {
    ctx.checks += 1;
    if (!(got == expected)) {
        ctx.failures += 1;
        std::cerr << file << ":" << line << " EXPECT_EQ failed: " << got_expr << " == " << expected_expr
                  << "\n";
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

inline void expect_true(TestContext& ctx, bool ok, const char* expr, const char* file, int line) {
    ctx.checks += 1;
    if (!ok) {
        ctx.failures += 1;
        std::cerr << file << ":" << line << " EXPECT_TRUE failed: " << expr << "\n";
    }
}

template <typename Fn>
inline void expect_throws(TestContext& ctx, Fn&& fn, const char* expr, const char* file, int line) {
    ctx.checks += 1;
    try {
        fn();
        ctx.failures += 1;
        std::cerr << file << ":" << line << " EXPECT_THROWS failed: " << expr << "\n";
    } catch (...) {
    }
}

#define EXPECT_TRUE(ctx, expr) expect_true((ctx), (expr), #expr, __FILE__, __LINE__)
#define EXPECT_THROWS(ctx, expr) expect_throws((ctx), [&] { (void)(expr); }, #expr, __FILE__, __LINE__)
#define EXPECT_EQ(ctx, got, expected) \
    expect_eq((ctx), (got), (expected), #got, #expected, __FILE__, __LINE__)
