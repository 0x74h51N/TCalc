/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "eval/internal/closed_forms.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <utility>
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
// The loop below IS that sum: k+1 terms (one per degree up to k), NOT m iterations (the range).
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

// Exact polynomial long division: the quotient a / b, but only when b divides a with no
// remainder (n^2 / n = n). A nonzero remainder means a / b is a rational function, not a
// polynomial, so it returns nullopt. b is trimmed and nonzero (degree >= 1 at the call site).
// See: https://en.wikipedia.org/wiki/Polynomial_long_division
std::optional<Poly> poly_div_exact(Poly a, const Poly &b) {
    trim(a);
    const std::size_t db = b.size() - 1; // divisor degree
    if (a.size() <= db)                  // deg(a) < deg(b): exact only if a is the zero polynomial
        return (a.size() == 1 && a[0] == 0) ? std::optional<Poly>(Poly{CppRat(0)}) : std::nullopt;
    Poly q(a.size() - db, CppRat(0));
    for (std::size_t k = q.size(); k-- > 0;) {
        const CppRat coeff = a[k + db] / b[db]; // cancel the current leading term of a
        q[k] = coeff;
        for (std::size_t j = 0; j <= db; ++j) // subtract coeff * x^k * b
            a[k + j] -= coeff * b[j];
    }
    trim(a); // what remains below degree db is the remainder
    if (a.size() != 1 || a[0] != 0)
        return std::nullopt; // nonzero remainder: not a polynomial
    return q;
}

// A Number/Const/session-var value as an exact Rational, or nullopt (double / irrational).
std::optional<CppRat> const_coeff(const Value &v) {
    const std::optional<Rational> r = to_rational(v);
    if (!r)
        return std::nullopt;
    return CppRat(r->numerator(), r->denominator());
}

// A Number, named constant, or non-loop Char as an exact Rational, or nullopt (the loop
// variable, a non-rational value, or any other token). Shared by both body walks.
std::optional<CppRat> token_constant(const Token &tok, std::string_view var) {
    switch (tok.kind) {
    case TokenKind::Number:
        return const_coeff(literal_value(std::get<parser::NumberToken>(tok.data).value));
    case TokenKind::Const:
        return const_coeff(
            const_value(*consts::const_spec(std::get<parser::ConstToken>(tok.data).id)));
    case TokenKind::Char: {
        const char ch = std::get<parser::CharToken>(tok.data).value;
        if (std::string_view(&ch, 1) == var)
            return std::nullopt; // the loop variable is not a constant
        const Value *v = session_vars().get(std::string(1, ch));
        return v ? const_coeff(*v) : std::nullopt;
    }
    default:
        return std::nullopt;
    }
}

// The single inner token span of a group, or nullopt if it is not a one-element open paren.
std::optional<std::span<const Token>> paren_element(const parser::ParenToken &p) {
    if (!p.has_open || p.elements.size() != 1)
        return std::nullopt;
    const auto *elem = std::get_if<std::vector<Token>>(&p.elements[0]);
    return elem ? std::span<const Token>(*elem)
                : std::span<const Token>(&std::get<Token>(p.elements[0]), 1);
}

// The single argument span of a one-argument call (its tokens), like paren_element for a group.
std::span<const Token> call_arg_span(const parser::ParenElement &e) {
    if (const auto *v = std::get_if<std::vector<Token>>(&e))
        return std::span<const Token>(*v);
    return std::span<const Token>(&std::get<Token>(e), 1);
}

// A real-arm Value as a double, reusing value.hpp's to_double overloads; nullopt for the
// complex or collection arms.
std::optional<double> real_value(const Value &v) {
    return std::visit(
        [](const auto &x) -> std::optional<double> {
            if constexpr (requires { to_double(x); })
                return to_double(x);
            else
                return std::nullopt;
        },
        v);
}

// Reject a nonlinear argument by comparing successive samples: loose for float noise, tight
// enough to catch a quadratic term.
constexpr double kLinearArgTol = 1e-9;

