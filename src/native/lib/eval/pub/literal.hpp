#pragma once

#include <string_view>

#include "value.hpp"

namespace tcalc::eval {

/// Decide what a number literal denotes: an exact int64, an exact Rational for a
/// decimal that fits one, a double, a BigReal when the literal's magnitude escapes
/// double's range, or a Complex for an imaginary literal such as "3i" or "i".
Value literal_value(std::string_view text);

} // namespace tcalc::eval
