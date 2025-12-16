#pragma once

#include <complex>
#include <stdexcept>

class Calculator {
public:
    using Complex = std::complex<double>;

    enum class AngleUnit {
        DEG,
        RAD,
        GRAD
    };

    Calculator() = default;

    // Real ops
    double add(double a, double b) const;
    double sub(double a, double b) const;
    double mul(double a, double b) const;
    double div(double a, double b) const;
    double pow(double a, long long b) const;
    double pow(double a, double b) const;
    double sqrt(double a) const;

    // Complex ops
    Complex add(Complex a, Complex b) const;
    Complex sub(Complex a, Complex b) const;
    Complex mul(Complex a, Complex b) const;
    Complex div(Complex a, Complex b) const;
    Complex pow(Complex a, Complex b) const;
    Complex sqrt(Complex a) const;

    // Trig ops
    double sin(double a, AngleUnit unit) const;
    double cos(double a, AngleUnit unit) const;
    double tan(double a, AngleUnit unit) const;

    Complex sin(Complex a, AngleUnit unit) const;
    Complex cos(Complex a, AngleUnit unit) const;
    Complex tan(Complex a, AngleUnit unit) const;

    // Hyperbolic ops
    double sinh(double a) const;
    double cosh(double a) const;
    double tanh(double a) const;

    Complex sinh(Complex a) const;
    Complex cosh(Complex a) const;
    Complex tanh(Complex a) const;
};

class CalculatorError : public std::runtime_error {
public:
    explicit CalculatorError(const char* message)
        : std::runtime_error(message) {}
};
