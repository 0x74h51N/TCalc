/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <cstddef>
#include <string>
#include <string_view>

// Single source for call-function + collection error messages.
// TODO: extend to ALL error messages across the engine.
namespace tcalc::errmsg {

inline std::string integers_only(std::string_view fn) {
    return std::string(fn) + " is only defined for integers";
}

inline std::string empty_collection(std::string_view fn) {
    return std::string(fn) + " of an empty collection";
}

inline std::string not_for_point(std::string_view fn) {
    return std::string(fn) + " is not defined for a point";
}

inline std::string unsupported_operand(std::string_view fn) {
    return "unsupported operand type for " + std::string(fn);
}

/// An op asked for an operand the stack cannot give.
inline constexpr std::string_view kPopOperand = "Pop operand, not operand in stack.";

/// The walk ended without producing a value.
inline constexpr std::string_view kOperandStackEmpty = "Operand stack empty";

/// An `=` reached the evaluator: assignment is only valid as the head of a row.
inline constexpr std::string_view kInvalidAssignment = "misplaced =";

/// The left of an `=` is not a name that may be bound.
inline constexpr std::string_view kInvalidAssignmentTarget =
    "left of = must be a single letter (A-Za-z)";

/// `A=` with nothing after the `=`.
inline constexpr std::string_view kEmptyAssignment = "assignment has no value";

/// An operator symbol on the left of an `=`.
inline std::string assignment_target_is_operator(std::string_view symbol) {
    return std::string(symbol) + " is an operator, use another letter";
}

/// A constant on the left of an `=`, subscripted or not.
inline std::string assignment_target_is_constant(std::string_view symbol) {
    return std::string(symbol) + " is defined as a constant, use another letter";
}

inline std::string undefined_variable(std::string_view name) {
    return "undefined variable " + std::string(name);
}

/// A fixed-arity call function has no infix form: `mod 5` must be `mod(a, b)`.
inline std::string needs_call_form(std::string_view fn) {
    return std::string(fn) + " must be written as " + std::string(fn) + "(...)";
}

/// A List holding a List.
inline constexpr std::string_view kListOfList = "List of List not allowed";

/// A List holding both scalars and points.
inline constexpr std::string_view kListMix = "List cannot mix scalars and points";

/// `()`: a Point needs at least one coordinate.
inline constexpr std::string_view kEmptyPoint = "empty Point";

/// A Point coordinate that is itself a list or a point.
inline constexpr std::string_view kPointItemCollection = "Point item cannot be a collection";

/// A brace group holds one value only; it is not a collection literal.
inline constexpr std::string_view kBraceUnsupported = "brace collection type not supported";

/// A comma with nothing between it and the next one.
inline constexpr std::string_view kEmptyElement = "empty element";

/// A fixed-arity call given the wrong number of arguments.
inline std::string takes_arguments(std::string_view fn, std::size_t n) {
    return std::string(fn) + " takes " + std::to_string(n) + " argument" + (n != 1 ? "s" : "");
}

/// A fixed-arity call given a list or a point.
inline std::string not_for_list_or_point(std::string_view fn) {
    return std::string(fn) + " is not defined for a list or point";
}

} // namespace tcalc::errmsg