// The trig argument's frequency k and phase phi as reals, by sampling k*var + phi at var = 0,1,2
// with the calc's own evaluator (which resolves pi and every constant). nullopt if the argument
// is not linear in var or not real, so the trig term then declines to brute. Reuses eval, no
// second token walk.
std::optional<std::pair<double, double>> trig_arg_phi(
    const std::vector<Token> &arg,
    std::string_view var,
    const Calculator &calc,
    Calculator::AngleUnit unit) {
    const std::vector<Token> rpn = shunting_yard(std::span<const Token>(arg));
    const std::string key(var);
    const Value *prior = session_vars().get(key);
    const std::optional<Value> saved =
        prior != nullptr ? std::optional<Value>(*prior) : std::nullopt;
    std::array<double, 3> s{};
    bool ok = true;
    try {
        for (int m = 0; m < 3; ++m) {
            session_vars().set(key, Value{Rational(m)});
            const auto d = real_value(eval_rpn(rpn, calc, unit));
            if (!d) {
                ok = false;
                break;
            }
            s[static_cast<std::size_t>(m)] = *d;
        }
    } catch (...) {
        ok = false;
    }
    if (saved)
        session_vars().set(key, *saved);
    else
        session_vars().unset(key);
    if (!ok)
        return std::nullopt;
    const double k = s[1] - s[0];
    if (std::abs((s[2] - s[1]) - k) > kLinearArgTol)
        return std::nullopt; // not linear in var
    return std::make_pair(k, s[0]);
}

// One folded value while walking the body: a var-free constant, a polynomial in the loop
// variable, or a geometric term c*r^n. This is the union of what a polynomial-only and a
// geometric-only walk would each track, so the single walk below classifies a body in one pass.
// "Interpret the body over these values instead of over numbers" is abstract interpretation.
// See: https://en.wikipedia.org/wiki/Abstract_interpretation
//      https://en.wikipedia.org/wiki/Geometric_series
struct ClosedTerm {
    enum class Kind : std::uint8_t { Const, Poly, Geo, Trig };
    Kind kind;
    Poly poly;                   // Kind::Poly, low degree first
    CppRat c;                    // the constant (Const), or the multiplier (Geo, Trig)
    CppRat r;                    // the base (Geo)
    bool is_sin = false;         // Trig: sin vs cos
    std::vector<Token> trig_arg; // Trig: the argument tokens (k*var + phi), sampled at finalize
};

ClosedTerm ct_const(const CppRat &c) {
    return {ClosedTerm::Kind::Const, {}, c, CppRat(0)};
}

// A polynomial value, normalized: a degree-0 polynomial folds back to a Const.
ClosedTerm ct_from_poly(Poly p) {
    trim(p);
    if (p.size() == 1)
        return ct_const(p[0]);
    return {ClosedTerm::Kind::Poly, std::move(p), CppRat(0), CppRat(0)};
}

// c*r^n, normalized: r == 1 is the constant c, r == 0 is degenerate.
std::optional<ClosedTerm> ct_geo(const CppRat &c, const CppRat &r) {
    if (r == 0)
        return std::nullopt;
    if (r == 1)
        return ct_const(c);
    return ClosedTerm{ClosedTerm::Kind::Geo, {}, c, r};
}

// c*trig(<arg>), coefficient starts at 1 and is folded in by ct_mul/ct_negate.
ClosedTerm ct_trig(bool is_sin, std::span<const Token> arg) {
    return {
        ClosedTerm::Kind::Trig,
        {},
        CppRat(1),
        CppRat(0),
        is_sin,
        std::vector<Token>(arg.begin(), arg.end())};
}

// A Const or Poly as a coefficient vector; nullopt for Geo/Trig, which have no polynomial form.
std::optional<Poly> ct_poly_view(const ClosedTerm &t) {
    if (t.kind == ClosedTerm::Kind::Geo || t.kind == ClosedTerm::Kind::Trig)
        return std::nullopt;
    if (t.kind == ClosedTerm::Kind::Const)
        return Poly{t.c};
    return t.poly;
}

ClosedTerm ct_negate(ClosedTerm t) {
    if (t.kind == ClosedTerm::Kind::Poly)
        for (auto &co : t.poly)
            co = -co;
    else
        t.c = -t.c; // Const value, or Geo/Trig multiplier
    return t;
}

// A term's geometric base; a constant's implicit base is 1. So * and / combine bases uniformly.
CppRat ct_base(const ClosedTerm &t) {
    return t.kind == ClosedTerm::Kind::Geo ? t.r : CppRat(1);
}

// a + sign*b. A geometric term plus anything is not a single closed term.
std::optional<ClosedTerm> ct_add(const ClosedTerm &a, const ClosedTerm &b, int sign) {
    const auto pa = ct_poly_view(a);
    const auto pb = ct_poly_view(b);
    if (!pa || !pb)
        return std::nullopt;
    return ct_from_poly(poly_add(*pa, *pb, sign));
}

