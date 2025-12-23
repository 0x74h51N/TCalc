#pragma once

#include <cstddef>
#include <cstdio>
#include <string_view>

#include "calc/internal/errors.hpp"

namespace tcalc::ops {

inline constexpr const char *kSyntaxError = "Syntax Error";
inline constexpr const char *kMalformedExpression = "Malformed Expression";
inline constexpr const char *kMathError = "Math error";
inline constexpr const char *kParserErrorPrefix = "[PARSER ERROR]";
inline constexpr const char *kUnexpectedCharacter = "unexpected character";

inline void print_error_context(const char *kind, std::string_view expr, std::size_t pos,
                                std::string_view detail) {
    std::fprintf(stderr, "%s %s", kParserErrorPrefix, kind);
    if (!detail.empty()) {
        std::fprintf(stderr, ": %.*s", static_cast<int>(detail.size()), detail.data());
    }
    std::fprintf(stderr, "\n");

    if (expr.empty()) {
        return;
    }

    if (pos > expr.size()) {
        pos = expr.size();
    }

    std::fprintf(stderr, "  %.*s\n", static_cast<int>(expr.size()), expr.data());
    std::fprintf(stderr, "  %*s^\n", static_cast<int>(pos), "");
}

[[noreturn]] inline void syntax_error(std::string_view expr = {}, std::size_t pos = 0,
                                      std::string_view detail = {}) {
    print_error_context(kSyntaxError, expr, pos, detail);
    throw CalculatorError(kSyntaxError);
}

[[noreturn]] inline void malformed_expression(std::string_view detail = {}) {
    print_error_context(kMalformedExpression, {}, 0, detail);
    throw CalculatorError(kMalformedExpression);
}

[[noreturn]] inline void math_error(std::string_view detail = {}) {
    print_error_context(kMathError, {}, 0, detail);
    throw CalculatorError(kMathError);
}

} // namespace tcalc::ops