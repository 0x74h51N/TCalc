#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "calc/pub/calculator.hpp"
#include "eval/pub/eval.hpp"
#include "internal/smoke_helpers.hpp"
#include "internal/test_helpers.hpp"
#include "parser/pub/ops.hpp"
#include "value.hpp"

namespace {

using tcalc::Collection;
using tcalc::CollectionItem;
using tcalc::Value;
using tcalc::ops::OpId;
using K = tcalc::CollectionKind;
namespace ops = tcalc::ops;

/// A case that has not returned in this time froze: `apply` has no deadline of its own.
constexpr int kCaseLimitMs = 1000;

struct Edge {
    std::string name;
    Value value;
};

struct OpCase {
    OpId id;
    std::string symbol;
    std::string name;
    std::vector<Value> args;
};

/// A case known to fail, held until its issue is fixed.
struct SmokePin {
    std::string_view case_id;
    std::string_view issue;
    std::string_view date;
};

const std::vector<SmokePin> kSmokePins = {};

std::vector<Edge> scalar_edges() {
    constexpr auto kMax = std::numeric_limits<std::int64_t>::max();
    constexpr auto kMin = std::numeric_limits<std::int64_t>::min();
    constexpr double kInf = std::numeric_limits<double>::infinity();
    constexpr double kNan = std::numeric_limits<double>::quiet_NaN();
    return {
        {.name = "i64 0", .value = std::int64_t{0}},
        {.name = "i64 1", .value = std::int64_t{1}},
        {.name = "i64 -1", .value = std::int64_t{-1}},
        {.name = "i64 MAX", .value = kMax},
        {.name = "i64 MIN", .value = kMin},
        {.name = "dbl 0", .value = 0.0},
        {.name = "dbl -0", .value = -0.0},
        {.name = "dbl 0.5", .value = 0.5},
        {.name = "dbl 1e19", .value = 1e19},
        {.name = "dbl 2^63", .value = 0x1p63},
        {.name = "dbl 1e308", .value = 1e308},
        {.name = "dbl denorm_min", .value = std::numeric_limits<double>::denorm_min()},
        {.name = "dbl inf", .value = kInf},
        {.name = "dbl -inf", .value = -kInf},
        {.name = "dbl nan", .value = kNan},
        {.name = "rat 1/3", .value = Rational(1, 3)},
        {.name = "rat MAX/1", .value = Rational(kMax)},
        {.name = "rat 1/MAX", .value = Rational(1, kMax)},
        {.name = "big 1e400", .value = BigReal("1e400")},
        {.name = "big 1e-400", .value = BigReal("1e-400")},
        {.name = "cx (inf,0)", .value = Complex(kInf, 0.0)},
        {.name = "cx (0,nan)", .value = Complex(0.0, kNan)},
        {.name = "bigcx (1e400,0)", .value = BigComplex(BigReal("1e400"), 0)},
        {.name = "bigcx (nan,0)", .value = BigComplex(kNan, 0.0)},
    };
}

/// A collection holds every scalar arm but Rational.
std::optional<CollectionItem> to_item(const Value &v) {
    if (const auto *i = std::get_if<std::int64_t>(&v))
        return CollectionItem{*i};
    if (const auto *d = std::get_if<double>(&v))
        return CollectionItem{*d};
    if (const auto *b = std::get_if<BigReal>(&v))
        return CollectionItem{*b};
    if (const auto *z = std::get_if<Complex>(&v))
        return CollectionItem{*z};
    if (const auto *bz = std::get_if<BigComplex>(&v))
        return CollectionItem{*bz};
    return std::nullopt;
}

/// One list per edge and per ordered pair, so an abort is never hidden behind an earlier item
/// that throws first.
std::vector<Edge> collection_edges(const std::vector<Edge> &scalars) {
    std::vector<Edge> out{
        {.name = "[]", .value = Collection{K::List, {}}},
        {.name = "point(1,2)", .value = Collection{K::Point, {std::int64_t{1}, std::int64_t{2}}}},
    };
    for (const auto &a : scalars) {
        const auto ia = to_item(a.value);
        if (!ia)
            continue;
        out.push_back({.name = "[" + a.name + "]", .value = Collection{K::List, {*ia}}});
        for (const auto &b : scalars)
            if (const auto ib = to_item(b.value))
                out.push_back(
                    {.name = "[" + a.name + ", " + b.name + "]",
                     .value = Collection{K::List, {*ia, *ib}}});
    }
    return out;
}

/// Every op with a kernel, over the edges its operand count takes.
std::vector<OpCase> op_cases() {
    const std::vector<Edge> scalars = scalar_edges();
    const std::vector<Edge> lists = collection_edges(scalars);
    std::vector<OpCase> cases;
    for (std::size_t n = 0; n < ops::kOpCount; ++n) {
        const auto id = static_cast<OpId>(n);
        if (ops::kernel_of(id) == nullptr)
            continue;
        const ops::OpSpec &spec = *ops::op_spec(id);
        const std::string sym(spec.symbol);
        const auto add = [&](const std::string &name, std::vector<Value> args) {
            cases.push_back(
                {.id = id, .symbol = sym, .name = sym + " :: " + name, .args = std::move(args)});
        };
        if (ops::is_variadic(spec)) {
            for (const auto &l : lists)
                add(l.name, {l.value});
        } else if (spec.arity == ops::Arity::Binary || spec.call_arity == 2) {
            for (const auto &a : scalars)
                for (const auto &b : scalars)
                    add(a.name + ", " + b.name, {a.value, b.value});
        } else {
            for (const auto &a : scalars)
                add(a.name, {a.value});
        }
    }
    return cases;
}

std::string_view fault_name(CaseFault f) {
    switch (f) {
    case CaseFault::Abort:
        return "abort";
    case CaseFault::Freeze:
        return "freeze";
    case CaseFault::Exception:
        return "exception";
    }
    return {};
}

/// Each op is one case listing its unpinned failures; a pin that no longer fails is red too.
void smoke_ops(TestContext &ctx) {
    const std::vector<OpCase> cases = op_cases();
    const Calculator c;
    const IsolatedRun run = run_isolated(cases.size(), kCaseLimitMs, [&](std::size_t i) {
        (void)tcalc::eval::apply(c, cases[i].id, cases[i].args, Calculator::AngleUnit::RAD);
    });

    test_detail::with_case(ctx, "ops :: setup", [&] {
        EXPECT_MSG(ctx, !run.setup_error, [&](auto &os) { os << run.setup_error.value_or(""); });
    });

    std::map<std::size_t, const CaseFailure *> failures;
    for (const auto &f : run.failures)
        failures.emplace(f.index, &f);
    std::map<std::string_view, const SmokePin *> pins;
    for (const auto &p : kSmokePins)
        pins.emplace(p.case_id, &p);

    for (std::size_t i = 0; i < cases.size(); ++i) {
        const auto f = failures.find(i);
        const auto pin = pins.find(cases[i].name);
        test_detail::with_case(ctx, "ops :: " + cases[i].name, [&] {
            if (pin == pins.end()) {
                EXPECT_MSG(ctx, f == failures.end(), [&](auto &os) {
                    os << fault_name(f->second->fault) << " " << f->second->detail;
                });
            } else {
                EXPECT_MSG(ctx, f != failures.end(), [&](auto &os) {
                    os << "pinned case passes, remove its pin (" << pin->second->issue << ")";
                });
                pins.erase(pin);
            }
        });
    }

    test_detail::with_case(ctx, "ops :: pins", [&] {
        EXPECT_MSG(ctx, pins.empty(), [&](auto &os) {
            for (const auto &[id, p] : pins)
                os << "unknown pin: " << id << " ";
        });
    });
}

} // namespace