// a * b. A polynomial times a geometric term (n^2 * 2^n) has no single closed form.
std::optional<ClosedTerm> ct_mul(const ClosedTerm &a, const ClosedTerm &b) {
    if (a.kind == ClosedTerm::Kind::Trig || b.kind == ClosedTerm::Kind::Trig) {
        if (a.kind == ClosedTerm::Kind::Trig && b.kind == ClosedTerm::Kind::Const) {
            ClosedTerm t = a;
            t.c *= b.c;
            return t;
        }
        if (b.kind == ClosedTerm::Kind::Trig && a.kind == ClosedTerm::Kind::Const) {
            ClosedTerm t = b;
            t.c *= a.c;
            return t;
        }
        return std::nullopt; // trig*trig, trig*poly, trig*geo: no single closed term
    }
    if (a.kind == ClosedTerm::Kind::Geo || b.kind == ClosedTerm::Kind::Geo) {
        if (a.kind == ClosedTerm::Kind::Poly || b.kind == ClosedTerm::Kind::Poly)
            return std::nullopt;
        // (c_a r_a^n)(c_b r_b^n) = (c_a c_b)(r_a r_b)^n.
        return ct_geo(a.c * b.c, ct_base(a) * ct_base(b));
    }
    const auto pa = ct_poly_view(a);
    const auto pb = ct_poly_view(b);
    if (!pa || !pb)
        return std::nullopt; // unreachable here (neither is Geo), but keeps the access checked
    Poly r = poly_mul(*pa, *pb);
    if (r.size() > kMaxDegree + 1)
        return std::nullopt;
    return ct_from_poly(std::move(r));
}

// a / b. The divisor must be var-free (a Const, scaling) or geometric (Geo/Geo, Const/Geo).
std::optional<ClosedTerm> ct_div(const ClosedTerm &a, const ClosedTerm &b) {
    if (a.kind == ClosedTerm::Kind::Trig || b.kind == ClosedTerm::Kind::Trig) {
        if (a.kind == ClosedTerm::Kind::Trig && b.kind == ClosedTerm::Kind::Const) {
            if (b.c == 0)
                calc_detail::math_error();
            ClosedTerm t = a;
            t.c /= b.c;
            return t;
        }
        return std::nullopt;
    }
    if (b.kind == ClosedTerm::Kind::Poly) {
        // dividing by a polynomial in the loop variable: closed only if it divides evenly
        // (n^2 / n = n). A geometric numerator or a nonzero remainder is not a polynomial.
        const auto pa = ct_poly_view(a);
        if (!pa)
            return std::nullopt;
        auto q = poly_div_exact(*pa, b.poly);
        if (!q)
            return std::nullopt;
        return ct_from_poly(std::move(*q));
    }
    if (b.c == 0)
        calc_detail::math_error(); // var-free zero divisor always errors
    if (b.kind == ClosedTerm::Kind::Const && a.kind == ClosedTerm::Kind::Poly) {
        Poly r = a.poly; // polynomial / constant: scale each coefficient
        for (auto &co : r)
            co /= b.c;
        return ct_from_poly(std::move(r));
    }
    if (a.kind == ClosedTerm::Kind::Poly)
        return std::nullopt; // polynomial / geometric
    return ct_geo(a.c / b.c, ct_base(a) / ct_base(b));
}

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

