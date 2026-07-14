#include "eval/pub/eval.hpp"

#include <bit>
#include <cmath>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

#include "calc/pub/error_messages.hpp"
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

bool promote_complex(OpId id, std::vector<Value> &args) {
    if (args.empty())
        return false;
    const Arm a0 = arm_of(args[0]);
    if (a0 != Arm::Int64 && a0 != Arm::Double)
        return false;
    for (const auto &a : args)
        if (arm_of(a) == Arm::Big)
            return false;

    // The rule lives in the op's own row, beside its kernel and its arms. Most ops have
    // no domain boundary, and for them this is a null read.
    const ops::DomainRule rule = ops::domain_of(id);
    if (rule == nullptr)
        return false;

    const double x = as_double(args[0]);

    // Only Root reads a second operand, its degree. It must be a plain real for the rule
    // to mean anything, and it is never promoted itself.
    double y = 0.0;
    if (args.size() > 1) {
        const Arm a1 = arm_of(args[1]);
        if (a1 != Arm::Int64 && a1 != Arm::Double)
            return false;
        y = as_double(args[1]);
    }

    if (!rule(x, y))
        return false;
    args[0] = Value{Complex(x, 0.0)};
    return true;
}

bool promote_big(OpId id, std::vector<Value> &args) {
    const ops::RangeRule rule = ops::range_of(id);
    if (rule == nullptr || args.size() < 2)
        return false;
    // A BigReal operand is already there, and a complex one has a magnitude the rule
    // cannot read off a single real.
    const ArmMask present = arms_present(args);
    if ((present & ~(arm_bit(Arm::Int64) | arm_bit(Arm::Double) | arm_bit(Arm::Rat))) != 0)
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

    if (has_big) {
        // Never demote a BigReal either: it exists to hold what a double cannot.
        if (!has_arm(arms, Arm::Big))
            throw_math(errmsg::unsupported_operand(op_name(id)));
        for (auto &a : args)
            a = lift_to_big(a);
        return args;
    }

    // Only the real arms remain here.
    // TODO: Fix Calculator (int, int) returning Rational(n, 1) instead of int.
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

    // A power whose result cannot fit a double is widened before it runs, not after: the
    // rounding is not reversible once the kernel has returned.
    promote_big(id, args);

    // The domain rule reads a real operand, so it runs on the arguments as they will be
    // dispatched, not as they arrived: coerce is what downcasts a Rational for an op with
    // no exact arm, and that downcast is the moment the rule can first see the value. An
    // op that does have an exact arm keeps its Rational here and gets first refusal on it,
    // which is what leaves `\root{-8}{3}` an exact -2 instead of a complex root.
    std::vector<Value> dispatch_args = coerce(id, args);
    if (promote_complex(id, dispatch_args))
        dispatch_args = coerce(id, dispatch_args);

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
        // The domain rule reads a real operand, so a Rational never met it. The downcast
        // has produced one: sqrt of a negative rational leaves the real domain here, and
        // the promotion has to run before the retry rather than after it. coerce only
        // follows when the promotion fired, since it would otherwise lift the operands
        // straight back into the exact arm the retry just left.
        promote_complex(id, dispatch_args);
        if (has_arm(arms_present(dispatch_args), Arm::Cx))
            dispatch_args = coerce(id, dispatch_args);
        result = ops::kernel_of(id)(id, c, dispatch_args, unit); // a second throw propagates
    }

    return promote_range(id, c, dispatch_args, result, unit);
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

/// A constant's value, which is a double for all but the imaginary unit.
Value const_value(const consts::ConstSpec &spec) {
    return std::visit([](const auto &x) -> Value { return Value{x}; }, spec.value);
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
        return const_value(*spec);
    return resolve_name(name);
}

/// A Frac / Pow / Root / Log token: each side is a row of its own. An absent side is
/// zero, except a Root's degree, where it means the square root.
Value eval_latex(const parser::LatexToken &latex, const Calculator &c, Calculator::AngleUnit unit) {
    Value left = latex.left.empty() ? Value{Rational(0)} : eval_row(latex.left, c, unit);
    Value right = Value{Rational(latex.kind == LatexKind::Root ? 2 : 0)};
    if (!latex.right.empty())
        right = eval_row(latex.right, c, unit);
    return apply(c, latex.op_id, {std::move(left), std::move(right)}, unit);
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
        return eval_rpn(std::span<const Token>(tok, 1), c, unit);

    const auto &row = std::get<std::vector<Token>>(element);
    if (row.empty())
        throw_invalid(std::string(errmsg::kEmptyElement));
    return eval_row(row, c, unit);
}

/// The two classes a collection may hold. A list is uniform in one of them.
enum class ItemClass : std::uint8_t { None, Scalar, Point };

