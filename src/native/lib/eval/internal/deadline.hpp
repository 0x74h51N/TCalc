/*
 * TCalc - Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

namespace tcalc::eval {

/// Arms the wall-clock deadline at the outermost evaluate() and disarms on exit. Nested
/// evaluate() calls reuse the outer deadline. A no-op while the budget is unlimited (<= 0).
class DeadlineScope {
  public:
    DeadlineScope();
    ~DeadlineScope();
    DeadlineScope(const DeadlineScope &) = delete;
    DeadlineScope &operator=(const DeadlineScope &) = delete;
    DeadlineScope(DeadlineScope &&) = delete;
    DeadlineScope &operator=(DeadlineScope &&) = delete;

  private:
    bool armed_{false}; // this scope started the clock, so it clears it
};

/// Throw when the armed deadline has passed. Cheap, and free while unarmed (no clock read).
/// Call from bounded loops so a long computation early-exits instead of freezing the app.
void check_deadline();

} // namespace tcalc::eval
