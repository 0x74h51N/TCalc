#include <chrono>
#include <iostream>
#include <string>

#include "internal/test_helpers.hpp"

void unit_arithmetic(TestContext &ctx);
void unit_rational(TestContext &ctx);
void unit_transcendental(TestContext &ctx);
void unit_trig(TestContext &ctx);
void unit_combinatorics(TestContext &ctx);
void unit_parser(TestContext &ctx);
void unit_collection(TestContext &ctx);
void unit_statistic(TestContext &ctx);
void unit_number_theory(TestContext &ctx);
void unit_helpers(TestContext &ctx);
void unit_ops(TestContext &ctx);
void unit_eval(TestContext &ctx);

void smoke_stress(TestContext &ctx);

int main(int argc, char **argv) { // NOLINT(modernize-use-trailing-return-type)
    TestContext ctx;
    const auto all_start = std::chrono::steady_clock::now();

    for (int i = 1; i < argc; i++) {
        const std::string arg = argv[i]; // NOLINT(cppcoreguidelines-pro-bounds-pointer-arithmetic)
        if (arg == "-q" || arg == "--quiet") {
            ctx.output = TestContext::OutputMode::Quiet;
        } else if (arg == "-v" || arg == "--verbose") {
            ctx.output = TestContext::OutputMode::Verbose;
        } else if (arg == "-m" || arg == "--mid") {
            ctx.output = TestContext::OutputMode::Mid;
        }
    }

    test_detail::run_suite(
        ctx, "unit test helpers", "src/native/tests/test_test_helpers.cpp", unit_helpers);
    test_detail::run_suite(ctx, "unit ops", "src/native/tests/unit/test_ops.cpp", unit_ops);
    test_detail::run_suite(ctx, "unit eval", "src/native/tests/unit/test_eval.cpp", unit_eval);
    test_detail::run_suite(
        ctx, "unit arithmetic", "src/native/tests/unit/test_arithmetic.cpp", unit_arithmetic);
    test_detail::run_suite(
        ctx, "unit rational", "src/native/tests/unit/test_rational.cpp", unit_rational);
    test_detail::run_suite(
        ctx,
        "unit transcendental",
        "src/native/tests/unit/test_transcendental.cpp",
        unit_transcendental);
    test_detail::run_suite(ctx, "unit trig", "src/native/tests/unit/test_trig.cpp", unit_trig);
    test_detail::run_suite(
        ctx,
        "unit combinatorics",
        "src/native/tests/unit/test_combinatorics.cpp",
        unit_combinatorics);
    test_detail::run_suite(
        ctx, "smoke stress", "src/native/tests/smoke/smoke_stress.cpp", smoke_stress);
    test_detail::run_suite(
        ctx, "unit parser", "src/native/tests/unit/test_parser.cpp", unit_parser);
    test_detail::run_suite(
        ctx, "unit collection", "src/native/tests/unit/test_collection.cpp", unit_collection);
    test_detail::run_suite(
        ctx, "unit statistic", "src/native/tests/unit/test_statistic.cpp", unit_statistic);
    test_detail::run_suite(
        ctx,
        "unit number_theory",
        "src/native/tests/unit/test_number_theory.cpp",
        unit_number_theory);

    const auto all_end = std::chrono::steady_clock::now();
    const auto all_elapsed_ms =
        std::chrono::duration_cast<std::chrono::milliseconds>(all_end - all_start);
    const int passed = ctx.cases - ctx.case_failures;
    const char *banner_color = (ctx.case_failures == 0) ? test_detail::kGreen : test_detail::kRed;
    const std::string summary =
        test_detail::summary_line(ctx.case_failures, passed, all_elapsed_ms.count());
    test_detail::print_banner(ctx, std::cout, summary, banner_color);

    return (ctx.failures == 0) ? 0 : 1;
}
