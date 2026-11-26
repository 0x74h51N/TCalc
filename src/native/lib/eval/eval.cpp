/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "eval/pub/eval.hpp"

#include <bit>
#include <cmath>
#include <iterator>
#include <memory>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

#include "calc/pub/error_messages.hpp"
#include "eval/internal/closed_forms.hpp"
#include "eval/internal/deadline.hpp"
#include "eval/internal/exact.hpp"
#include "eval/pub/literal.hpp"
#include "eval/pub/varstore.hpp"
#include "parser/pub/consts.hpp"

namespace tcalc::eval {

using ops::OpId;
using parser::LatexKind;
using parser::Token;
using parser::TokenKind;

namespace {

/// The op's method name, which is what the error messages call it. An op with no kernel
/// has no method either, so it falls back to the symbol the user typed.
std::string_view op_name(OpId id) {
    const ops::OpSpec *spec = ops::op_spec(id);
    if (spec == nullptr)
        return "?";
    return spec->method.empty() ? spec->symbol : spec->method;
}

/// A real arm as a double. Only the three real arms reach this; a BigReal is never read
/// through a double, since one that is out of double's range would come back as 0 or inf
/// and answer a range or domain question with a lie.
double as_double(const Value &v) {
    if (const auto *i = std::get_if<std::int64_t>(&v))
        return to_double(*i);
    if (const auto *r = std::get_if<Rational>(&v))
        return to_double(*r);
    return std::get<double>(v);
}

/// Whether v is a real operand below zero; a complex or a collection is neither.
bool negative_real(const Value &v) {
    if (const auto *b = std::get_if<BigReal>(&v))
        return *b < 0;
    const Arm a = arm_of(v);
    return (a == Arm::Int64 || a == Arm::Rat || a == Arm::Double) && as_double(v) < 0.0;
}

// Each lift names its to_X overload set directly inside the `requires`. Forwarding
// through a generic lambda instead would move the failing call out of the immediate
// context, so the check turns into a hard error rather than yielding false.

/// Widen to Complex, leaving an arm with no complex form untouched.
Value lift_to_complex(const Value &v) {
    return std::visit(
        [](const auto &x) -> Value {
            if constexpr (requires { tcalc::to_complex(x); })
                return Value{tcalc::to_complex(x)};
            else
                return Value{x};
        },
        v);
}

/// Widen to BigComplex, leaving an arm with no such form untouched.
Value lift_to_big_complex(const Value &v) {
    return std::visit(
        [](const auto &x) -> Value {
            if constexpr (requires { tcalc::to_big_complex(x); })
                return Value{tcalc::to_big_complex(x)};
            else
                return Value{x};
        },
        v);
}

/// Widen to BigReal. The guard is what keeps a Collection, the one arm with no BigReal
/// form, from ever reaching the conversion.
Value lift_to_big(const Value &v) {
    if (!is_num_or_big(v))
        return v;
    return std::visit(
        [](const auto &x) -> Value {
            if constexpr (requires { tcalc::to_big(x); })
                return Value{tcalc::to_big(x)};
            else
                return Value{x};
        },
        v);
}

/// An operand an op cannot take is a math error. Invalid and Malformed are reserved for
/// the parser.
[[noreturn]] void throw_math(const std::string &message) {
    throw CalculatorError(message, ErrorKind::MathErr);
}

/// The arms present in args, in one pass, so the lattice reads bits instead of
/// rescanning the arguments at every rung.
ArmMask arms_present(const std::vector<Value> &args) {
    ArmMask m = 0;
    for (const auto &v : args)
        m |= arm_bit(arm_of(v));
    return m;
}

/// True when an operand is exactly zero. Only Int64 and Double can reach a kernel that
/// returns a plain double.
bool any_operand_zero(const std::vector<Value> &args) {
    for (const auto &a : args) {
        if (const auto *i = std::get_if<std::int64_t>(&a)) {
            if (*i == 0)
                return true;
        } else if (const auto *d = std::get_if<double>(&a)) {
            if (*d == 0.0)
                return true;
        }
    }
    return false;
}

/// Overflow to infinity, or the subnormal band where a double sheds digits unnoticed.
bool outside_double_range(double x) {
    return std::isinf(x) || std::fpclassify(x) == FP_SUBNORMAL;
}

/// The three exact signs that a double result lost its range: it overflowed to infinity,
/// it collapsed to zero although no operand was zero, or it landed in the subnormal band.
/// IEEE-754 makes each of them an exact detector, so no magnitude estimate is needed.
bool escaped_double_range(double result, const std::vector<Value> &args, bool exact_zero) {
    if (outside_double_range(result))
        return true;
    // fmod and a difference of two doubles are exact, so a zero out of them is the answer,
    // not a magnitude that fell out of range. Overflow and the subnormal band still apply.
    if (exact_zero)
        return false;
    return result == 0.0 && !any_operand_zero(args);
}

/// True when every Complex operand is finite: an inf from sinh(1000+i) came in, it did not escape.
bool complex_operands_finite(const std::vector<Value> &args) {
    for (const auto &a : args)
        if (const auto *z = std::get_if<Complex>(&a))
            if (!std::isfinite(z->real()) || !std::isfinite(z->imag()))
                return false;
    return true;
}

/// Per part, but only a whole zero counts: a zero part is often the answer (i·i).
bool escaped_double_range(const Complex &result, const std::vector<Value> &args, bool exact_zero) {
    if (outside_double_range(result.real()) || outside_double_range(result.imag()))
        return complex_operands_finite(args);
    if (exact_zero)
        return false;
    return result == 0.0 && !any_operand_zero(args);
}

/// Re-run the op on its operands widened by `lift`.
Value redispatch_big(
    OpId id,
    const Calculator &c,
    const std::vector<Value> &args,
    Calculator::AngleUnit unit,
    Value (*lift)(const Value &)) {
    std::vector<Value> big_args;
    big_args.reserve(args.size());
    for (const auto &a : args)
        big_args.push_back(lift(a));
    return ops::kernel_of(id)(id, c, big_args, unit);
}

/// An op with no `wide_arm` keeps its result: permute must never be re-run in a type it rejects.
template <class Wide, class Narrow>
Value widen_escaped(
    OpId id,
    const Calculator &c,
    const std::vector<Value> &args,
    Value result,
    const Narrow &narrow,
    Arm wide_arm,
    Value (*lift)(const Value &),
    Calculator::AngleUnit unit) {
    if (!escaped_double_range(narrow, args, ops::has_trait(id, ops::Trait::ExactZero)))
        return result;
    if (!has_arm(ops::arms_of(id), wide_arm))
        return result;
    // A zero the widened run confirms was never an underflow, so the narrow result stands
    // rather than leaking a wide type into everything after it.
    Value widened = redispatch_big(id, c, args, unit, lift);
    const auto *w = std::get_if<Wide>(&widened);
    if (w != nullptr && *w == 0)
        return result;
    return widened;
}

/// Range promotion: one rule, above every kernel, so it cannot differ between ops. A
/// double result widens into BigReal, a Complex one into BigComplex.
Value promote_range(
    OpId id,
    const Calculator &c,
    const std::vector<Value> &args,
    Value result,
    Calculator::AngleUnit unit) {
    if (const auto *d = std::get_if<double>(&result))
        return widen_escaped<BigReal>(id, c, args, result, *d, Arm::Big, lift_to_big, unit);
    if (const auto *z = std::get_if<Complex>(&result))
        return widen_escaped<BigComplex>(
            id, c, args, result, *z, Arm::BigCx, lift_to_big_complex, unit);
    return result;
}

} // namespace

bool promote_complex(OpId id, std::vector<Value> &args) {
    if (args.empty())
        return false;

    // The rule lives in the op's own row, beside its kernel and its arms. Most ops have
    // no domain boundary, and for them this is a null read.
    const ops::DomainRule rule = ops::domain_of(id);
    if (rule.on_double == nullptr)
        return false;

    const Arm a0 = arm_of(args[0]);
    // coerce lifts every operand once one is a BigReal, so a BigReal radicand has a BigReal
    // degree, read as itself: as a double 1e-400 would be 0 and 1e400 inf.
    if (a0 == Arm::Big) {
        const BigReal y = args.size() > 1 ? std::get<BigReal>(args[1]) : BigReal(0);
        if (!rule.on_big(std::get<BigReal>(args[0]), y))
            return false;
        args[0] = lift_to_big_complex(args[0]);
        return true;
    }
    if (a0 != Arm::Int64 && a0 != Arm::Double)
        return false;

    const double x = as_double(args[0]);

    // Root and Pow read a second operand, the degree or the exponent. It must be a plain real for
    // the rule to mean anything, and it is never promoted itself.
    double y = 0.0;
    if (args.size() > 1) {
        const Arm a1 = arm_of(args[1]);
        if (a1 != Arm::Int64 && a1 != Arm::Double)
            return false;
        y = as_double(args[1]);
    }

    if (!rule.on_double(x, y))
        return false;
    args[0] = Value{Complex(x, 0.0)};
    return true;
}

namespace {

/// Int64 and Rational are exactly the arms an exact lift accepts.
bool exact_lift_accepts(ArmMask present) {
    return (present & ~(arm_bit(Arm::Int64) | arm_bit(Arm::Rat))) == 0;
}

} // namespace

bool promote_big(OpId id, std::vector<Value> &args) {
    const ops::RangeRule rule = ops::range_of(id);
    if (rule == nullptr || args.size() < ops::kBinaryOperands)
        return false;
    // A BigReal operand is already there, and a complex one has a magnitude the rule
    // cannot read off a single real.
    const ArmMask present = arms_present(args);
    if ((present & ~(arm_bit(Arm::Int64) | arm_bit(Arm::Double) | arm_bit(Arm::Rat))) != 0)
        return false;
    if (ops::has_trait(id, ops::Trait::DoubleKernelRange) && exact_lift_accepts(present))
        return false;

    if (!rule(as_double(args[0]), as_double(args[1])))
        return false;
    for (auto &a : args)
        a = lift_to_big(a);
    return true;
}

std::vector<Value> coerce(OpId id, std::vector<Value> args) {
    const ArmMask arms = ops::arms_of(id);
    const ArmMask present = arms_present(args);

    // Collections are settled first: none of the numeric lifts has a Collection overload,
    // so one must never reach them.
    if (has_arm(present, Arm::Coll)) {
        if (!has_arm(arms, Arm::Coll))
            throw_math(errmsg::unsupported_operand(op_name(id)));
        return args;
    }

    const bool has_big = has_arm(present, Arm::Big);
    const bool has_complex = has_arm(present, Arm::Cx);

    // BigComplex > Complex > BigReal > Rational. A BigReal paired with a Complex joins
    // upward to BigComplex rather than narrowing into a double-precision complex.
    if (has_arm(present, Arm::BigCx) || (has_big && has_complex)) {
        if (!has_arm(arms, Arm::BigCx))
            throw_math(errmsg::unsupported_operand(op_name(id)));
        for (auto &a : args)
            a = lift_to_big_complex(a);
        return args;
    }

    // A complex operand meeting an op with no complex arm is an error, never a narrowing:
    // the imaginary part would simply be discarded.
    if (has_complex) {
        if (!has_arm(arms, Arm::Cx))
            throw_math(errmsg::unsupported_operand(op_name(id)));
        for (auto &a : args)
            a = lift_to_complex(a);
        return args;
    }

    if (has_big && has_arm(arms, Arm::Big)) {
        for (auto &a : args)
            a = lift_to_big(a);
        return args;
    }
    // Never demote a BigReal a double cannot hold: it exists for that. One a double holds,
    // such as an exact result past int64, goes on below as the double it was before it widened.
    // Past double's range the conversion is inf; below DBL_MIN boost gives 0, never a subnormal.
    if (has_big)
        for (auto &a : args)
            if (const auto *b = std::get_if<BigReal>(&a)) {
                const double d = to_double(*b);
                if (std::isinf(d) || (d == 0.0 && *b != 0))
                    throw_math(errmsg::unsupported_operand(op_name(id)));
                a = Value{d};
            }

    // Only the real arms remain here.
    // TODO: Fix Calculator (int, int) returning Rational(n, 1) instead of int.
    if (has_arm(arms, Arm::Rat)) {
        // The mask settles this all-or-nothing arm up front: one double among the operands
        // leaves args untouched for the double arm below. Past the check only the integers
        // convert, and like every other arm this one lifts in place.
        if (exact_lift_accepts(present)) {
            for (auto &a : args)
                if (const auto *i = std::get_if<std::int64_t>(&a))
                    a = Value{Rational(*i)};
            return args;
        }
    }

    if (has_arm(arms, Arm::Double)) {
        for (auto &a : args)
            a = rational_downcast(a);

        // Dispatch reads one arm and expects every argument to share it, and that arm has
        // to be one the op actually has. Two things break the rule and both widen here: a
        // mixed pair like (2, 3.5), and an integer reaching an op with no integer arm,
        // which is how exp gets a double rather than an arm it cannot dispatch on.
        const ArmMask now = arms_present(args);
        const bool homogeneous = std::popcount(now) == 1;
        const bool dispatchable = (now & ~arms) == 0;
        if (!homogeneous || !dispatchable)
            for (auto &a : args)
                a = Value{as_double(a)};
        return args;
    }

    if (has_arm(arms, Arm::Int64)) {
        bool all_int = true;
        for (const auto &a : args)
            if (arm_of(a) != Arm::Int64)
                all_int = false;
        if (all_int)
            return args;
        // Choose and Permute take integers only; a non-integer is reported as such
        // rather than being truncated.
        throw_math(errmsg::integers_only(op_name(id)));
    }

    throw_math(errmsg::unsupported_operand(op_name(id)));
}

Value apply(const Calculator &c, OpId id, std::vector<Value> args, Calculator::AngleUnit unit) {
    // An OpId the syntax table knows but the kernel table has no row for (`==`). The RPN
    // walk hands over whatever op a token stream names, so this is reachable input, not a
    // lattice bug: it takes no operands at all.
    if (ops::kernel_of(id) == nullptr)
        throw_math(errmsg::unsupported_operand(op_name(id)));

    // An op that names a stand-in for its second operand gets it here, the one place every
    // caller converges. Zero means none is named, and those ops always arrive with both.
    if (args.size() == 1 && ops::second_default_of(id) != 0)
        args.push_back(Value{static_cast<std::int64_t>(ops::second_default_of(id))});

    // TODO(#230): real first. A negative base under p/q with an odd q has the real value
    // root(x^p, q), the exact arm's own definition, and it is taken here because lifting
    // the exponent loses q. An even q has no real value and is promoted to its principal
    // complex power below; a complex number set skips this and promotes every q. A root's
    // fractional degree loses its numerator the same way, so it becomes that power first.
    if (args.size() > 1 && negative_real(args[0]))
        if (const auto *e = std::get_if<Rational>(&args[1]);
            e != nullptr && !calc_detail::whole(*e)) {
            // A degree whose reciprocal is past int64 takes the ordinary path instead, where
            // the kernel's math error reaches the retry; a throw here would skip it.
            if (ops::has_trait(id, ops::Trait::InverseDegree))
                if (const auto inv =
                        calc_detail::narrow(calc_detail::WideRational(1) / calc_detail::widen(*e)))
                    return apply(c, OpId::Pow, {args[0], Value{*inv}}, unit);
            if (ops::has_trait(id, ops::Trait::RootExponent) &&
                calc_detail::odd_integer(e->denominator())) {
                const Value power = apply(c, id, {args[0], Value{e->numerator()}}, unit);
                return apply(c, OpId::Root, {power, Value{e->denominator()}}, unit);
            }
        }

    // A power whose result cannot fit a double is widened before it runs, not after: the
    // rounding is not reversible once the kernel has returned.
    promote_big(id, args);

    // The domain rule reads a real operand, so it runs on the arguments as they will be
    // dispatched, not as they arrived: coerce is what downcasts a Rational for an op with
    // no exact arm, and that downcast is the moment the rule can first see the value. An
    // op that does have an exact arm keeps its Rational here and gets first refusal on it,
    // which is what leaves `\root{-8}{3}` an exact -2 instead of a complex root.
    std::vector<Value> dispatch_args = coerce(id, std::move(args));
    if (promote_complex(id, dispatch_args))
        dispatch_args = coerce(id, dispatch_args);

    Value result;
    try {
        result = ops::kernel_of(id)(id, c, dispatch_args, unit);
    } catch (const CalculatorError &) {
        // Exact arithmetic that cannot represent its own result throws: a rational root
        // that is irrational, a rational result past int64. The retry is how the calculator
        // reaches an answer anyway. The trigger is what the failing call actually ran with,
        // not what the caller passed: coerce lifts plain integers into Rational, so it is the
        // lifted arguments that need unwinding.
        if (!has_arm(arms_present(dispatch_args), Arm::Rat))
            throw;
        // The op's row names the arm: BigReal holds a rational answer that overflowed int64.
        // coerce made every operand Rational, as the rule reads them.
        if (const ops::RetryArmRule retry = ops::retry_arm_of(id);
            retry != nullptr && retry(dispatch_args) == Arm::Big) {
            for (auto &a : dispatch_args)
                a = lift_to_big(a);
        } else {
            // A cast would round the exponent p/q before the power is taken; the row computes
            // it from the exact operands instead.
            if (const ops::ExactRetry exact = ops::exact_retry_of(id); exact != nullptr)
                if (const auto value = exact(c, dispatch_args))
                    return promote_range(id, c, dispatch_args, *value, unit);
            // An integer is no arm of an op with a Rational arm, and Pow's (double, long long)
            // overload would make an integer pair ambiguous.
            for (auto &a : dispatch_args)
                a = Value{as_double(a)};
        }
        // The domain rule reads a real operand, so a Rational never met it. The lift has
        // produced one: sqrt of a negative rational leaves the real domain here, and the
        // promotion has to run before the retry rather than after it. coerce only follows
        // when the promotion fired, since it would otherwise lift the operands straight back
        // into the exact arm the retry just left.
        if (promote_complex(id, dispatch_args))
            dispatch_args = coerce(id, dispatch_args);
        result = ops::kernel_of(id)(id, c, dispatch_args, unit); // a second throw propagates
    }

    return promote_range(id, c, dispatch_args, result, unit);
}

/// A constant's value, which is a double for all but the imaginary unit.
Value const_value(consts::ConstId id) {
    return std::visit(
        [](const auto &x) -> Value { return Value{x}; }, consts::const_spec(id)->value);
}

namespace {

[[noreturn]] void throw_invalid(const std::string &message) {
    throw CalculatorError(message, ErrorKind::Invalid);
}

[[noreturn]] void throw_malformed(std::string_view message) {
    throw CalculatorError(std::string(message), ErrorKind::Malformed);
}

Value pop_operand(std::vector<Value> &stack) {
    if (stack.empty())
        throw_malformed(errmsg::kPopOperand);
    Value v = std::move(stack.back());
    stack.pop_back();
    return v;
}

/// Gather operands into an argument vector by moving. A braced-init std::vector copies,
/// because an initializer_list hands out const references its elements cannot move from,
/// which for a Collection operand means copying every item.
template <class... Vs> std::vector<Value> args_of(Vs &&...vs) {
    std::vector<Value> out;
    out.reserve(sizeof...(vs));
    (out.push_back(std::forward<Vs>(vs)), ...);
    return out;
}

/// The name a subscript denotes: the text without its braces, so the token `x_{0}` and
/// the constant table's symbol `σ_{SB}` give the keys `x_0` and `σ_SB`.
std::string strip_braces(std::string_view text) {
    std::string name;
    name.reserve(text.size());
    for (const char ch : text)
        if (ch != '{' && ch != '}')
            name.push_back(ch);
    return name;
}

/// The subscripted constant a name denotes, or nullptr when it names none.
const consts::ConstSpec *subscript_const(std::string_view name) {
    for (const auto &spec : consts::kConstants)
        if (strip_braces(spec.symbol) == name)
            return &spec;
    return nullptr;
}

/// A name resolves against the store; an unset one is an error, never a zero.
Value resolve_name(const std::string &name) {
    const Value *v = session_vars().get(name);
    if (v == nullptr)
        throw_invalid(errmsg::undefined_variable(name));
    return *v;
}

/// A subscripted name is a constant first, a variable second.
Value eval_subscript(const Token &tok) {
    const std::string name = strip_braces(parser::token_text(tok));
    if (const consts::ConstSpec *spec = subscript_const(name))
        return const_value(spec->id);
    return resolve_name(name);
}

/// The two sides of a Frac / Pow / Root token, each a row of its own. An absent side is
/// zero, except a Root's degree, where it means the square root.
std::vector<Value>
latex_operands(const parser::LatexToken &latex, const Calculator &c, Calculator::AngleUnit unit) {
    Value left = latex.left.empty() ? Value{Rational(0)} : eval_row(latex.left, c, unit);
    Value right = Value{Rational(latex.kind == LatexKind::Root ? kSquare : 0)};
    if (!latex.right.empty())
        right = eval_row(latex.right, c, unit);
    return args_of(std::move(left), std::move(right));
}

/// A latex rule, when the op has one, runs on both rows before either is evaluated:
/// evaluating the base is exactly what would destroy an identity like e^{ln u}.
Value eval_latex(const parser::LatexToken &latex, const Calculator &c, Calculator::AngleUnit unit) {
    if (const exact::LatexRule rule = exact::latex_rule(latex.op_id))
        if (auto v = rule(latex.left, latex.right, c, unit))
            return *v;
    return apply(c, latex.op_id, latex_operands(latex, c, unit), unit);
}

/// A value as a collection item. Rational has no item arm, so an exact fraction leaves
/// the exact domain here: integral to an integer, fractional to a double. A nested
/// collection is shared rather than copied.
CollectionItem collection_item(const Value &v) {
    return std::visit(
        [](const auto &x) -> CollectionItem {
            using T = std::decay_t<decltype(x)>;
            if constexpr (std::is_same_v<T, Rational>) {
                if (x.denominator() == 1)
                    return CollectionItem{x.numerator()};
                return CollectionItem{x.to_double()};
            } else if constexpr (std::is_same_v<T, Collection>) {
                return CollectionItem{std::make_shared<const Collection>(x)};
            } else {
                return CollectionItem{x};
            }
        },
        v);
}

/// Build a collection, reporting the constructor's own validation (point arity, uniform
/// point arity in a list) as an input error.
Value make_collection(CollectionKind kind, std::vector<CollectionItem> items) {
    try {
        return Value{Collection(kind, std::move(items))};
    } catch (const std::invalid_argument &e) {
        throw_invalid(e.what());
    }
}

/// One element of a paren group or one call argument: a single token stands on its own,
/// a token run is a row.
Value eval_element(
    const parser::ParenElement &element, const Calculator &c, Calculator::AngleUnit unit) {
    if (const auto *tok = std::get_if<Token>(&element))
        return eval_rpn(
            std::span<const Token>(tok, 1), c, unit); /// Element has one token, pass shunting_yard

    const auto &row = std::get<std::vector<Token>>(element); /// Element has many tokens
    if (row.empty())
        throw_invalid(std::string(errmsg::kEmptyElement));
    return eval_row(row, c, unit);
}

/// The two classes a collection may hold. A list is uniform in one of them.
enum class ItemClass : std::uint8_t { None, Scalar, Point };

/// Turn the comma-split groups into a value. A Bracket makes them a List, a Paren a Point.
/// Branches on the group count: one is grouping, zero is empty, more is a collection.
Value eval_elements(
    std::span<const parser::ParenElement> elements,
    parser::ParenKind kind,
    const Calculator &c,
    Calculator::AngleUnit unit) {
    // One group, no comma: grouping, `(x)` is `x`, which is why mean([1,2,3]) reads like
    // mean[1,2,3]. A bracket wraps only a collection: `[5]` is 5, `[[1,2]]` is rejected.
    if (elements.size() == 1) {
        Value v = eval_element(elements[0], c, unit);
        const auto *inner = std::get_if<Collection>(&v);
        if (inner == nullptr || kind != parser::ParenKind::Bracket)
            return v;
        if (inner->kind == CollectionKind::List)
            throw_invalid(std::string(errmsg::kListOfList));
        return make_collection(CollectionKind::List, {collection_item(v)});
    }

    if (kind == parser::ParenKind::Brace)
        throw_invalid(std::string(errmsg::kBraceUnsupported));

    // No group: an empty pair. `()` has no coordinate, `[]` is the empty List.
    if (elements.empty()) {
        if (kind == parser::ParenKind::Paren)
            throw_invalid(std::string(errmsg::kEmptyPoint));
        return make_collection(CollectionKind::List, {});
    }

    // More than one group: a collection, one item per group.
    const bool is_point = kind == parser::ParenKind::Paren;
    std::vector<CollectionItem> items;
    items.reserve(elements.size());
    ItemClass expected = ItemClass::None;

    for (const auto &element : elements) {
        const Value v = eval_element(element, c, unit);
        const auto *coll = std::get_if<Collection>(&v);
        const ItemClass got = coll != nullptr ? ItemClass::Point : ItemClass::Scalar;

        if (coll != nullptr) {
            if (is_point)
                throw_invalid(std::string(errmsg::kPointItemCollection));
            if (coll->kind == CollectionKind::List)
                throw_invalid(std::string(errmsg::kListOfList));
        }
        if (expected == ItemClass::None)
            expected = got;
        else if (expected != got)
            throw_invalid(std::string(errmsg::kListMix));

        items.push_back(collection_item(v));
    }

    return make_collection(
        is_point ? CollectionKind::Point : CollectionKind::List, std::move(items));
}

/// A variadic call's arguments as one List dataset: a lone collection is the dataset
/// itself, a lone scalar wraps, and N arguments follow the bracket rule.
Value call_dataset(
    std::span<const parser::ParenElement> args, const Calculator &c, Calculator::AngleUnit unit) {
    if (args.size() != 1)
        return eval_elements(args, parser::ParenKind::Bracket, c, unit);

    Value v = eval_element(args[0], c, unit);
    if (std::holds_alternative<Collection>(v))
        return v;
    return make_collection(CollectionKind::List, {collection_item(v)});
}

/// The values a call hands its op: one dataset for a variadic op, else exactly the arguments
/// its spec names, and no collection among them.
std::vector<Value>
call_operands(const parser::CallToken &call, const Calculator &c, Calculator::AngleUnit unit) {
    const ops::OpSpec &spec = *ops::op_spec(call.op_id);
    if (ops::is_variadic(spec))
        return args_of(call_dataset(call.args, c, unit));
    if (call.args.size() != spec.call_arity)
        throw_invalid(errmsg::takes_arguments(spec.symbol, spec.call_arity));

    std::vector<Value> args;
    args.reserve(call.args.size());
    for (const auto &arg : call.args) {
        Value v = eval_element(arg, c, unit);
        if (std::holds_alternative<Collection>(v))
            throw_invalid(errmsg::not_for_list_or_point(spec.symbol));
        args.push_back(std::move(v));
    }

    return args;
}

/// A call token. A single-argument trig call tries its exact form first: radians from the
/// argument's own tokens, before it is evaluated at all; degrees and grads from the evaluated
/// value, after. gcd and lcm read a power or a factorial argument from its tokens, and evaluate
/// their arguments themselves when they do.
Value eval_call(const parser::CallToken &call, const Calculator &c, Calculator::AngleUnit unit) {
    // Only a one-argument op carries a token rule (exact.cpp asserts it), so a call of any
    // other size goes straight to its operands and their arity check.
    if (call.args.size() == 1)
        if (const exact::TokenRule rule = exact::token_rule(call.op_id))
            if (auto v = rule(call.op_id, parser::element_tokens(call.args.front()), c, unit))
                return *v;

    if (const exact::CallRule rule = exact::call_rule(call.op_id))
        if (auto v = rule(call.op_id, call.args, c, unit))
            return *v;

    std::vector<Value> args = call_operands(call, c, unit);
    if (args.size() == 1)
        if (const exact::ValueRule rule = exact::value_rule(call.op_id))
            if (auto v = rule(call.op_id, args[0], c, unit))
                return *v;

    return apply(c, call.op_id, std::move(args), unit);
}

/// The operands an op token takes off the stack, once the op may be applied at all.
std::vector<Value> op_operands(OpId id, std::vector<Value> &stack) {
    if (id == OpId::Assign)
        throw_invalid(std::string(errmsg::kInvalidAssignment));

    const ops::OpSpec &spec = *ops::op_spec(id);
    // A fixed-arity call function has no infix form. Typed bare it arrives here with too
    // few operands, so it is reported rather than left to underflow. A variadic one does
    // apply to a following collection (`min[1,2,3]`) and is not rejected.
    if (!ops::is_variadic(spec) && spec.call_arity != 1)
        throw_invalid(errmsg::needs_call_form(spec.symbol));

    if (spec.arity != ops::Arity::Binary)
        return args_of(pop_operand(stack));
    Value right = pop_operand(stack);
    Value left = pop_operand(stack);
    return args_of(std::move(left), std::move(right));
}

/// An op token: take its operands off the stack and hand them to apply. A unary op in degrees
/// or grads tries the exact trig path on its operand's value first; radians are already handled
/// by eval_rpn's lookahead before this ever runs.
Value eval_op(OpId id, std::vector<Value> &stack, const Calculator &c, Calculator::AngleUnit unit) {
    std::vector<Value> args = op_operands(id, stack);
    if (args.size() == 1)
        if (const exact::ValueRule rule = exact::value_rule(id))
            if (auto v = rule(id, args[0], c, unit))
                return *v;
    return apply(c, id, std::move(args), unit);
}

/// A token that completes an operand: a following +/- is binary, and an implicit
/// multiplication may be inserted after it. Shared by the implicit-mult rule and the
/// iterated-body terminator.
bool ends_operand(const Token &t) {
    if (t.kind == TokenKind::Latex) {
        // An iterated op takes the term after it, and so does a logarithm carrying its base,
        // so neither closes an operand no implicit multiplication may follow.
        if (parser::is_iterated(std::get<parser::LatexToken>(t.data).kind))
            return false;
        const auto scripted = parser::scripted_op(t);
        return !scripted || scripted->id != OpId::Log;
    }
    if (t.kind == TokenKind::Number || t.kind == TokenKind::Char || t.kind == TokenKind::Const)
        return true;
    if (t.kind == TokenKind::Paren)
        return std::get<parser::ParenToken>(t.data).has_close;
    if (t.kind == TokenKind::Call)
        return std::get<parser::CallToken>(t.data).has_close;
    if (t.kind == TokenKind::Op)
        return ops::op_spec(std::get<parser::OpToken>(t.data).op_id)->arity == ops::Arity::Postfix;
    return false;
}

/// Add's precedence: an iterated body keeps everything that binds tighter than this.
inline constexpr ops::Precedence kIteratedBodyPrecedence = ops::op_spec(OpId::Add)->precedence;

/// True when tok ends the iterated body collected so far. An operator in operand position
/// is a sign, not a terminator, so the body of `\sum_{n=1}^{3} +n` keeps its `+`.
bool closes_iterated_body(const Token &tok, std::span<const Token> body) {
    if (tok.kind != TokenKind::Op || body.empty() || !ends_operand(body.back()))
        return false;
    return ops::op_spec(std::get<parser::OpToken>(tok.data).op_id)->precedence <=
           kIteratedBodyPrecedence;
}

bool opens_iterated_body(const Token &t) {
    return t.kind == TokenKind::Latex &&
           parser::is_iterated(std::get<parser::LatexToken>(t.data).kind);
}

/// Finish the innermost open body: the tokens from its start index to the end of the row
/// collapse into one operand, in place. A single token is already a complete operand (a
/// user paren, a Pow, a bare Char, anything) and stays where it is. An empty body becomes
/// a paren with no elements, the "no body" marker; the eval arm reads that directly, no
/// reaching inside a paren required. Eval-only: render reads the original branch, so this
/// never reaches the UI.
void close_body(std::vector<Token> &out, std::vector<std::size_t> &body_starts) {
    const std::size_t start = body_starts.back();
    body_starts.pop_back();
    if (out.size() - start == 1)
        return;
    const auto first = out.begin() + static_cast<std::ptrdiff_t>(start);
    parser::ParenToken group;
    group.kind = parser::ParenKind::Paren;
    if (out.size() > start)
        group.elements.emplace_back(
            std::vector<Token>(std::make_move_iterator(first), std::make_move_iterator(out.end())));
    out.erase(first, out.end());
    out.push_back(Token{.kind = TokenKind::Paren, .data = parser::TokenData{std::move(group)}});
}

/// Display name for an iterated op's error messages.
std::string_view iterated_op_name(LatexKind kind) {
    return kind == LatexKind::Sum ? "Sum" : "Product";
}

/// Split an iterated lower limit `[Char(var), Op(Assign), <start tokens>]`.
std::pair<std::string, std::span<const Token>>
peel_lower(const std::vector<Token> &left, std::string_view op_name) {
    if (left.size() < 3 || left[0].kind != TokenKind::Char || left[1].kind != TokenKind::Op ||
        std::get<parser::OpToken>(left[1].data).op_id != OpId::Assign)
        throw_invalid(errmsg::iterated_bad_lower(op_name));
    return {
        std::string(1, std::get<parser::CharToken>(left[0].data).value),
        std::span<const Token>(left).subspan(2)};
}

/// A bound must be a whole number: 2.5 is an error, not a truncation.
std::int64_t require_integer(const Value &v, std::string_view op_name) {
    const std::optional<Rational> r = to_rational(v);
    if (!r || r->denominator() != 1)
        throw_invalid(errmsg::iterated_non_integer_bound(op_name));
    return r->numerator();
}

// On in production; a benchmark turns it off to force the brute-force path. Read once per
// iterate() call (before the loop). Function-local static so it is not a mutable namespace
// global; visible to the public setters below since they share this translation unit.
bool &closed_forms_flag() {
    static bool on = true;
    return on;
}

// Test-only hit flag for the closed-form matcher below, thread_local so parallel test runs
// don't cross-pollute each other's results.
bool &closed_form_taken_flag() {
    thread_local bool taken = false;
    return taken;
}

// Check the deadline once every this many brute iterations, so the clock read is amortized away.
constexpr std::int64_t kDeadlineCheckStride = 1024;

/// Run an iterated op's brute-force loop. Both limits are evaluated before the bound
/// variable is bound, so a limit can never see it.
Value iterate(
    const parser::LatexToken &tok,
    std::span<const Token> body,
    const Calculator &c,
    Calculator::AngleUnit unit) {
    const std::string_view op_name = iterated_op_name(tok.kind);
    if (tok.right.empty())
        throw_invalid(errmsg::iterated_missing_upper(op_name));

    const auto [var, start_tokens] = peel_lower(tok.left, op_name);
    const std::int64_t first = require_integer(eval_row(start_tokens, c, unit), op_name);
    const std::int64_t last = require_integer(eval_row(tok.right, c, unit), op_name);

    const bool is_sum = tok.kind == LatexKind::Sum;
    Value acc{Rational(is_sum ? 0 : 1)};
    if (first > last)
        return acc; // empty range yields the identity

    // body is always one token (a user paren, a single char, whatever normalize left in
    // place); shunting_yard runs its own normalize + shunt over it. Hoisted out of the loop,
    // and shared by the closed-form matcher below.
    const std::vector<Token> rpn = shunting_yard(body);
    // The closed-form matcher is checked once here, before the loop (not per iteration).
    // A benchmark can force the brute path by turning it off; production leaves it on.
    if (closed_forms_enabled())
        if (auto closed = try_closed_form(tok.kind, rpn, var, first, last, c, unit)) {
            closed_form_taken_flag() = true;
            return *closed; // O(1) for a polynomial sum, exempt from any range limit
        }

    // The loop variable is a transient local bind: remember the caller's binding and put
    // it back on every exit, so a sum never leaks its index.
    const Value *prior = session_vars().get(var);
    const std::optional<Value> saved =
        prior != nullptr ? std::optional<Value>(*prior) : std::nullopt;
    const auto restore = [&] {
        if (saved)
            session_vars().set(var, *saved);
        else
            session_vars().unset(var);
    };

    try {
        const OpId op = is_sum ? OpId::Add : OpId::Mul;
        std::int64_t steps = 0;
        for (std::int64_t m = first; m <= last; ++m) {
            if ((++steps & (kDeadlineCheckStride - 1)) == 0)
                check_deadline(); // early-exit a runaway loop; amortized ~free
            session_vars().set(var, Value{Rational(m)});
            acc = apply(c, op, args_of(std::move(acc), eval_rpn(rpn, c, unit)), unit);
        }
    } catch (...) {
        restore();
        throw;
    }
    restore();
    return acc;
}

} // namespace

void set_closed_forms_enabled(bool on) {
    closed_forms_flag() = on;
}
bool closed_forms_enabled() {
    return closed_forms_flag();
}

void reset_closed_form_taken() {
    closed_form_taken_flag() = false;
}
bool closed_form_taken() {
    return closed_form_taken_flag();
}

namespace {

/// A logarithm's operands: its value, then its base when the script names one.
std::vector<Value> log_operands(
    std::span<const Token> base,
    std::span<const Token> value,
    const Calculator &c,
    Calculator::AngleUnit unit) {
    std::vector<Value> args = args_of(eval_row(value, c, unit));
    if (!base.empty())
        args.push_back(eval_row(base, c, unit));
    return args;
}

/// Walk an RPN list and leave its operand stack, which a whole row reduces to one value.
std::vector<Value>
walk_rpn(std::span<const Token> rpn, const Calculator &c, Calculator::AngleUnit unit) {
    std::vector<Value> stack;
    stack.reserve(rpn.size());

    for (std::size_t i = 0; i < rpn.size(); ++i) {
        const Token &tok = rpn[i];

        // The bare infix form (`sin π`) binds exactly one operand, the entry right before it.
        // The token phase reads tokens only, so it can run on tok itself, before tok is
        // evaluated: a hit needs no value and no stack pop to undo.
        if (i + 1 < rpn.size() && rpn[i + 1].kind == TokenKind::Op) {
            const OpId next_id = std::get<parser::OpToken>(rpn[i + 1].data).op_id;
            if (const exact::TokenRule rule = exact::token_rule(next_id))
                if (auto v = rule(next_id, rpn.subspan(i, 1), c, unit)) {
                    stack.push_back(*v);
                    ++i; // consume the trig op too
                    continue;
                }
        }

        switch (tok.kind) {
        case TokenKind::Number:
            stack.push_back(literal_value(std::get<parser::NumberToken>(tok.data).value));
            break;
        case TokenKind::Char:
            stack.push_back(
                resolve_name(std::string(1, std::get<parser::CharToken>(tok.data).value)));
            break;
        case TokenKind::Const:
            stack.push_back(const_value(std::get<parser::ConstToken>(tok.data).id));
            break;
        case TokenKind::Latex: {
            const auto &latex = std::get<parser::LatexToken>(tok.data);
            if (parser::is_iterated(latex.kind)) {
                // normalize guarantees the body token is next; consume it too. An empty
                // paren is the "no body" marker close_body leaves when nothing follows.
                ++i;
                const bool no_body =
                    i >= rpn.size() || (rpn[i].kind == TokenKind::Paren &&
                                        std::get<parser::ParenToken>(rpn[i].data).elements.empty());
                if (no_body)
                    throw_invalid(errmsg::iterated_missing_body(iterated_op_name(latex.kind)));
                stack.push_back(iterate(latex, rpn.subspan(i, 1), c, unit));
                break;
            }
            if (latex.kind == LatexKind::Subscript) {
                const auto scripted = parser::scripted_op(tok);
                if (!scripted || scripted->id != OpId::Log) {
                    stack.push_back(eval_subscript(tok)); // a name and its index
                    break;
                }
                // A logarithm's script is its base and its value is the next token, which the
                // shunt leaves right here because this token is an operand to it.
                const std::vector<Token> &base = *scripted->script;
                ++i;
                if (i >= rpn.size())
                    throw_invalid(errmsg::log_missing_value());
                // log_b(b^k) = k has to run before either row is evaluated: the value token
                // right here is exactly what a matching rule reads off, and evaluating it
                // first is what would turn a power into a float and lose the answer.
                if (const exact::LatexRule rule = exact::latex_rule(OpId::Log))
                    if (auto v = rule(base, rpn.subspan(i, 1), c, unit)) {
                        stack.push_back(*v);
                        break;
                    }
                stack.push_back(
                    apply(c, OpId::Log, log_operands(base, rpn.subspan(i, 1), c, unit), unit));
                break;
            }
            stack.push_back(eval_latex(latex, c, unit));
            break;
        }
        case TokenKind::Paren: {
            const auto &paren = std::get<parser::ParenToken>(tok.data);
            // A stray close has no content to contribute. An unclosed open still does:
            // the row is evaluated as the user types it.
            if (!paren.has_open)
                break;
            stack.push_back(eval_elements(paren.elements, paren.kind, c, unit));
            break;
        }
        case TokenKind::Call:
            stack.push_back(eval_call(std::get<parser::CallToken>(tok.data), c, unit));
            break;
        case TokenKind::Op:
            stack.push_back(eval_op(std::get<parser::OpToken>(tok.data).op_id, stack, c, unit));
            break;
        }
    }

    return stack;
}

} // namespace

Value eval_rpn(std::span<const Token> rpn, const Calculator &c, Calculator::AngleUnit unit) {
    std::vector<Value> stack = walk_rpn(rpn, c, unit);
    if (stack.empty())
        throw_malformed(errmsg::kOperandStackEmpty);
    return std::move(stack.front());
}

/// Insert implicit multiplication and collapse runs of + and - into one sign, before the
/// shunt. Also groups each iterated op's body into a synthetic paren so the shunt's flat
/// RPN cannot lose the boundary between the body and what follows it. Reads the row
/// without owning it and builds the normalized copy fresh.
std::vector<Token> normalize(std::span<const Token> raw) {
    std::vector<Token> out;
    out.reserve(raw.size());
    // Where each open iterated body starts in `out`. Stays empty, and never allocates, for
    // a row with no iterated op, which is every row that does not contain a sum.
    std::vector<std::size_t> body_starts;

    const auto is_plus_minus = [](const Token &t) -> bool {
        if (t.kind != TokenKind::Op)
            return false;
        const auto &op_token = std::get<parser::OpToken>(t.data);
        return op_token.op_id == OpId::Add || op_token.op_id == OpId::Sub;
    };

    const auto starts_operand = [](const Token &t) -> bool {
        if (t.kind == TokenKind::Number || t.kind == TokenKind::Latex ||
            t.kind == TokenKind::Char || t.kind == TokenKind::Const) {
            return true;
        }
        if (t.kind == TokenKind::Paren)
            return std::get<parser::ParenToken>(t.data).has_open;
        if (t.kind == TokenKind::Call)
            return true;
        if (t.kind == TokenKind::Op)
            return ops::op_spec(std::get<parser::OpToken>(t.data).op_id)->arity ==
                   ops::Arity::Unary;
        return false;
    };

    for (const Token &tok : raw) {
        // A binary operator no tighter than Add closes every body it separates.
        while (!body_starts.empty() &&
               closes_iterated_body(tok, std::span<const Token>(out).subspan(body_starts.back())))
            close_body(out, body_starts);

        // Everything below reads the innermost body only, so it starts where that body does.
        const std::size_t body_start = body_starts.empty() ? 0 : body_starts.back();
        if (out.size() > body_start) {
            const Token &last = out.back();

            if (is_plus_minus(tok) && is_plus_minus(last)) {
                auto &last_op = std::get<parser::OpToken>(out.back().data);
                const auto &curr_op = std::get<parser::OpToken>(tok.data);

                if (last_op.op_id == OpId::Sub) {
                    if (curr_op.op_id == OpId::Sub)
                        last_op.op_id = OpId::Add;
                    continue;
                }
                last_op = curr_op; // + followed by +/- keeps the later sign
                continue;
            }

            if (ends_operand(last) && starts_operand(tok))
                out.push_back(
                    Token{
                        .kind = TokenKind::Op,
                        .data = parser::TokenData{parser::OpToken{OpId::Mul}}});
        }
        out.push_back(tok);

        if (opens_iterated_body(tok))
            body_starts.push_back(out.size()); // this sum's body starts after it
    }

    while (!body_starts.empty())
        close_body(out, body_starts);
    return out;
}

std::vector<Token> shunt_normalized(std::vector<Token> normalized) {
    std::vector<Token> output;
    output.reserve(normalized.size());
    std::vector<Token> operator_stack;

    for (Token &tok : normalized) {
        // Everything that is not an operator is an operand, and an operand goes straight
        // to the output.
        if (tok.kind != TokenKind::Op) {
            output.push_back(std::move(tok));
            continue;
        }

        const ops::OpSpec *op = ops::op_spec(std::get<parser::OpToken>(tok.data).op_id);

        while (!operator_stack.empty() && operator_stack.back().kind == TokenKind::Op) {
            const parser::OpToken &top_tok = std::get<parser::OpToken>(operator_stack.back().data);
            const ops::OpSpec *top = ops::op_spec(top_tok.op_id);

            if (op->id == OpId::Negate && top->arity == ops::Arity::Unary &&
                top->id != OpId::Negate) {
                break;
            }

            const bool pop_left =
                (op->associativity == ops::Assoc::Left) && (op->precedence <= top->precedence);
            const bool pop_right =
                (op->associativity == ops::Assoc::Right) && (op->precedence < top->precedence);
            if (!(pop_left || pop_right))
                break;

            output.push_back(operator_stack.back());
            operator_stack.pop_back();
        }

        operator_stack.push_back(tok);
    }

    while (!operator_stack.empty()) {
        output.push_back(operator_stack.back());
        operator_stack.pop_back();
    }

    return output;
}

std::vector<Token> shunting_yard(std::span<const Token> tokens) {
    return shunt_normalized(normalize(tokens));
}

Value eval_row(std::span<const Token> tokens, const Calculator &c, Calculator::AngleUnit unit) {
    // Arms the wall-clock guard at the outermost row and reuses it for every nested row (a
    // paren, a latex side, a call arg), so the whole evaluation shares one deadline.
    const DeadlineScope deadline;
    return eval_rpn(shunting_yard(tokens), c, unit);
}

namespace {

/// True for the `=` that heads an assignment.
bool is_assign(const Token &tok) {
    return tok.kind == TokenKind::Op && std::get<parser::OpToken>(tok.data).op_id == OpId::Assign;
}

/// An `=` in second position makes the row an assignment.
bool is_assignment(std::span<const Token> tokens) {
    return tokens.size() >= 2 && is_assign(tokens[1]);
}

/// The tokens a row's value comes from: an assignment's right side, else the whole row.
std::span<const Token> value_tokens(std::span<const Token> tokens) {
    return is_assignment(tokens) ? tokens.subspan(2) : tokens;
}

/// The name an assignment binds. Two token kinds may be bound: a letter, and a subscript
/// over a letter. An operator or a constant is named in the error rather than lumped in
/// with the rest, because the user has to be told which letter is already taken.
std::string assign_target(const Token &tok) {
    switch (tok.kind) {
    case TokenKind::Char:
        return std::string(1, std::get<parser::CharToken>(tok.data).value);
    case TokenKind::Op:
        throw_invalid(
            errmsg::assignment_target_is_operator(
                ops::op_spec(std::get<parser::OpToken>(tok.data).op_id)->symbol));
    case TokenKind::Const:
        throw_invalid(
            errmsg::assignment_target_is_constant(
                consts::const_spec(std::get<parser::ConstToken>(tok.data).id)->symbol));
    case TokenKind::Latex: {
        const auto &latex = std::get<parser::LatexToken>(tok.data);
        if (latex.kind != LatexKind::Subscript)
            break;
        std::string name = strip_braces(parser::token_text(tok));
        // A subscripted constant is a constant, and it is reported as one: its base is not
        // a letter either, so the check has to come first to reach the right message.
        if (subscript_const(name) != nullptr)
            throw_invalid(errmsg::assignment_target_is_constant(name));
        if (latex.left.size() != 1 || latex.left[0].kind != TokenKind::Char)
            throw_invalid(std::string(errmsg::kInvalidAssignmentTarget));
        return name;
    }
    default:
        break;
    }
    throw_invalid(std::string(errmsg::kInvalidAssignmentTarget));
}

} // namespace

Value evaluate(
    const parser::TokensBranch &branch, const Calculator &c, Calculator::AngleUnit unit) {
    const std::span<const Token> tokens(branch.tokens); // eval_row arms the wall-clock guard
    if (!is_assignment(tokens))
        return eval_row(tokens, c, unit);

    const std::string name = assign_target(tokens[0]);
    const std::span<const Token> rhs = tokens.subspan(2);
    if (rhs.empty())
        throw_invalid(std::string(errmsg::kEmptyAssignment));

    Value value = eval_row(rhs, c, unit);
    session_vars().set(name, value);
    return value;
}

std::optional<std::pair<OpId, std::vector<Value>>>
root_operands(const parser::TokensBranch &branch, const Calculator &c, Calculator::AngleUnit unit) {
    const DeadlineScope deadline;
    const std::vector<Token> rpn = shunting_yard(value_tokens(branch.tokens));
    if (rpn.empty())
        return std::nullopt;
    // A logarithm carrying its base is its subscript and its value, and a well-formed row
    // holds nothing else: any other token would be joined to them by an op that is the root.
    if (rpn.size() == 2)
        if (const auto scripted = parser::scripted_op(rpn[0]);
            scripted && scripted->id == OpId::Log)
            return std::pair{
                OpId::Log, log_operands(*scripted->script, std::span(rpn).subspan(1), c, unit)};
    const Token &root = rpn.back();
    switch (root.kind) {
    case TokenKind::Op: {
        const OpId id = std::get<parser::OpToken>(root.data).op_id;
        std::vector<Value> stack = walk_rpn(std::span(rpn).first(rpn.size() - 1), c, unit);
        return std::pair{id, op_operands(id, stack)};
    }
    case TokenKind::Call: {
        const auto &call = std::get<parser::CallToken>(root.data);
        return std::pair{call.op_id, call_operands(call, c, unit)};
    }
    case TokenKind::Latex: {
        const auto &latex = std::get<parser::LatexToken>(root.data);
        // a subscript, a sum and a product are evaluated whole, with no op of their own
        if (latex.kind == LatexKind::Subscript || parser::is_iterated(latex.kind))
            break;
        return std::pair{latex.op_id, latex_operands(latex, c, unit)};
    }
    case TokenKind::Number:
    case TokenKind::Char:
    case TokenKind::Const:
    case TokenKind::Paren:
        break;
    }
    return std::nullopt;
}

} // namespace tcalc::eval