// Walk the body RPN, classifying it as a single Const / Poly / Geo term, or nullopt when it is
// none of those (a Call, a variable divisor, a polynomial times a geometric term, etc.).
// Examples: n^2 - 3n -> Poly[0,-3,1]; 2^n -> Geo(1,2); 5 -> Const(5); sin(n) -> nullopt.
std::optional<ClosedTerm> classify_walk(std::span<const Token> rpn, std::string_view var) {
    std::vector<ClosedTerm> stack;
    for (const Token &tok : rpn) {
        switch (tok.kind) {
        // A numeric literal, named constant, or non-loop letter is a var-free constant (nullopt
        // if not an exact Rational, e.g. pi).
        case TokenKind::Number:
        case TokenKind::Const: {
            const auto c = token_constant(tok, var);
            if (!c)
                return std::nullopt;
            stack.push_back(ct_const(*c));
            break;
        }
        // The bound variable is the polynomial n = [0,1]; any other letter is a loop constant.
        case TokenKind::Char: {
            const char ch = std::get<parser::CharToken>(tok.data).value;
            if (std::string_view(&ch, 1) == var) {
                stack.push_back(ct_from_poly({CppRat(0), CppRat(1)}));
                break;
            }
            const auto c = token_constant(tok, var);
            if (!c)
                return std::nullopt;
            stack.push_back(ct_const(*c));
            break;
        }
        // A group: recurse into its single element and push the sub-body's term.
        case TokenKind::Paren: {
            const auto inner = paren_element(std::get<parser::ParenToken>(tok.data));
            if (!inner)
                return std::nullopt;
            auto sub = classify_walk(shunting_yard(*inner), var);
            if (!sub)
                return std::nullopt;
            stack.push_back(std::move(*sub));
            break;
        }
        case TokenKind::Latex: {
            const auto &lx = std::get<parser::LatexToken>(tok.data);
            if (lx.kind == LatexKind::Pow) {
                auto base_opt = classify_walk(shunting_yard(lx.left), var);
                if (!base_opt)
                    return std::nullopt;
                const ClosedTerm base = std::move(*base_opt); // bind once, past the null check
                if (const auto e = literal_int_exponent(lx.right)) {
                    // base ^ (literal non-negative int): a polynomial power by repeated
                    // convolution (n^2 = [0,1] convolved with itself), capped at kMaxDegree.
                    if (base.kind == ClosedTerm::Kind::Geo)
                        return std::nullopt;
                    const std::int64_t ex = static_cast<std::int64_t>(*e);
                    if (ex > static_cast<std::int64_t>(kMaxDegree))
                        return std::nullopt;
                    ClosedTerm acc = ct_const(CppRat(1));
                    for (std::int64_t p = 0; p < ex; ++p) {
                        auto m = ct_mul(acc, base);
                        if (!m)
                            return std::nullopt;
                        acc = std::move(*m);
                    }
                    stack.push_back(std::move(acc));
                } else {
                    // constant ^ (bound variable): the geometric term c*r^n. The exponent must
                    // be exactly the bare variable, the polynomial [0,1].
                    static const Poly kBareVar = {CppRat(0), CppRat(1)};
                    const auto exp = classify_walk(shunting_yard(lx.right), var);
                    if (base.kind != ClosedTerm::Kind::Const || !exp ||
                        exp->kind != ClosedTerm::Kind::Poly || exp->poly != kBareVar)
                        return std::nullopt;
                    auto g = ct_geo(CppRat(1), base.c);
                    if (!g)
                        return std::nullopt;
                    stack.push_back(std::move(*g));
                }
            } else if (lx.kind == LatexKind::Frac) {
                auto n = classify_walk(shunting_yard(lx.left), var);
                auto d = classify_walk(shunting_yard(lx.right), var);
                if (!n || !d)
                    return std::nullopt;
                auto q = ct_div(*n, *d);
                if (!q)
                    return std::nullopt;
                stack.push_back(std::move(*q));
            } else {
                return std::nullopt; // Root / Log / Subscript / Sum / Prod
            }
            break;
        }
        // Operators pop their operand terms and combine them.
        case TokenKind::Op: {
            const OpId id = std::get<parser::OpToken>(tok.data).op_id;
            if (id == OpId::Negate) {
                if (stack.empty())
                    return std::nullopt;
                stack.back() = ct_negate(std::move(stack.back()));
                break;
            }
            if (stack.size() < 2)
                return std::nullopt;
            ClosedTerm b = std::move(stack.back());
            stack.pop_back();
            ClosedTerm a = std::move(stack.back());
            stack.pop_back();
            std::optional<ClosedTerm> out;
            if (id == OpId::Add)
                out = ct_add(a, b, 1);
            else if (id == OpId::Sub)
                out = ct_add(a, b, -1);
            else if (id == OpId::Mul)
                out = ct_mul(a, b);
            else if (id == OpId::Div)
                out = ct_div(a, b);
            else
                return std::nullopt; // ^, !, ... : not closed here
            if (!out)
                return std::nullopt;
            stack.push_back(std::move(*out));
            break;
        }
        case TokenKind::Call: {
            const auto &call = std::get<parser::CallToken>(tok.data);
            const bool is_sin = call.op_id == OpId::Sin;
            if ((!is_sin && call.op_id != OpId::Cos) || call.args.size() != 1)
                return std::nullopt;
            // Store the raw argument tokens; trig_sum reads k and phi from them by sampling with
            // the real evaluator, so a pi-based argument works. Owned copy: a span would dangle.
            stack.push_back(ct_trig(is_sin, call_arg_span(call.args[0])));
            break;
        }
        default:
            return std::nullopt;
        }
    }
    if (stack.size() != 1)
        return std::nullopt;
    return std::move(stack.back());
}