/// The comma-split elements of a paren group, and of a call's argument list when it folds
/// into a bracket. A Bracket is a List, a Paren is a Point, and arity 1 is grouping for
/// every kind: `(x)` is `x`, which is what makes `mean([1,2,3])` read like `mean[1,2,3]`.
Value eval_elements(
    std::span<const parser::ParenElement> elements,
    parser::ParenKind kind,
    const Calculator &c,
    Calculator::AngleUnit unit) {
    if (elements.size() == 1) {
        Value v = eval_element(elements[0], c, unit);
        // A Bracket is the one kind that groups nothing: `[X]` is a real one-element List
        // once X is a point, and a list inside it has no meaning.
        const auto *inner = std::get_if<Collection>(&v);
        if (inner == nullptr || kind != parser::ParenKind::Bracket)
            return v;
        if (inner->kind == CollectionKind::List)
            throw_invalid(std::string(errmsg::kListOfList));
        return make_collection(CollectionKind::List, {collection_item(v)});
    }

    if (kind == parser::ParenKind::Brace)
        throw_invalid(std::string(errmsg::kBraceUnsupported));

    if (elements.empty()) {
        if (kind == parser::ParenKind::Paren)
            throw_invalid(std::string(errmsg::kEmptyPoint));
        return make_collection(CollectionKind::List, {});
    }

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

    return make_collection(is_point ? CollectionKind::Point : CollectionKind::List, items);
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

/// A call token: a variadic op reduces one dataset, a fixed-arity op takes exactly the
/// arguments its spec names, and no collection among them.
Value eval_call(const parser::CallToken &call, const Calculator &c, Calculator::AngleUnit unit) {
    const ops::OpSpec &spec = *ops::op_spec(call.op_id);

    if (ops::is_variadic(spec))
        return apply(c, call.op_id, {call_dataset(call.args, c, unit)}, unit);

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
    return apply(c, call.op_id, std::move(args), unit);
}

/// An op token: take its operands off the stack and hand them to apply.
Value eval_op(OpId id, std::vector<Value> &stack, const Calculator &c, Calculator::AngleUnit unit) {
    if (id == OpId::Assign)
        throw_invalid(std::string(errmsg::kInvalidAssignment));

    const ops::OpSpec &spec = *ops::op_spec(id);
    // A fixed-arity call function has no infix form. Typed bare it arrives here with too
    // few operands, so it is reported rather than left to underflow. A variadic one does
    // apply to a following collection (`min[1,2,3]`) and is not rejected.
    if (!ops::is_variadic(spec) && spec.call_arity != 1)
        throw_invalid(errmsg::needs_call_form(spec.symbol));

    if (spec.arity != ops::Arity::Binary)
        return apply(c, id, {pop_operand(stack)}, unit);

    Value right = pop_operand(stack);
    Value left = pop_operand(stack);
    return apply(c, id, {std::move(left), std::move(right)}, unit);
}

} // namespace

Value eval_rpn(std::span<const Token> rpn, const Calculator &c, Calculator::AngleUnit unit) {
    std::vector<Value> stack;
    stack.reserve(rpn.size());

    for (const Token &tok : rpn) {
        switch (tok.kind) {
        case TokenKind::Number:
            stack.push_back(literal_value(std::get<parser::NumberToken>(tok.data).value));
            break;
        case TokenKind::Char:
            stack.push_back(
                resolve_name(std::string(1, std::get<parser::CharToken>(tok.data).value)));
            break;
        case TokenKind::Const:
            stack.push_back(
                const_value(*consts::const_spec(std::get<parser::ConstToken>(tok.data).id)));
            break;
        case TokenKind::Latex: {
            const auto &latex = std::get<parser::LatexToken>(tok.data);
            stack.push_back(
                latex.kind == LatexKind::Subscript ? eval_subscript(tok)
                                                   : eval_latex(latex, c, unit));
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

    if (stack.empty())
        throw_malformed(errmsg::kOperandStackEmpty);
    return stack.front();
}

Value eval_row(std::span<const Token> tokens, const Calculator &c, Calculator::AngleUnit unit) {
    return eval_rpn(
        parser::shunting_yard(std::vector<Token>(tokens.begin(), tokens.end())), c, unit);
}

namespace {

/// True for the `=` that heads an assignment.
bool is_assign(const Token &tok) {
    return tok.kind == TokenKind::Op && std::get<parser::OpToken>(tok.data).op_id == OpId::Assign;
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
    const std::span<const Token> tokens(branch.tokens);
    if (tokens.size() < 2 || !is_assign(tokens[1]))
        return eval_row(tokens, c, unit);

    const std::string name = assign_target(tokens[0]);
    const std::span<const Token> rhs = tokens.subspan(2);
    if (rhs.empty())
        throw_invalid(std::string(errmsg::kEmptyAssignment));

    Value value = eval_row(rhs, c, unit);
    session_vars().set(name, value);
    return value;
}

} // namespace tcalc::eval
