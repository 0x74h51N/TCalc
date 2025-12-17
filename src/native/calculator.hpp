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
	    double add(double a, double b) const { return a + b; }
	    double sub(double a, double b) const { return a - b; }
	    double mul(double a, double b) const { return a * b; }
	    double div(double a, double b) const;
	    double mod(double a, double b) const;
	    double pow(double a, long long b) const;
	    double pow(double a, double b) const;
	    double sqrt(double a) const;

    // Complex ops
	    Complex add(Complex a, Complex b) const { return a + b; }
	    Complex sub(Complex a, Complex b) const { return a - b; }
	    Complex mul(Complex a, Complex b) const { return a * b; }
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

    // Inverse Trig ops
    double asin(double a, AngleUnit unit) const;
    double acos(double a, AngleUnit unit) const;
    double atan(double a, AngleUnit unit) const;

    Complex asin(Complex a, AngleUnit unit) const;
    Complex acos(Complex a, AngleUnit unit) const;
    Complex atan(Complex a, AngleUnit unit) const;

    // Inverse Trig Hyperbolic ops
    double asinh(double a) const;
    double acosh(double a) const;
    double atanh(double a) const;

    Complex asinh(Complex a) const;
    Complex acosh(Complex a) const;
    Complex atanh(Complex a) const;


    // Log ops
    double log(double a) const;
    Complex log(Complex a) const;
    double ln(double a) const;
    Complex ln(Complex a) const;
};

class CalculatorError : public std::runtime_error {
public:
    explicit CalculatorError(const char* message)
        : std::runtime_error(message) {}
};
