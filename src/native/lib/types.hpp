#pragma once

#include <cstdint>
#include <boost/multiprecision/cpp_complex.hpp>
#include <boost/multiprecision/cpp_dec_float.hpp>

constexpr int kBigRealPrecisionDigits = 50;

// Wider exponent range so expressions like 1e-100000000 remain representable
// (cpp_dec_float_50 underflows at |exponent10| > 67108864).
using BigReal = boost::multiprecision::number<
    boost::multiprecision::cpp_dec_float<kBigRealPrecisionDigits, std::int64_t>>;

using BigComplex = boost::multiprecision::cpp_complex_50;
