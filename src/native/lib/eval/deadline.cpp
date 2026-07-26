/*
 * TCalc - Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "eval/internal/deadline.hpp"

#include <chrono>
#include <optional>

#include "calc/pub/error_messages.hpp"
#include "calc/pub/errors.hpp"
#include "eval/pub/eval.hpp"

namespace tcalc::eval {
namespace {

// Process-wide budget in milliseconds. 0 (default) means unlimited: benchmarks and the whole
// test suite leave it there so results stay deterministic. Production sets ~500ms; a single
// test sets a tiny budget to prove the guard early-exits. Held in a function-local static so
// it is not a mutable namespace global.
long &budget_ms() {
    static long ms = 0;
    return ms;
}

// The deadline for the evaluation running on this thread, set at the outermost eval_row().
std::optional<std::chrono::steady_clock::time_point> &deadline() {
    thread_local std::optional<std::chrono::steady_clock::time_point> dl;
    return dl;
}

} // namespace

void set_eval_time_budget_ms(long ms) {
    budget_ms() = ms;
}

long eval_time_budget_ms() {
    return budget_ms();
}

DeadlineScope::DeadlineScope() {
    if (budget_ms() > 0 && !deadline()) {
        deadline() = std::chrono::steady_clock::now() + std::chrono::milliseconds(budget_ms());
        armed_ = true;
    }
}

DeadlineScope::~DeadlineScope() {
    if (armed_)
        deadline().reset();
}

void check_deadline() {
    const auto &dl = deadline();
    if (dl && std::chrono::steady_clock::now() > *dl)
        throw CalculatorError(std::string(errmsg::kEvalTimedOut), ErrorKind::MathErr);
}

} // namespace tcalc::eval
