#pragma once

#include <stdexcept>

class CalculatorError : public std::runtime_error {
public:
    explicit CalculatorError(const char* message)
        : std::runtime_error(message) {}
};