// |x| as an unsigned, correct even at INT64_MIN (where -x would overflow).
std::uint64_t abs_u64(std::int64_t x) {
    return x < 0 ? -static_cast<std::uint64_t>(x) : static_cast<std::uint64_t>(x);
}

// Bits to write the larger of |numerator|, |denominator| of a nonzero rational.
int rat_bitlen(const CppRat &r) {
    const BigInt num = boost::multiprecision::abs(boost::multiprecision::numerator(r));
    const BigInt den = boost::multiprecision::denominator(r); // always > 0
    const int nb = num == 0 ? 1 : static_cast<int>(boost::multiprecision::msb(num)) + 1;
    const int db = static_cast<int>(boost::multiprecision::msb(den)) + 1; // msb(1) == 0
    return std::max(nb, db);
}

// r^e in exact rational by binary exponentiation. Only reached with a small |e| (gated by the
// caller), so the intermediate bignums stay tiny.
CppRat rat_pow(CppRat base, std::int64_t e) {
    if (e < 0)
        return CppRat(1) / rat_pow(base, -e);
    CppRat acc = 1;
    while (e > 0) {
        if (e & 1)
            acc *= base;
        base *= base;
        e >>= 1;
    }
    return acc;
}

// base^e in BigReal by binary exponentiation: O(log e) fixed-precision multiplies, matching the
// representation brute lands in once r^n overflows int64. A double would give inf for r > 1.
BigReal big_pow(BigReal base, std::int64_t e) {
    const bool neg = e < 0;
    std::uint64_t q = abs_u64(e);
    BigReal acc = 1;
    while (q > 0) {
        check_deadline(); // a large exponent makes each squaring a real fixed-precision multiply
        if (q & 1)
            acc *= base;
        base *= base;
        q >>= 1;
    }
    return neg ? BigReal(1) / acc : acc;
}

// Below this many bits the result plausibly fits int64, so the sum is computed exactly; past
// it the exact numerator is as big as brute's, so it switches to BigReal instead.
constexpr std::uint64_t kExactPowerBits = 62;

// sum_{n=a}^{b} c*r^n given the end powers r_a = r^a, r_b = r^b. Used by the real geometric sum
// (CppRat/BigReal). Using r*r_b (= r^(b+1)) avoids a b+1 overflow.
template <class T> T geometric_closed(const T &c, const T &r, const T &r_a, const T &r_b) {
    return c * (r * r_b - r_a) / (r - T(1));
}

// Sum_{n=a}^{b} c * r^n for a matched geometric term (r != 0, 1; a <= b guaranteed by the caller).
Value geometric_sum(const CppRat &c, const CppRat &r, std::int64_t a, std::int64_t b) {
    // Sum_{n=a}^{b} c r^n = c (r*r^b - r^a) / (r - 1). Using r*r^b (not r^(b+1)) sidesteps a
    // b + 1 overflow at INT64_MAX. Compute exact only while the largest power stays a small
    // bignum that plausibly fits int64; past that, a giant exact numerator would be as slow as
    // brute, so fall to BigReal (never double: r^b would be inf for r > 1) and match brute's
    // 50-digit overflow representation.
    const std::uint64_t max_exp = std::max(abs_u64(a), abs_u64(b));
    const bool exact = max_exp <= kExactPowerBits &&
                       max_exp * static_cast<std::uint64_t>(rat_bitlen(r)) <= kExactPowerBits;
    if (exact) {
        return value_from_big_rational(geometric_closed(c, r, rat_pow(r, a), rat_pow(r, b)));
    }
    const BigReal br = r.convert_to<BigReal>();
    return Value{geometric_closed(c.convert_to<BigReal>(), br, big_pow(br, a), big_pow(br, b))};
}

// k is treated as (near) a multiple of a full turn (body constant over integer n) when
// sin(k/2) lands within this of 0; then sum = count * c * trig(phi). Loose enough to catch
// k = 2*pi evaluated in floating point, tight enough not to swallow a genuine small frequency.
constexpr double kTrigDegenerateEps = 1e-9;

