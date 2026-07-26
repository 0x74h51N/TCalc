/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "eval/internal/closed_forms.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <boost/multiprecision/cpp_int.hpp>
#include "calc/internal/helpers.hpp"
#include "calc/pub/error_messages.hpp"
#include "calc/pub/errors.hpp"
#include "eval/internal/deadline.hpp"
#include "eval/pub/eval.hpp"
#include "eval/pub/literal.hpp"
#include "eval/pub/varstore.hpp"
#include "parser/pub/consts.hpp"
#include "types.hpp"

namespace tcalc::eval {

using BigInt = boost::multiprecision::cpp_int;
using ops::OpId;
using parser::LatexKind;
using parser::Token;
using parser::TokenKind;

namespace {

// Bernoulli numbers B_0..B_24, B_1 = +1/2 convention. Odd B_(>=3) are zero.
// See: https://en.wikipedia.org/wiki/Bernoulli_number
//      https://www.bernoulli.org/
const std::array<CppRat, 25> kBernoulli = {
    CppRat(1),
    CppRat(1, 2),
    CppRat(1, 6),
    CppRat(0),
    CppRat(-1, 30),
    CppRat(0),
    CppRat(1, 42),
    CppRat(0),
    CppRat(-1, 30),
    CppRat(0),
    CppRat(5, 66),
    CppRat(0),
    CppRat(-691, 2730),
    CppRat(0),
    CppRat(7, 6),
    CppRat(0),
    CppRat(-3617, 510),
    CppRat(0),
    CppRat(43867, 798),
    CppRat(0),
    CppRat(-174611, 330),
    CppRat(0),
    CppRat(854513, 138),
    CppRat(0),
    CppRat(-236364091, 2730)};

// C(n, j), built incrementally in exact BigInt: C(n,i+1) = C(n,i) * (n-i)/(i+1).
// See: https://en.wikipedia.org/wiki/Binomial_coefficient
BigInt binom(int n, int j) {
    BigInt r = 1;
    for (int i = 0; i < j; ++i)
        r = r * (n - i) / (i + 1);
    return r;
}

// S_k(m) = sum_{n=1}^{m} n^k, exact.
// Faulhaber in umbral form: S_k(m) = ((B+m)^(k+1) - B^(k+1)) / (k+1), where after
// expanding (B+m)^(k+1) by the binomial theorem each symbolic B^j is the Bernoulli
// number B_j. The subtracted B^(k+1) cancels the j=k+1 term, leaving one plain sum:
//   S_k(m) = 1/(k+1) * sum_{j=0}^{k} C(k+1,j) B_j m^(k+1-j)
// The loop below IS that sum: k+1 terms (the degree, <= 17), NOT m iterations (the range).
//
// See: https://en.wikipedia.org/wiki/Faulhaber%27s_formula
//      https://en.wikipedia.org/wiki/Umbral_calculus
//      https://rosettacode.org/wiki/Faulhaber%27s_formula
CppRat S_k(int k, const BigInt &m) {
    CppRat total = 0;
    for (int j = 0; j <= k; ++j) { // one binomial-expansion term per j
        if (kBernoulli[j] == 0)
            continue; // odd B_(>=3) are zero, skip
        BigInt mpow = 1;
        for (int p = 0; p < k + 1 - j; ++p) // mpow = m^(k+1-j)  (exponentiation, not the sum)
            mpow *= m;
        total += CppRat(binom(k + 1, j)) * kBernoulli[j] * CppRat(mpow); // C(k+1,j) B_j m^(k+1-j)
    }
    return total / (k + 1); // the 1/(k+1) factor
}

} // namespace

CppRat faulhaber_sum(const std::vector<CppRat> &coeffs, std::int64_t a, std::int64_t b) {
    // Sum_{n=a}^{b} sum_k c_k n^k = sum_k c_k (S_k(b) - S_k(a-1)).
    const BigInt bb = b;
    const BigInt aa = BigInt(a) - 1;
    CppRat total = 0;
    for (std::size_t k = 0; k < coeffs.size(); ++k) {
        if (coeffs[k] == 0)
            continue;
        total += coeffs[k] * (S_k(static_cast<int>(k), bb) - S_k(static_cast<int>(k), aa));
    }
    return total;
}

Value value_from_big_rational(const CppRat &r) {
    const BigInt num = boost::multiprecision::numerator(r);
    const BigInt den = boost::multiprecision::denominator(r);
    const BigInt kInt64Max = std::numeric_limits<std::int64_t>::max();
    const BigInt kInt64Min = std::numeric_limits<std::int64_t>::min();
    if (num >= kInt64Min && num <= kInt64Max && den >= kInt64Min && den <= kInt64Max)
        return Value{Rational(num.convert_to<std::int64_t>(), den.convert_to<std::int64_t>())};
    // No Rational->BigReal in this calc: overflow falls to double, matching brute.
    return Value{r.convert_to<double>()};
}

namespace {

// Polynomial ops over CppRat coefficient vectors, "low degree first": index i holds
// the coefficient of x^i, so [c0, c1, c2] is c0 + c1 x + c2 x^2. That convention is
// what makes poly_mul convolve at index ia+ib and trim drop from the back.
using Poly = std::vector<CppRat>;

// A degree > kMaxDegree can never reach faulhaber_sum (its Bernoulli table stops at 24).
constexpr std::size_t kMaxDegree = 24;

// Drop trailing (highest-degree) zero coefficients so the degree stays exact.
void trim(Poly &p) {
    while (p.size() > 1 && p.back() == 0)
        p.pop_back();
}
// r = a + sign*b, coefficient by coefficient (same index = same degree).
Poly poly_add(const Poly &a, const Poly &b, int sign) {
    Poly r(std::max(a.size(), b.size()), CppRat(0)); // room for the higher degree
    for (std::size_t idx = 0; idx < a.size(); ++idx) // copy a in
        r[idx] += a[idx];
    for (std::size_t idx = 0; idx < b.size(); ++idx) // add (sign +1) or subtract (sign -1) b
        r[idx] += sign * b[idx];
    trim(r);
    return r;
}
// r = a * b. Multiplying two polynomials distributes every term of a over every term of b;
// since x^ia * x^ib = x^(ia+ib), grouping the products by degree IS a convolution of the
// coefficient vectors, so a[ia]*b[ib] accumulates at r[ia+ib]. That is why powers use it too.
//
// See: https://en.wikipedia.org/wiki/Cauchy_product
Poly poly_mul(const Poly &a, const Poly &b) {
    Poly r(a.size() + b.size() - 1, CppRat(0));       // degree(a*b) = degree a + degree b
    for (std::size_t ia = 0; ia < a.size(); ++ia)     // every term of a
        for (std::size_t ib = 0; ib < b.size(); ++ib) // times every term of b
            r[ia + ib] += a[ia] * b[ib];              // accumulate at degree ia+ib
    trim(r);
    return r;
}

// A Number/Const/session-var value as an exact Rational, or nullopt (double / irrational).
std::optional<CppRat> const_coeff(const Value &v) {
    const std::optional<Rational> r = to_rational(v);
    if (!r)
        return std::nullopt;
    return CppRat(r->numerator(), r->denominator());
}

// Extract the body's polynomial in `var` as a coefficient vector, or nullopt when the
// body is not a polynomial (a Call, division by the variable, etc.). Walks the RPN with
// a stack of coefficient vectors; the bound variable is symbolic as [0,1].
//
// Example:
// n^2 - 3n -> [0, -3, 1] (0 + -3 n + 1 n^2);
// sin(n) -> nullopt.
// This "interpret the body over polynomials instead of numbers" is abstract interpretation.
// See: https://en.wikipedia.org/wiki/Abstract_interpretation
std::optional<Poly> canon_walk(std::span<const Token> rpn, std::string_view var);

// A Pow's exponent side: exactly one non-negative integer literal.
std::optional<CppRat> literal_int_exponent(const std::vector<Token> &right) {
    if (right.size() != 1 || right[0].kind != TokenKind::Number)
        return std::nullopt;
    const std::optional<Rational> r =
        to_rational(literal_value(std::get<parser::NumberToken>(right[0].data).value));
    if (!r || r->denominator() != 1 || r->numerator() < 0)
        return std::nullopt;
    return CppRat(r->numerator());
}

std::optional<Poly> canon_walk(std::span<const Token> rpn, std::string_view var) {
    std::vector<Poly> stack;
    for (const Token &tok : rpn) {
        switch (tok.kind) {
        // A numeric literal is a constant polynomial [c] (or nullopt if not an exact Rational).
        case TokenKind::Number: {
            const auto c =
                const_coeff(literal_value(std::get<parser::NumberToken>(tok.data).value));
            if (!c)
                return std::nullopt;
            stack.push_back({*c});
            break;
        }
        // The bound variable is the polynomial n = [0,1]; any other letter is a session
        // constant (constant w.r.t. the loop), so it is a constant polynomial [c].
        case TokenKind::Char: {
            const char ch = std::get<parser::CharToken>(tok.data).value;
            if (std::string_view(&ch, 1) == var) {
                stack.push_back({CppRat(0), CppRat(1)}); // the bound variable = [0,1]
            } else {                                     // a session variable, constant in the loop
                const Value *v = session_vars().get(std::string(1, ch));
                const auto c = v ? const_coeff(*v) : std::nullopt;
                if (!c)
                    return std::nullopt;
                stack.push_back({*c});
            }
            break;
        }
        // A named constant is a constant polynomial [c]; an irrational one (pi, e) is not a
        // Rational, so const_coeff returns nullopt and the whole body declines.
        case TokenKind::Const: {
            const auto c = const_coeff(
                const_value(*consts::const_spec(std::get<parser::ConstToken>(tok.data).id)));
            if (!c)
                return std::nullopt;
            stack.push_back({*c});
            break;
        }
        // A group: recurse into its single element and push the sub-body's polynomial.
        case TokenKind::Paren: {
            const auto &p = std::get<parser::ParenToken>(tok.data);
            if (!p.has_open || p.elements.size() != 1)
                return std::nullopt;
            const auto *elem = std::get_if<std::vector<Token>>(&p.elements[0]);
            const std::span<const Token> inner =
                elem ? std::span<const Token>(*elem)
                     : std::span<const Token>(&std::get<Token>(p.elements[0]), 1);
            auto sub = canon_walk(shunting_yard(inner), var);
            if (!sub)
                return std::nullopt;
            stack.push_back(std::move(*sub));
            break;
        }
        case TokenKind::Latex: {
            const auto &lx = std::get<parser::LatexToken>(tok.data);
            // base ^ (literal non-negative int): raise the base polynomial by repeated
            // convolution (n^2 = [0,1] convolved with itself). Cap the exponent/degree at
            // kMaxDegree.
            if (lx.kind == LatexKind::Pow) {
                auto base = canon_walk(shunting_yard(lx.left), var);
                const auto e = literal_int_exponent(lx.right);
                if (!base || !e)
                    return std::nullopt;
                const Poly &base_poly = *base;
                const std::int64_t ex = static_cast<std::int64_t>(*e);
                if (ex > static_cast<std::int64_t>(kMaxDegree))
                    return std::nullopt; // degree-0 base with huge exponent: brute force handles it
                Poly acc{CppRat(1)};
                for (std::int64_t p = 0; p < ex; ++p) {
                    acc = poly_mul(acc, base_poly);
                    if (acc.size() > kMaxDegree + 1)
                        return std::nullopt;
                }
                stack.push_back(std::move(acc));
                // numerator / var-free divisor: scalar-divide each coefficient. A divisor
                // containing the variable is a rational function, not a polynomial -> nullopt.
            } else if (lx.kind == LatexKind::Frac) {
                auto n = canon_walk(shunting_yard(lx.left), var);
                auto d = canon_walk(shunting_yard(lx.right), var);
                if (!n || !d || d->size() != 1)
                    return std::nullopt; // divisor must be var-free
                const CppRat &divisor = (*d)[0];
                if (divisor == 0)
                    calc_detail::math_error(); // var-free zero divisor: always errors
                Poly r = *n;
                for (auto &co : r)
                    co /= divisor;
                stack.push_back(std::move(r));
            } else {
                return std::nullopt; // Root / Log / Subscript / Sum / Prod
            }
            break;
        }
        // Operators pop their operand polynomials and combine them.
        case TokenKind::Op: {
            const OpId id = std::get<parser::OpToken>(tok.data).op_id;
            if (id == OpId::Negate) { // -a: negate every coefficient
                if (stack.empty())
                    return std::nullopt;
                for (auto &co : stack.back())
                    co = -co;
                break;
            }
            if (stack.size() < 2)
                return std::nullopt;
            Poly b = std::move(stack.back());
            stack.pop_back();
            Poly a = std::move(stack.back());
            stack.pop_back();
            if (id == OpId::Add)
                stack.push_back(poly_add(a, b, 1)); // a + b
            else if (id == OpId::Sub)
                stack.push_back(poly_add(a, b, -1)); // a - b
            else if (id == OpId::Mul)
                stack.push_back(poly_mul(a, b)); // a * b (convolution)
            else if (id == OpId::Div) {          // a / var-free b: scalar-divide
                if (b.size() != 1)
                    return std::nullopt; // divisor must be var-free
                if (b[0] == 0)
                    calc_detail::math_error(); // var-free zero divisor: always errors
                for (auto &co : a)
                    co /= b[0];
                stack.push_back(std::move(a));
            } else
                return std::nullopt; // any other op (^, !, ...) is not polynomial-closed here
            break;
        }
        default:
            return std::nullopt; // Call, etc.: not a polynomial
        }
        if (!stack.empty() && stack.back().size() > kMaxDegree + 1)
            return std::nullopt; // degree grew past the Bernoulli table
    }
    // A well-formed polynomial body leaves exactly one vector on the stack.
    if (stack.size() != 1)
        return std::nullopt;
    trim(stack.back());
    return stack.back();
}

} // namespace

std::optional<std::vector<CppRat>> canonicalise(std::span<const Token> rpn, std::string_view var) {
    return canon_walk(rpn, var);
}

std::optional<Value> try_closed_form(
    LatexKind kind,
    std::span<const Token> rpn,
    std::string_view var,
    std::int64_t first,
    std::int64_t last) {
    const auto coeffs = canonicalise(rpn, var);
    if (!coeffs)
        return std::nullopt;
    if (kind == LatexKind::Sum)
        return value_from_big_rational(faulhaber_sum(*coeffs, first, last));
    // Prod: only a var-free (degree 0) body has a worthwhile closed form: c^(last-first+1).
    if (coeffs->size() == 1) {
        // Same span iterate() uses, no +1 before the check: at first == INT64_MIN,
        // last == INT64_MAX, count would wrap to 0 and silently skip the cap. span itself
        // can't overflow (first <= last is guaranteed by the caller).
        const std::uint64_t span =
            static_cast<std::uint64_t>(last) - static_cast<std::uint64_t>(first);
        // c^count grows exponentially, and one big-int squaring is a single allocation the
        // wall-clock deadline cannot interrupt mid-flight, so this needs its own size bound.
        // Over it, the product is genuinely too large: throw rather than hand a runaway count
        // to the (now uncapped) brute loop. kind is provably Prod here (Sum returned above).
        if (span >= static_cast<std::uint64_t>(kMaxIterations))
            throw CalculatorError(errmsg::iterated_range_too_large("Product"), ErrorKind::Invalid);
        const std::uint64_t count = span + 1; // safe: span < kMaxIterations here
        // c^count by exponentiation by squaring: O(log count) multiplies, not count.
        //
        // See: https://cp-algorithms.com/algebra/binary-exp.html
        //      https://en.wikipedia.org/wiki/Exponentiation_by_squaring
        CppRat base = (*coeffs)[0];
        CppRat acc = 1;
        std::uint64_t q = count;
        while (q > 0) {
            check_deadline(); // a large base near the cap makes each squaring a big-int multiply
            if (q & 1)
                acc *= base;
            base *= base;
            q >>= 1;
        }
        return value_from_big_rational(acc);
    }
    return std::nullopt; // degree >= 1 product: brute force
}

} // namespace tcalc::eval
