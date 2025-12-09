#pragma once

#include <stdexcept>

class Calculator {
public:
    Calculator() = default;

    double add(double a, double b) const;
    double sub(double a, double b) const;
    double mul(double a, double b) const;
    double div(double a, double b) const;
};

class CalculatorError : public std::runtime_error {
public:
    explicit CalculatorError(const char* message)
        : std::runtime_error(message) {}
};

