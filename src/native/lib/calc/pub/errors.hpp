#pragma once

#include <cstdint>
#include <stdexcept>
#include <string>

/// Mirrors tcalc/errors.py:14 (ErrorKind). Defaults to MathErr so every existing
/// native `throw CalculatorError(msg)` keeps compiling and behaving unchanged.
enum class ErrorKind : std::uint8_t { Invalid, Malformed, MathErr };

class CalculatorError : public std::runtime_error {
  public:
    explicit CalculatorError(const std::string &what, ErrorKind kind = ErrorKind::MathErr)
        : std::runtime_error(what)
        , kind_(kind) {}

    [[nodiscard]] ErrorKind kind() const { return kind_; }

  private:
    ErrorKind kind_;
};
