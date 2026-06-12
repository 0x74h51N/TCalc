#pragma once

#include <complex>
#include <cstdint>
#include <boost/multiprecision/cpp_complex.hpp>
#include <boost/multiprecision/cpp_dec_float.hpp>
#include <boost/rational.hpp>

constexpr int kBigRealPrecisionDigits = 50;

// Wider exponent range so expressions like 1e-100000000 remain representable
// (cpp_dec_float_50 underflows at |exponent10| > 67108864).
using BigReal = boost::multiprecision::number<
    boost::multiprecision::cpp_dec_float<kBigRealPrecisionDigits, std::int64_t>>;

using Complex = std::complex<double>;
using BigComplex = boost::multiprecision::cpp_complex_50;

/// Exact rational number backed by boost::rational<int64_t>.
struct Rational {
    boost::rational<std::int64_t> frac{0};

    constexpr Rational() = default;
    explicit Rational(std::int64_t n)
        : frac(n) {}
    Rational(std::int64_t num, std::int64_t den)
        : frac(num, den) {}
    explicit Rational(boost::rational<std::int64_t> f)
        : frac(f) {}

    static Rational from_int(std::int64_t n) { return Rational(n); }

    [[nodiscard]] std::int64_t numerator() const { return frac.numerator(); }
    [[nodiscard]] std::int64_t denominator() const { return frac.denominator(); }

    [[nodiscard]] double to_double() const { return boost::rational_cast<double>(frac); }

    bool operator==(const Rational &o) const noexcept { return frac == o.frac; }

    bool operator!=(const Rational &o) const noexcept { return !(*this == o); }
};
