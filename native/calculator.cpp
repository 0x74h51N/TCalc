#include "calculator.hpp"

double Calculator::add(double a, double b) const {
    return a + b;
}

double Calculator::sub(double a, double b) const {
    return a - b;
}

double Calculator::mul(double a, double b) const {
    return a * b;
}

double Calculator::div(double a, double b) const {
    if (b == 0.0) {
        throw CalculatorError("Math error");
    }
    return a / b;
}