void smoke_stress(TestContext &ctx) {
    Calculator c;
    using BC = BigComplex;
    using BF = boost::multiprecision::cpp_bin_float_50;

    const double inf = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();

    smoke_allow_math_error(ctx, "double :: add inf one", [&] { (void)c.add(inf, 1.0); });
    smoke_allow_math_error(ctx, "double :: mul inf zero", [&] { (void)c.mul(inf, 0.0); });
    smoke_allow_math_error(ctx, "double :: div one inf", [&] { (void)c.div(1.0, inf); });
    smoke_allow_math_error(ctx, "double :: div one zero", [&] { (void)c.div(1.0, 0.0); });

    smoke_allow_math_error(ctx, "double :: pow large exp", [&] { (void)c.pow(10.0, 308.0); });
    smoke_allow_math_error(
        ctx, "double :: pow large base int exp", [&] { (void)c.pow(1e154, 2LL); });

    smoke_allow_math_error(ctx, "double :: sqrt inf", [&] { (void)c.sqrt(inf); });
    smoke_allow_math_error(ctx, "double :: sqrt nan", [&] { (void)c.sqrt(nan); });
    smoke_allow_math_error(ctx, "double :: log inf", [&] { (void)c.log(inf); });
    smoke_allow_math_error(ctx, "double :: log nan", [&] { (void)c.log(nan); });

    smoke_allow_math_error(
        ctx, "double :: sin inf", [&] { (void)c.sin(inf, Calculator::AngleUnit::RAD); });
    smoke_allow_math_error(
        ctx, "double :: cos nan", [&] { (void)c.cos(nan, Calculator::AngleUnit::RAD); });

    smoke_allow_math_error(ctx, "double :: fact large", [&] { (void)c.fact(171.0); });
    smoke_allow_math_error(ctx, "double :: fact huge", [&] { (void)c.fact(1e17); });
    smoke_allow_math_error(ctx, "double :: fact inf", [&] { (void)c.fact(inf); });
    smoke_allow_math_error(ctx, "double :: gamma huge", [&] { (void)c.gamma(1e17); });

    smoke_allow_math_error(ctx, "double :: choose large", [&] { (void)c.choose(500, 250); });

    const BigReal hug = BigReal("1e1000");
    smoke_allow_math_error(ctx, "bigreal :: sqrt huge", [&] { (void)c.sqrt(hug); });
    smoke_allow_math_error(ctx, "bigreal :: log huge", [&] { (void)c.log(hug); });
    smoke_allow_math_error(ctx, "bigreal :: pow huge", [&] { (void)c.pow(hug, BigReal("2.0")); });

    const BigReal hug2 = BigReal("1e20000");
    smoke_allow_math_error(ctx, "bigreal :: sqrt enormous", [&] { (void)c.sqrt(hug2); });
    smoke_allow_math_error(
        ctx, "bigreal :: root enormous", [&] { (void)c.root(hug2, BigReal("7")); });
    smoke_allow_math_error(
        ctx, "bigreal :: pow enormous", [&] { (void)c.pow(hug2, BigReal("3")); });

    const BC z("1e400", "1");
    const BC z_pow = c.pow(z, BC("20000"));
    TEST_CASE(ctx, "bigcomplex :: pow enormous", {
        EXPECT_TRUE(ctx, boost::multiprecision::abs(z_pow) > BF(0));
    });

    const BC z_log = c.log(z);
    TEST_CASE(ctx, "bigcomplex :: log enormous", {
        EXPECT_TRUE(ctx, boost::multiprecision::abs(z_log) > BF(0));
    });

    const BC z_root = c.root(BC("1e400", "1e-50"), BC("3"));
    TEST_CASE(ctx, "bigcomplex :: root enormous", {
        EXPECT_TRUE(ctx, boost::multiprecision::abs(z_root) > BF(0));
    });

    const BC z_pow2 = c.pow(BC("1e200", "1e200"), BC("5000"));
    TEST_CASE(ctx, "bigcomplex :: pow huge", {
        EXPECT_TRUE(ctx, boost::multiprecision::abs(z_pow2) > BF(0));
    });

    smoke_ops(ctx);
}
