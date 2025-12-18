#pragma once

#include <complex>
#include <stdexcept>

#include <boost/multiprecision/cpp_dec_float.hpp>

using BigReal = boost::multiprecision::cpp_dec_float_50;

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
	BigReal intdiv(double a, double b) const;
	double mod(double a, double b) const;
	double pow(double a, long long b) const;
	double pow(double a, double b) const;
	double sqrt(double a) const;
	double cbrt(double a) const;
	double root(double a, double b) const;

    // BigReal ops (real-only, extended range)
    BigReal add(const BigReal& a, const BigReal& b) const { return a + b; }
    BigReal sub(const BigReal& a, const BigReal& b) const { return a - b; }
    BigReal mul(const BigReal& a, const BigReal& b) const { return a * b; }
    BigReal div(const BigReal& a, const BigReal& b) const;
    BigReal pow(const BigReal& a, const BigReal& b) const;
    BigReal intdiv(const BigReal& a, const BigReal& b) const;
    BigReal mod(const BigReal& a, const BigReal& b) const;
    BigReal sqrt(const BigReal& a) const;
    BigReal log(const BigReal& a) const;
    BigReal ln(const BigReal& a) const;
    BigReal root(const BigReal& a, const BigReal& b) const;

    // Complex ops
	Complex add(Complex a, Complex b) const { return a + b; }
	Complex sub(Complex a, Complex b) const { return a - b; }
	Complex mul(Complex a, Complex b) const { return a * b; }
	Complex div(Complex a, Complex b) const;
	Complex pow(Complex a, Complex b) const;
	Complex sqrt(Complex a) const;
	Complex root(Complex a, Complex b) const;

    // Polar (cis): cos(a) + i*sin(a) using selected angle unit
    Complex polar(double a, AngleUnit unit) const;
    Complex polar(Complex a, AngleUnit unit) const;

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
    double ln(double a) const;

    Complex log(Complex a) const;
    Complex ln(Complex a) const;

    // Fuctorial
    double fact(double a) const;
    double gamma(double a) const;

    // Permute/Choose
    BigReal permute(long long a, long long b) const;
    BigReal choose(long long a, long long b) const;
};

class CalculatorError : public std::runtime_error {
public:
    explicit CalculatorError(const char* message)
        : std::runtime_error(message) {}
};