// sum_{n=a}^{b} c*trig(k*n + phi) via the real Dirichlet product form:
//   c * sin(k*count/2)/sin(k/2) * {sin,cos}(k*(a+b)/2 + phi),  count = b - a + 1.
// k and phi are sampled from the argument (so pi works); all angles go through the calc's own
// sin/cos so the angle unit and the exact values match brute. nullopt declines to brute.
// See: https://en.wikipedia.org/wiki/List_of_trigonometric_identities#Sums
std::optional<Value> trig_sum(
    const ClosedTerm &t,
    std::string_view var,
    std::int64_t a,
    std::int64_t b,
    const Calculator &calc,
    Calculator::AngleUnit unit) {
    const auto kphi = trig_arg_phi(t.trig_arg, var, calc, unit);
    if (!kphi)
        return std::nullopt;
    const double c = t.c.convert_to<double>();
    const double k = kphi->first;
    const double phi = kphi->second;
    // double subtraction, so b - a + 1 cannot overflow int64 at extreme bounds
    const double count = static_cast<double>(b) - static_cast<double>(a) + 1.0;
    const double half = calc.sin(k / 2.0, unit); // sin(k/2)
    if (std::abs(half) < kTrigDegenerateEps) {
        // k is (near) 0 / a full turn: the body is the constant trig(phi).
        const double body = t.is_sin ? calc.sin(phi, unit) : calc.cos(phi, unit);
        return Value{count * c * body};
    }
    const double factor = calc.sin(k * count / 2.0, unit) / half;
    const double mid = k * (static_cast<double>(a) + static_cast<double>(b)) / 2.0 + phi;
    const double outer = t.is_sin ? calc.sin(mid, unit) : calc.cos(mid, unit);
    return Value{c * factor * outer};
}

} // namespace

std::optional<std::vector<CppRat>> canonicalise(std::span<const Token> rpn, std::string_view var) {
    const auto t = classify_walk(rpn, var);
    if (!t || t->kind == ClosedTerm::Kind::Geo || t->kind == ClosedTerm::Kind::Trig)
        return std::nullopt;
    return t->kind == ClosedTerm::Kind::Const ? std::vector<CppRat>{t->c} : t->poly;
}

std::optional<Value> try_closed_form(
    LatexKind kind,
    std::span<const Token> rpn,
    std::string_view var,
    std::int64_t first,
    std::int64_t last,
    const Calculator &calc,
    Calculator::AngleUnit unit) {
    const auto term = classify_walk(rpn, var);
    if (kind == LatexKind::Sum) {
        // A single closed term: Faulhaber for a polynomial (constant included), the geometric
        // formula for c*r^n. Anything else declines, and the caller brute-forces.
        if (!term)
            return std::nullopt;
        if (term->kind == ClosedTerm::Kind::Geo)
            return geometric_sum(term->c, term->r, first, last);
        if (term->kind == ClosedTerm::Kind::Trig)
            return trig_sum(*term, var, first, last, calc, unit);
        const std::vector<CppRat> coeffs =
            term->kind == ClosedTerm::Kind::Const ? std::vector<CppRat>{term->c} : term->poly;
        return value_from_big_rational(faulhaber_sum(coeffs, first, last));
    }
    // Prod: only a var-free (constant) body has a worthwhile closed form: c^(last-first+1).
    if (!term || term->kind != ClosedTerm::Kind::Const)
        return std::nullopt;
    // Same span iterate() uses, no +1 before the check: at first == INT64_MIN, last == INT64_MAX,
    // count would wrap to 0 and silently skip the cap. span itself can't overflow (first <= last).
    const std::uint64_t span = static_cast<std::uint64_t>(last) - static_cast<std::uint64_t>(first);
    // c^count grows exponentially, and one big-int squaring is a single allocation the wall-clock
    // deadline cannot interrupt mid-flight, so this needs its own size bound. Over it the product
    // is genuinely too large: throw rather than hand a runaway count to the (now uncapped) brute
    // loop.
    if (span >= static_cast<std::uint64_t>(kMaxIterations))
        throw CalculatorError(errmsg::iterated_range_too_large("Product"), ErrorKind::Invalid);
    const std::uint64_t count = span + 1; // safe: span < kMaxIterations here
    // c^count by exponentiation by squaring: O(log count) multiplies, not count.
    //
    // See: https://cp-algorithms.com/algebra/binary-exp.html
    //      https://en.wikipedia.org/wiki/Exponentiation_by_squaring
    CppRat base = term->c;
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

} // namespace tcalc::eval
