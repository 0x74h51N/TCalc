#include <iostream>

#include "internal/test_helpers.hpp"

void unit_arithmetic(TestContext& ctx);
void unit_transcendental(TestContext& ctx);
void unit_trig(TestContext& ctx);
void unit_combinatorics(TestContext& ctx);
void smoke_stress(TestContext& ctx);

template <typename Fn>
static void run_suite(TestContext& ctx, const char* name, Fn&& fn) {
    if (ctx.verbose) {
        std::cout << "RUN " << name << "\n";
    }

    try {
        fn(ctx);
    } catch (const std::exception& e) {
        ctx.failures += 1;
        std::cerr << "Unhandled exception in " << name << ": " << e.what() << "\n";
    } catch (...) {
        ctx.failures += 1;
        std::cerr << "Unhandled unknown exception in " << name << "\n";
    }

    if (ctx.verbose) {
        std::cout << "DONE " << name << "\n";
    }
}

int main(int argc, char** argv) {
    TestContext ctx;

    for (int i = 1; i < argc; i++) {
        const std::string arg = argv[i];
        if (arg == "-q" || arg == "--quiet") {
            ctx.verbose = false;
        }
    }

    run_suite(ctx, "unit_arithmetic", unit_arithmetic);
    run_suite(ctx, "unit_transcendental", unit_transcendental);
    run_suite(ctx, "unit_trig", unit_trig);
    run_suite(ctx, "unit_combinatorics", unit_combinatorics);
    run_suite(ctx, "smoke_stress", smoke_stress);

    if (ctx.failures == 0) {
        std::cout << "native tests: OK (" << ctx.checks << " checks)\n";
        return 0;
    }

    std::cerr << "native tests: FAIL (" << ctx.failures << "/" << ctx.checks << ")\n";
    return 1;
}
