#include "calculator.hpp"
#include <cmath>


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

double Calculator::pow(double a, double b) const {
    // Int check
    if (std::floor(b) == b) {
        long long exp = static_cast<long long>(b);

        double result = 1.0;
        double base = a;

        if (exp < 0) {
            exp = -exp;
            base = 1.0 / base;
        }

        while (exp > 0) {
            if (exp & 1)
                result *= base;
            base *= base;
            exp >>= 1;
        }

        return result;
    }

    return std::pow(a, b);
}

double Calculator::sqrt(double a) const {
    if (a < 0.0) {
        throw CalculatorError("Math error");
    }
    return std::sqrt(a);
}