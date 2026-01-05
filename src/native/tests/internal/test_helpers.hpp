#pragma once

#include "calc/pub/calculator.hpp"
#include "parser/pub/parser.hpp"

#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <limits>
#include <string>
#include <utility>
#include <vector>

#include <sys/ioctl.h>
#include <unistd.h>

/// Tracks test assertions and verbosity for native test runs.
struct TestContext {
    int failures = 0;
    int checks = 0;
    int cases = 0;
    int case_failures = 0;
    bool case_failed_reported = false;
    enum class OutputMode {
        Quiet,
        Mid,
        Verbose,
    };
    OutputMode output = OutputMode::Mid;
    std::string current_case{};
};

/// Simple test case pairing input data with an expected result.
template <typename InputT, typename ExpectedT> struct Case {
    InputT input;
    ExpectedT expected;
};

namespace test_detail {
inline constexpr const char *kRed = "\033[31m";
inline constexpr const char *kGreen = "\033[32m";
inline constexpr const char *kYellow = "\033[33m";
inline constexpr const char *kReset = "\033[0m";

inline const char *color_code(const TestContext &ctx, const char *code) {
    (void)ctx;
    return code;
}

inline const char *color_reset(const TestContext &ctx) {
    return color_code(ctx, kReset);
}

inline const char *status_word(bool ok) {
    return ok ? "PASSED" : "FAILED";
}

inline void
status_line(const TestContext &ctx, bool passed, std::string_view text, bool new_block = false) {
    if (new_block) {
        std::cout << "\n";
    }
    const char *label = status_word(passed);
    const char *color = passed ? kGreen : kRed;
    std::cout << color_code(ctx, color) << label << color_reset(ctx) << " " << text << "\n";
}

template <typename Fn>
inline void detail_line(const TestContext &ctx, std::string_view label, Fn &&fn) {
    std::cout << "  " << color_code(ctx, kYellow) << label << color_reset(ctx) << " ";
    std::forward<Fn>(fn)();
    std::cout << "\n";
}

inline void fail_case(TestContext &ctx) {
    if (ctx.case_failed_reported) {
        return;
    }
    if (ctx.current_case.empty()) {
        return;
    }
    ctx.case_failed_reported = true;
    status_line(ctx, false, ctx.current_case, true);
    std::cout << "\n";
}

inline std::string summary_line(int failed, int passed, std::int64_t ms) {
    std::ostringstream os;
    if (failed != 0) {
        os << failed << " " << status_word(false) << ", ";
    }
    os << passed << " " << status_word(true) << " IN " << ms << "ms";
    return os.str();
}

inline std::size_t terminal_width() {
    winsize w{};
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &w) == 0 && w.ws_col > 0) {
        return static_cast<std::size_t>(w.ws_col);
    }

    if (const char *cols = std::getenv("COLUMNS"); cols != nullptr) {
        const long v = std::strtol(cols, nullptr, 10);
        if (v > 0) {
            return static_cast<std::size_t>(v);
        }
    }

    return 120;
}

inline void print_banner(
    const TestContext &ctx, std::ostream &os, std::string_view label, const char *color = nullptr) {
    const std::size_t width = terminal_width();
    const std::size_t content_len = label.size() + 2; // " " + label + " "
    const std::size_t pad_total = (width > content_len) ? (width - content_len) : 0;
    const std::size_t pad_left = pad_total / 2;
    const std::size_t pad_right = pad_total - pad_left;

    if (color) {
        os << color_code(ctx, color);
    }
    os << std::string(pad_left, '=') << " " << label << " " << std::string(pad_right, '=');
    if (color) {
        os << color_reset(ctx);
    }
    os << "\n";
}

inline bool out(const TestContext &ctx) {
    return ctx.output != TestContext::OutputMode::Quiet;
}

inline std::string case_prefix(const TestContext &ctx) {
    if (ctx.current_case.empty()) {
        return {};
    }
    return ctx.current_case + " ";
}

struct ScopedCase {
    TestContext &ctx;
    std::string prev;

    explicit ScopedCase(TestContext &ctx_, std::string name)
        : ctx(ctx_)
        , prev(ctx_.current_case) {
        if (prev.empty()) {
            ctx.current_case = std::move(name);
        } else {
            ctx.current_case = prev + " :: " + std::move(name);
        }
    }

    ~ScopedCase() { ctx.current_case = std::move(prev); }
};

template <typename Fn> inline void with_case(TestContext &ctx, std::string name, Fn &&fn) {
    const int failures_before = ctx.failures;
    ScopedCase scoped(ctx, std::move(name));
    const std::string label = ctx.current_case;
    ctx.cases += 1;
    ctx.case_failed_reported = false;
    std::forward<Fn>(fn)();
    const bool ok = (ctx.failures == failures_before);
    if (!ok) {
        ctx.case_failures += 1;
    }
}

