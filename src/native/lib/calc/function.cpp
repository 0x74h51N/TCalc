/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "calc/pub/calculator.hpp"

#include <numeric>

//
// TODO: Move other functions to here
//

// ---------------------------------------------------------------------------
// GCD / LCM
// ---------------------------------------------------------------------------

long long Calculator::gcd(long long a, long long b) const {
    return std::gcd(a, b);
}

long long Calculator::lcm(long long a, long long b) const {
    if (a == 0 && b == 0)
        return 0;
    return std::lcm(a, b);
}
