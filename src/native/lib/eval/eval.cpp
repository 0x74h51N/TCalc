#include "eval/pub/eval.hpp"

#include <cmath>

#include "calc/pub/error_messages.hpp"

namespace tcalc::eval {

using ops::OpId;

namespace {

std::string_view op_name(OpId id) {
    const ops::OpSpec *spec = ops::op_spec(id);
    return spec != nullptr ? spec->method : std::string_view{"?"};
}

/// A value's real part as a double, for arms already known to be Int64 or Double.
double as_double(const Value &v) {
    if (const auto *i = std::get_if<std::int64_t>(&v))
        return to_double(*i);
    return std::get<double>(v);
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

/// The three exact signs that a double result lost its range: it overflowed to infinity,
/// it collapsed to zero although no operand was zero, or it landed in the subnormal band
/// below 1e-308, where a double keeps shedding significant digits unnoticed. IEEE-754
/// makes each of them an exact detector, so no magnitude estimate is needed.
bool escaped_double_range(double result, const std::vector<Value> &args) {
    if (std::isinf(result))
        return true;
    if (std::fpclassify(result) == FP_SUBNORMAL)
        return true;
    return result == 0.0 && !any_operand_zero(args);
}

/// Re-run the op in BigReal. Only reached once the result is known to have escaped the
/// double range and the op is known to have a BigReal arm.
Value redispatch_big(
    OpId id, const Calculator &c, const std::vector<Value> &args, Calculator::AngleUnit unit) {
    std::vector<Value> big_args;
    big_args.reserve(args.size());
    for (const auto &a : args)
        big_args.push_back(lift_to_big(a));
    return ops::kernel_of(id)(id, c, big_args, unit);
}

/// Range promotion: one rule, above every kernel, so it cannot differ between ops. A
/// no-op unless a double result escaped its range and the op has a BigReal arm to widen
/// into (an integer-only op like permute must never be re-run in a type it rejects).
Value promote_range(
    OpId id,
    const Calculator &c,
    const std::vector<Value> &args,
    Value result,
    Calculator::AngleUnit unit) {
    const auto *d = std::get_if<double>(&result);
    if (d == nullptr || !escaped_double_range(*d, args))
        return result;
    if (!has_arm(ops::arms_of(id), Arm::Big))
        return result;
    return redispatch_big(id, c, args, unit);
}

} // namespace

void promote_complex(OpId id, std::vector<Value> &args) {
    if (args.empty())
        return;
    const Arm a0 = arm_of(args[0]);
    if (a0 != Arm::Int64 && a0 != Arm::Double)
        return;
    for (const auto &a : args)
        if (arm_of(a) == Arm::Big)
            return;

    // The rule lives in the op's own row, beside its kernel and its arms. Most ops have
    // no domain boundary, and for them this is a null read.
    const ops::DomainRule rule = ops::domain_of(id);
    if (rule == nullptr)
        return;

    const double x = as_double(args[0]);

    // Only Root reads a second operand, its degree. It must be a plain real for the rule
    // to mean anything, and it is never promoted itself.
    double y = 0.0;
    if (args.size() > 1) {
        const Arm a1 = arm_of(args[1]);
        if (a1 != Arm::Int64 && a1 != Arm::Double)
            return;
        y = as_double(args[1]);
    }

    if (!rule(x, y))
        return;
    args[0] = Value{Complex(x, 0.0)};
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

    if (has_big) {
        // Never demote a BigReal either: it exists to hold what a double cannot.
        if (!has_arm(arms, Arm::Big))
            throw_math(errmsg::unsupported_operand(op_name(id)));
        for (auto &a : args)
            a = lift_to_big(a);
        return args;
    }

    // Only the real arms remain here.
    if (has_arm(arms, Arm::Rat)) {
        std::vector<Value> lifted;
        lifted.reserve(args.size());
        bool all_lift = true;
        for (const auto &a : args) {
            const auto r = to_rational(a);
            if (!r) {
                all_lift = false;
                break;
            }
            lifted.push_back(Value{*r});
        }
        if (all_lift)
            return lifted;
    }

    if (has_arm(arms, Arm::Double)) {
        for (auto &a : args)
            a = rational_downcast(a);

        // Dispatch reads one arm and expects every argument to share it, so a mixed
        // pair like (2, 3.5) has to be widened here. A lone argument is already
        // homogeneous and must not be forced to double.
        if (args.size() > 1) {
            const Arm a0 = arm_of(args[0]);
            bool all_same = true;
            for (const auto &a : args)
                if (arm_of(a) != a0)
                    all_same = false;
            if (!all_same)
                for (auto &a : args)
                    a = Value{as_double(a)};
        }
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
    promote_complex(id, args);
    std::vector<Value> dispatch_args = coerce(id, args);

    Value result;
    try {
        result = ops::kernel_of(id)(id, c, dispatch_args, unit);
    } catch (const CalculatorError &) {
        // Exact arithmetic that cannot represent its own result throws: a rational root
        // that is irrational, a rational power that overflows. Retrying in double is how
        // the calculator reaches an answer anyway. The trigger is what the failing call
        // actually ran with, not what the caller passed: coerce lifts plain integers into
        // Rational, so it is the lifted arguments that need unwinding.
        if (!has_arm(arms_present(dispatch_args), Arm::Rat))
            throw;
        for (auto &a : dispatch_args)
            a = rational_downcast(a);
        // Pow has both a (double, double) and a (double, long long) overload, so two
        // integral fractions downcasting to a bare integer pair would make the retry
        // ambiguous. Take it all the way to double instead.
        if (dispatch_args.size() > 1)
            for (auto &a : dispatch_args)
                a = Value{as_double(a)};
        result = ops::kernel_of(id)(id, c, dispatch_args, unit); // a second throw propagates
    }

    return promote_range(id, c, dispatch_args, result, unit);
}

} // namespace tcalc::eval