template <typename Fn>
inline void run_suite(TestContext &ctx, const char *name, const char *file, Fn &&fn) {
    const int cases_before = ctx.cases;
    const int case_failures_before = ctx.case_failures;

    const auto start = std::chrono::steady_clock::now();

    if (out(ctx)) {
        const std::string label = std::string("RUN ") + name;
        print_banner(ctx, std::cout, label, kYellow);
        std::cout << file << "\n" << std::flush;
    }

    try {
        ScopedCase suite_case(ctx, name);
        std::forward<Fn>(fn)(ctx);
    } catch (const std::exception &e) {
        ctx.failures += 1;
        status_line(ctx, false, std::string(name) + " unhandled exception: " + e.what(), true);
    } catch (...) {
        ctx.failures += 1;
        status_line(ctx, false, std::string(name) + " unhandled unknown exception", true);
    }

    const auto end = std::chrono::steady_clock::now();
    const auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    const int suite_case_failures = ctx.case_failures - case_failures_before;
    const int suite_cases_total = ctx.cases - cases_before;
    const int suite_cases_passed = (ctx.cases - cases_before) - suite_case_failures;
    const char *banner_color = (suite_case_failures == 0) ? kGreen : kRed;

    if (out(ctx)) {
        if (ctx.output == TestContext::OutputMode::Mid) {
            std::cout << suite_cases_total << " cases\n\n";
        }
        const std::string summary =
            summary_line(suite_case_failures, suite_cases_passed, elapsed_ms.count());
        print_banner(ctx, std::cout, summary, banner_color);
    }
}
} // namespace test_detail

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

inline std::string_view token_kind_name(tcalc::parser::TokenKind kind) {
    static constexpr std::array<std::string_view, 4> kNames{"Number", "Op", "LParen", "RParen"};
    const auto idx = static_cast<std::size_t>(kind);
    if (idx >= kNames.size()) {
        return "<unknown>";
    }
    return kNames[idx];
}

inline std::string_view op_id_name(tcalc::ops::OpId id) {
    using tcalc::ops::OpId;
    if (id == OpId::Count) {
        return "Count";
    }
    const auto *spec = tcalc::ops::op_spec(id);
    if (spec == nullptr) {
        return "<unknown>";
    }
    return spec->method;
}

inline void print_value(std::ostream &os, const tcalc::parser::Token &tok) {
    os << "Token{kind=" << token_kind_name(tok.kind) << ", op_id=" << op_id_name(tok.op_id);

    if (tok.kind == tcalc::parser::TokenKind::Op && tok.op_id != tcalc::ops::OpId::Count) {
        if (const auto *spec = tcalc::ops::op_spec(tok.op_id)) {
            os << "(";
            print_value(os, spec->symbol);
            os << ")";
        }
    }

    os << ", value=\"";
    print_value(os, tok.value);
    os << "\"}";
}

inline void print_value(std::ostream &os, const std::vector<tcalc::parser::Token> &values) {
    os << "[";
    if (!values.empty()) {
        os << "\n";
    }

    for (std::size_t i = 0; i < values.size(); ++i) {
        os << "  ";
        print_value(os, values[i]);
        if (i + 1 != values.size()) {
            os << ",";
        }
        os << "\n";
    }

    os << "]";
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
    const bool ok = (got == expected);
    if (!ok) {
        ctx.failures += 1;
        test_detail::fail_case(ctx);
        if (test_detail::out(ctx)) {
            test_detail::detail_line(
                ctx, "EXPECT_EQ:", [&] { std::cout << got_expr << " == " << expected_expr; });
            test_detail::detail_line(ctx, "GOT:", [&] { print_value(std::cout, got); });
            test_detail::detail_line(ctx, "EXPECTED:", [&] { print_value(std::cout, expected); });
            test_detail::detail_line(ctx, "AT:", [&] { std::cout << file << ":" << line; });
        }
        return;
    }

    if (ctx.output == TestContext::OutputMode::Verbose) {
        const std::string prefix = test_detail::case_prefix(ctx);
        test_detail::status_line(
            ctx, true, prefix + "EXPECT_EQ: " + got_expr + " == " + expected_expr);
        return;
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
        test_detail::fail_case(ctx);
        if (test_detail::out(ctx)) {
            test_detail::detail_line(ctx, "EXPECT_TRUE:", [&] {
                std::cout << expr;
                if (message) {
                    std::cout << " (" << message << ")";
                }
            });
            test_detail::detail_line(ctx, "AT:", [&] { std::cout << file << ":" << line; });
        }
        return;
    }

    if (ctx.output == TestContext::OutputMode::Verbose) {
        const std::string prefix = test_detail::case_prefix(ctx);
        test_detail::status_line(ctx, true, prefix + "EXPECT_TRUE: " + expr);
        return;
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
        if (ctx.output == TestContext::OutputMode::Verbose) {
            const std::string prefix = test_detail::case_prefix(ctx);
            test_detail::status_line(ctx, true, prefix + "EXPECT_THROWS: " + expr);
            return;
        }
        return;
    }
    ctx.failures += 1;
    test_detail::fail_case(ctx);
    if (test_detail::out(ctx)) {
        test_detail::detail_line(ctx, "EXPECT_THROWS:", [&] { std::cout << expr; });
        test_detail::detail_line(ctx, "AT:", [&] { std::cout << file << ":" << line; });
    }
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
/// Run a group of expectations under a single id (printed once on success).
#define TEST_CASE(ctx, id, ...) test_detail::with_case((ctx), (id), [&] { __VA_ARGS__; })
