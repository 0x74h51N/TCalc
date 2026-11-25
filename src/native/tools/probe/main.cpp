/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

// native_probe: one case on one native layer, without the binding. docs/probe.md says
// which command answers which question.

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <istream>
#include <optional>
#include <span>
#include <sstream>
#include <string>
#include <string_view>
#include <type_traits>
#include <variant>
#include <vector>

#include "calc/pub/calculator.hpp"
#include "calc/pub/errors.hpp"
#include "eval/pub/eval.hpp"
#include "eval/pub/literal.hpp"
#include "eval/pub/varstore.hpp"
#include "frame.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"

namespace {

using tcalc::Value;
using tcalc::probe::ProbeError;
using tcalc::probe::Row;
using Unit = Calculator::AngleUnit;
using tcalc::Arm;

enum class Flag : std::uint8_t { Def, Defs, Time, Unit, NoClosedForms, Arms };
using FlagSet = std::uint8_t;

constexpr FlagSet flag_bit(Flag f) {
    return static_cast<FlagSet>(1U << static_cast<unsigned>(f));
}

struct FlagSpec {
    Flag flag;
    std::string_view name;
    // empty for a flag that takes no value
    std::string_view value;
    std::string_view help;
};

constexpr std::array kFlags{
    FlagSpec{Flag::Def, "--def", "NAME=KIND:VALUE", "a typed operand named once, used as @NAME"},
    FlagSpec{Flag::Defs, "--defs", "FILE", "NAME=KIND:VALUE lines, # starts a comment"},
    FlagSpec{Flag::Time, "--time", "N", "the median nanoseconds of N runs, in an ns column"},
    FlagSpec{Flag::Unit, "--unit", "UNIT", "the angle unit (default DEG, the app's start unit)"},
    FlagSpec{Flag::NoClosedForms, "--no-closed-forms", "", "sums and products by brute force"},
    FlagSpec{Flag::Arms, "--arms", "", "the op on each of its arms, the operands lifted to it"},
};

struct UnitName {
    Unit unit;
    std::string_view name;
};

constexpr std::array kUnits{
    UnitName{Unit::DEG, "DEG"},
    UnitName{Unit::RAD, "RAD"},
    UnitName{Unit::GRAD, "GRAD"},
};

constexpr char kComment = '#';
constexpr char kDefEquals = '=';
constexpr std::string_view kBlank = " \t\r";
constexpr std::string_view kOperandForms =
    "int:-5  dbl:0.1 or dbl:0x1.999999999999ap-4  rat:1/3  big:0.1  cx:RE,IM  bigcx:RE+IMi";
constexpr std::string_view kStdin = "-";
constexpr std::string_view kHelp = "--help";
constexpr std::string_view kUnitColumn = "unit";
constexpr std::string_view kTimeColumn = "ns";
constexpr int kExitUsage = 2;

struct Options {
    // the arguments, and the lines of stdin when one argument is -
    std::vector<std::string> inputs;
    std::vector<std::string> lines;
    tcalc::probe::Defs defs;
    std::optional<int> runs;
    Unit unit = Unit::DEG;
    bool closed_forms = true;
    bool arms = false;
};

std::string_view unit_name(Unit unit) {
    return std::ranges::find(kUnits, unit, &UnitName::unit)->name;
}

/// --time: the median of fn's runs as the ns column.
template <class Fn> void add_time(Row &row, const Options &options, Fn &&fn) {
    if (options.runs) {
        const auto ns = std::llround(tcalc::probe::median_ns(fn, *options.runs));
        row.extra.emplace_back(kTimeColumn, std::to_string(ns));
    }
}

/// The value fn gives, or the error it throws, with the unit; --time adds its median.
template <class Fn>
Row value_row(std::string input, std::string_view layer, const Options &options, Fn &&fn) {
    Row row{
        std::move(input),
        std::string(layer),
        "",
        "",
        {{std::string(kUnitColumn), std::string(unit_name(options.unit))}}};
    try {
        const Value value = fn();
        row.type = tcalc::probe::type_name(value);
        row.value = tcalc::probe::value_text(value);
        add_time(row, options, fn);
    } catch (const CalculatorError &error) {
        row.type = "CalculatorError";
        row.value = error.what();
    } catch (const std::runtime_error &error) {
        // seen: Boost's "non-numeric content" on `$`, which the binding lets through too
        row.type = "RuntimeError";
        row.value = error.what();
    } catch (const std::invalid_argument &error) {
        // seen: Boost's std::stol on an empty or cut literal ('', 1.5e); pybind's ValueError
        row.type = "ValueError";
        row.value = error.what();
    }
    return row;
}

std::vector<std::string> texts(const Options &options) {
    std::vector<std::string> all = options.inputs;
    all.insert(all.end(), options.lines.begin(), options.lines.end());
    return all;
}

std::vector<std::string> words(std::string_view line) {
    std::istringstream stream{std::string(line)};
    std::vector<std::string> out;
    for (std::string word; stream >> word;) {
        out.push_back(word);
    }
    return out;
}

std::vector<Row> run_literal(const Options &options) {
    std::vector<Row> rows;
    for (const auto &text : texts(options)) {
        rows.push_back(
            value_row(text, "literal", options, [&] { return tcalc::eval::literal_value(text); }));
    }
    return rows;
}

/// The operands an op takes: a call's own count, two for a binary op or one with a
/// stand-in second operand (log's base), one otherwise.
std::size_t operand_count(const tcalc::ops::OpSpec &spec) {
    // log is a call of one argument, and its kernel still takes the base
    if (tcalc::ops::second_default_of(spec.id) != 0) {
        return tcalc::ops::kBinaryOperands;
    }
    if (tcalc::ops::is_call_function(spec)) {
        return spec.call_arity;
    }
    switch (spec.arity) {
    case tcalc::ops::Arity::Binary:
        return tcalc::ops::kBinaryOperands;
    case tcalc::ops::Arity::Unary:
    case tcalc::ops::Arity::Postfix:
        return 1;
    }
    throw ProbeError("an Arity with no operand count");
}

/// Where the operands go: apply fills a stand-in second operand (log's base) itself, a
/// kernel or a promotion step alone does not.
enum class Target : std::uint8_t { Apply, Alone };

/// apply drops an extra operand and reads past a missing one, so the count is checked here.
void check_count(const tcalc::ops::OpSpec &spec, std::size_t given, Target target) {
    if (tcalc::ops::is_variadic(spec)) {
        // seen: kernel mean with no operand reads past the end
        if (given == 0) {
            throw ProbeError(std::string(spec.symbol) + " takes one operand or more, got none");
        }
        return;
    }
    const std::size_t takes = operand_count(spec);
    const bool stand_in = tcalc::ops::second_default_of(spec.id) != 0;
    if (given == takes || (target == Target::Apply && stand_in && given + 1 == takes)) {
        return;
    }
    const std::string why = stand_in ? " (apply fills the second; alone it is needed)" : "";
    throw ProbeError(
        std::string(spec.symbol) + " takes " + std::to_string(takes) + " operands, got " +
        std::to_string(given) + why);
}

/// An op and its typed operands, with the input text they print as.
struct OpCase {
    const tcalc::ops::OpSpec *spec;
    std::vector<Value> args;
    std::string input;
};

OpCase op_case(std::span<const std::string> words, const Options &options, Target target) {
    if (words.empty()) {
        throw ProbeError("an op and its operands are needed");
    }
    const auto *spec = tcalc::ops::find_op(words[0]);
    if (spec == nullptr) {
        throw ProbeError(
            "no op '" + words[0] + "'; name it by its symbol or an alias, such as root or sin");
    }
    // apply raises its own error on an op with no kernel (==); alone there is nothing to run
    if (target == Target::Alone && tcalc::ops::kernel_of(spec->id) == nullptr) {
        throw ProbeError(std::string(spec->symbol) + " has no kernel");
    }
    check_count(*spec, words.size() - 1, target);
    OpCase c{spec, {}, std::string(spec->symbol)};
    for (const auto &word : words.subspan(1)) {
        c.args.push_back(tcalc::probe::parse_operand(tcalc::probe::substitute(word, options.defs)));
        c.input += " " + tcalc::probe::operand_text(c.args.back());
    }
    return c;
}

/// The rows of each case: the arguments as one, then each line of stdin as one. A case
/// the probe cannot read is a probe row, so the cases after it still run.
std::vector<Row> per_case(
    const Options &options,
    Target target,
    std::vector<Row> (*rows_of)(const OpCase &, const Options &)) {
    std::vector<Row> rows;
    const auto add = [&](std::span<const std::string> case_words) {
        try {
            const auto more = rows_of(op_case(case_words, options, target), options);
            rows.insert(rows.end(), more.begin(), more.end());
        } catch (const ProbeError &error) {
            rows.push_back(
                {tcalc::probe::join(case_words, " "), "probe", "ProbeError", error.what(), {}});
        }
    };
    if (!options.inputs.empty()) {
        add(options.inputs);
    }
    for (const auto &line : options.lines) {
        add(words(line));
    }
    return rows;
}

std::vector<Row> apply_rows(const OpCase &c, const Options &options) {
    const Calculator calc;
    return {value_row(c.input, "apply", options, [&] {
        return tcalc::eval::apply(calc, c.spec->id, c.args, options.unit);
    })};
}

std::vector<Row> run_apply(const Options &options) {
    return per_case(options, Target::Apply, apply_rows);
}

/// One promotion step: the operands' types and values after it.
Row step_row(const OpCase &c, std::string_view layer, const std::vector<Value> &args) {
    std::vector<std::string> types;
    std::vector<std::string> values;
    for (const auto &arg : args) {
        types.push_back(tcalc::probe::type_name(arg));
        values.push_back(tcalc::probe::value_text(arg));
    }
    return {
        c.input,
        std::string(layer),
        tcalc::probe::join(types, " "),
        tcalc::probe::join(values, " "),
        {}};
}

/// apply's steps before the kernel, in its order (eval.cpp): promote_big, coerce,
/// promote_complex, and coerce again when that changed an arm.
std::vector<Row> promote_rows(const OpCase &c, const Options & /*options*/) {
    const auto id = c.spec->id;
    std::vector<Value> args = c.args;
    std::vector<Row> rows{step_row(c, "in", args)};
    tcalc::eval::promote_big(id, args);
    rows.push_back(step_row(c, "promote_big", args));
    const auto coerced = [&] {
        try {
            args = tcalc::eval::coerce(id, std::move(args));
            rows.push_back(step_row(c, "coerce", args));
            return true;
        } catch (const CalculatorError &error) {
            rows.push_back({c.input, "coerce", "CalculatorError", error.what(), {}});
            return false;
        }
    };
    if (!coerced()) {
        return rows;
    }
    const bool fired = tcalc::eval::promote_complex(id, args);
    rows.push_back(step_row(c, "promote_complex", args));
    if (fired) {
        coerced();
    }
    return rows;
}

std::vector<Row> run_promote(const Options &options) {
    return per_case(options, Target::Alone, promote_rows);
}

struct ArmLift {
    Arm arm;
    std::optional<Value> (*lift)(const Value &);
};

/// The value as an F of value.hpp makes it, or nullopt when F has no overload for its arm.
template <class F> std::optional<Value> lift_with(const Value &v, F f) {
    return std::visit(
        [&](const auto &x) -> std::optional<Value> {
            if constexpr (std::is_invocable_v<F, decltype(x)>) {
                return Value{f(x)};
            } else {
                return std::nullopt;
            }
        },
        v);
}

template <class T> std::optional<Value> held(const Value &v) {
    const auto *x = std::get_if<T>(&v);
    return x != nullptr ? std::optional<Value>{*x} : std::nullopt;
}

// value.hpp's own lifts, one per arm; an int64 and a collection are only ever themselves
const std::array kLifts{
    ArmLift{Arm::Int64, held<std::int64_t>},
    ArmLift{
        Arm::Double,
        [](const Value &v) {
            return lift_with(v, [](const auto &x) -> decltype(tcalc::to_double(x)) {
                return tcalc::to_double(x);
            });
        }},
    ArmLift{
        Arm::Cx,
        [](const Value &v) {
            return lift_with(v, [](const auto &x) -> decltype(tcalc::to_complex(x)) {
                return tcalc::to_complex(x);
            });
        }},
    ArmLift{
        Arm::Big,
        [](const Value &v) {
            return lift_with(
                v, [](const auto &x) -> decltype(tcalc::to_big(x)) { return tcalc::to_big(x); });
        }},
    ArmLift{
        Arm::BigCx,
        [](const Value &v) {
            return lift_with(v, [](const auto &x) -> decltype(tcalc::to_big_complex(x)) {
                return tcalc::to_big_complex(x);
            });
        }},
    ArmLift{
        Arm::Rat,
        [](const Value &v) {
            const auto r = tcalc::to_rational(v);
            return r ? std::optional<Value>{*r} : std::nullopt;
        }},
    ArmLift{Arm::Coll, held<tcalc::Collection>},
};

std::string arm_list(tcalc::ArmMask mask) {
    std::vector<std::string> names;
    for (const auto &lift : kLifts) {
        if (tcalc::has_arm(mask, lift.arm)) {
            names.emplace_back(tcalc::probe::arm_names(lift.arm).type);
        }
    }
    return tcalc::probe::join(names, ", ");
}

Row kernel_row(
    const OpCase &c, const std::vector<Value> &args, std::string input, const Options &options) {
    const Calculator calc;
    const auto kernel = tcalc::ops::kernel_of(c.spec->id);
    return value_row(std::move(input), "kernel", options, [&] {
        return kernel(c.spec->id, calc, args, options.unit);
    });
}

/// The op on each of its arms, the operands lifted to it as value.hpp lifts them.
std::vector<Row> arm_rows(const OpCase &c, const Options &options) {
    std::vector<Row> rows;
    for (const auto &lift : kLifts) {
        if (!tcalc::has_arm(tcalc::ops::arms_of(c.spec->id), lift.arm)) {
            continue;
        }
        std::vector<Value> args;
        std::string input(c.spec->symbol);
        for (const auto &arg : c.args) {
            const auto lifted = lift.lift(arg);
            if (!lifted) {
                rows.push_back(
                    // a type no grader knows, so grade leaves the row alone
                    {c.input,
                     "kernel",
                     "none",
                     std::string(tcalc::probe::arm_names(lift.arm).type) +
                         ": value.hpp has no lift from " + tcalc::probe::type_name(arg),
                     {}});
                break;
            }
            args.push_back(*lifted);
            input += " " + tcalc::probe::operand_text(*lifted);
        }
        if (args.size() == c.args.size()) {
            rows.push_back(kernel_row(c, args, input, options));
        }
    }
    return rows;
}

/// The kernel alone, on operands already of one arm the op has: no promotion, no lattice.
std::vector<Row> kernel_rows(const OpCase &c, const Options &options) {
    if (options.arms) {
        return arm_rows(c, options);
    }
    const auto mask = tcalc::ops::arms_of(c.spec->id);
    std::vector<std::string> types;
    bool one_arm = true;
    for (const auto &arg : c.args) {
        types.push_back(tcalc::probe::type_name(arg));
        one_arm = one_arm && tcalc::arm_of(arg) == tcalc::arm_of(c.args.front()) &&
                  tcalc::has_arm(mask, tcalc::arm_of(arg));
    }
    if (!one_arm) {
        throw ProbeError(
            std::string(c.spec->symbol) + " has no kernel arm for " +
            tcalc::probe::join(types, " ") + "; its arms are " + arm_list(mask) +
            " (--arms lifts to each)");
    }
    return {kernel_row(c, c.args, c.input, options)};
}

std::vector<Row> run_kernel(const Options &options) {
    return per_case(options, Target::Alone, kernel_rows);
}

/// The token texts of one stage, two spaces apart as `probe layers` writes them.
Row tokens_row(
    const std::string &text, std::string_view stage, std::span<const tcalc::parser::Token> tokens) {
    std::vector<std::string> parts;
    for (const auto &token : tokens) {
        parts.push_back(tcalc::parser::token_text(token));
    }
    return {text, std::string(stage), "str", tcalc::probe::join(parts, "  "), {}};
}

std::vector<Row> run_tokens(const Options &options) {
    std::vector<Row> rows;
    for (const auto &text : texts(options)) {
        const auto branch = tcalc::parser::tokenize(text);
        rows.push_back(tokens_row(text, "tokenize", branch.tokens));
        std::string_view stage = "normalize";
        try {
            rows.push_back(tokens_row(text, stage, tcalc::eval::normalize(branch.tokens)));
            stage = "shunting_yard";
            // shunting_yard normalizes on its own, as evaluate calls it
            rows.push_back(tokens_row(text, stage, tcalc::eval::shunting_yard(branch.tokens)));
        } catch (const CalculatorError &error) {
            rows.push_back({text, std::string(stage), "CalculatorError", error.what(), {}});
        }
    }
    return rows;
}

/// A Boost row; --time adds the median of the whole row, its arguments read from text included.
Row timed_boost_row(std::span<const std::string> words, const Options &options) {
    const auto fn = [&] { return tcalc::probe::boost_row(words); };
    Row row = fn();
    add_time(row, options, fn);
    return row;
}

std::vector<Row> run_boost(const Options &options) {
    std::vector<Row> rows;
    if (!options.inputs.empty()) {
        rows.push_back(timed_boost_row(options.inputs, options));
    }
    for (const auto &line : options.lines) {
        rows.push_back(timed_boost_row(words(line), options));
    }
    return rows;
}

std::vector<Row> run_eval(const Options &options) {
    tcalc::eval::set_closed_forms_enabled(options.closed_forms);
    const Calculator calc;
    std::vector<Row> rows;
    for (const auto &text : texts(options)) {
        const auto branch = tcalc::parser::tokenize(text);
        rows.push_back(value_row(text, "eval", options, [&] {
            // a fresh store each run, as the Python probe clears it, so A=1 runs again
            tcalc::eval::session_vars().clear();
            return tcalc::eval::evaluate(branch, calc, options.unit);
        }));
    }
    return rows;
}

struct Command {
    std::string_view name;
    std::string_view help;
    std::string_view example;
    FlagSet flags;
    std::vector<Row> (*run)(const Options &);
};

constexpr FlagSet kTyped = flag_bit(Flag::Def) | flag_bit(Flag::Defs);
constexpr FlagSet kValued = flag_bit(Flag::Time) | flag_bit(Flag::Unit);

constexpr std::array kCommands{
    Command{
        "literal",
        "what a number literal denotes (literal_value): TEXT...",
        "native_probe literal 0.1 1e400 3i",
        kValued,
        run_literal},
    Command{
        "apply",
        "one op on typed operands (eval::apply): OP KIND:VALUE...",
        "native_probe apply root dbl:1e300 int:3 --time 1000",
        kTyped | kValued,
        run_apply},
    Command{
        "eval",
        "an expression through tokenize and evaluate: EXPR...",
        "native_probe eval '\\sum_{n=1}^{10}n' --no-closed-forms",
        kValued | flag_bit(Flag::NoClosedForms),
        run_eval},
    Command{
        "tokens",
        "an expression's tokens after tokenize, normalize and shunting_yard: EXPR...",
        "native_probe tokens '2sin 30'",
        0,
        run_tokens},
    Command{
        "promote",
        "apply's promotion steps, the operands after each (a root or power's real-first rewrite "
        "runs before them and is not shown): OP KIND:VALUE...",
        "native_probe promote sqrt dbl:-4",
        kTyped,
        run_promote},
    Command{
        "kernel",
        "the kernel alone on operands of one arm it has: OP KIND:VALUE...",
        "native_probe kernel root dbl:1e300 dbl:3 --arms",
        kTyped | kValued | flag_bit(Flag::Arms),
        run_kernel},
    Command{
        "boost",
        "a Boost function with TCalc bypassed, a row of boost_table.cpp: NAME TYPE ARG...",
        "native_probe boost int_gcd dec50 1e19 10 --time 1000",
        flag_bit(Flag::Time),
        run_boost},
};

const Command &find_command(std::string_view name) {
    const auto *command = std::ranges::find(kCommands, name, &Command::name);
    if (command == kCommands.end()) {
        throw ProbeError(
            "no command '" + std::string(name) + "'; the commands are " +
            tcalc::probe::names_of(kCommands, &Command::name));
    }
    return *command;
}

void list_commands() {
    for (const auto &command : kCommands) {
        std::cout << command.name << "  " << command.help << "\n    " << command.example << '\n';
    }
}

void command_help(const Command &command) {
    std::cout << command.name << ": " << command.help << '\n';
    for (const auto &flag : kFlags) {
        if ((command.flags & flag_bit(flag.flag)) != 0) {
            std::cout << "  " << flag.name << (flag.value.empty() ? "" : " ") << flag.value << "  "
                      << flag.help << '\n';
        }
    }
    if ((command.flags & flag_bit(Flag::Def)) != 0) {
        std::cout << "  operands: " << kOperandForms << '\n';
    }
    std::cout << "  -  read the inputs from stdin, one per line\n"
              << "example: " << command.example << '\n';
}

bool is_name(std::string_view text) {
    const auto name_char = [](char c) {
        return std::isalnum(static_cast<unsigned char>(c)) != 0 || c == '_';
    };
    return !text.empty() && std::isdigit(static_cast<unsigned char>(text[0])) == 0 &&
           std::ranges::all_of(text, name_char);
}

std::string_view stripped(std::string_view text) {
    const auto start = text.find_first_not_of(kBlank);
    return start == std::string_view::npos
               ? std::string_view{}
               : text.substr(start, text.find_last_not_of(kBlank) - start + 1);
}

/// NAME=KIND:VALUE, blanks around either side allowed, as scripts/probe's definitions.
void define(std::string_view entry, tcalc::probe::Defs &defs) {
    const auto equals = entry.find(kDefEquals);
    const std::string_view name = stripped(entry.substr(0, equals));
    if (equals == std::string_view::npos || !is_name(name)) {
        throw ProbeError("'" + std::string(entry) + "': expected NAME=KIND:VALUE");
    }
    defs.insert_or_assign(std::string(name), std::string(stripped(entry.substr(equals + 1))));
}

std::vector<std::string> entries(std::istream &in) {
    std::vector<std::string> out;
    for (std::string line; std::getline(in, line);) {
        const std::string_view entry = stripped(line);
        if (!entry.empty() && !entry.starts_with(kComment)) {
            out.emplace_back(entry);
        }
    }
    return out;
}

void read_defs(const std::string &path, tcalc::probe::Defs &defs) {
    std::ifstream file(path);
    if (!file) {
        throw ProbeError("cannot read --defs " + path);
    }
    for (const auto &entry : entries(file)) {
        define(entry, defs);
    }
}

int positive(std::string_view text) {
    const auto value = tcalc::probe::whole<int>(text);
    if (!value || *value <= 0) {
        throw ProbeError("--time '" + std::string(text) + "' is not a positive count of runs");
    }
    return *value;
}

/// Any case, as scripts/probe reads it: rad is RAD.
Unit read_unit(std::string_view text) {
    std::string upper(text);
    std::ranges::transform(
        upper, upper.begin(), [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
    const auto *unit = std::ranges::find(kUnits, upper, &UnitName::name);
    if (unit == kUnits.end()) {
        throw ProbeError(
            "no angle unit '" + std::string(text) + "'; the units are " +
            tcalc::probe::names_of(kUnits, &UnitName::name));
    }
    return unit->unit;
}

void set_flag(Flag flag, const std::string &value, Options &options) {
    switch (flag) {
    case Flag::Def:
        define(value, options.defs);
        return;
    case Flag::Defs:
        read_defs(value, options.defs);
        return;
    case Flag::Time:
        options.runs = positive(value);
        return;
    case Flag::Unit:
        options.unit = read_unit(value);
        return;
    case Flag::NoClosedForms:
        options.closed_forms = false;
        return;
    case Flag::Arms:
        options.arms = true;
        return;
    }
}

/// The options of args; nullopt when --help printed the command's help instead.
std::optional<Options> parse(const Command &command, std::span<const std::string> args) {
    Options options;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string &arg = args[i];
        if (arg == kHelp) {
            command_help(command);
            return std::nullopt;
        }
        if (arg == kStdin) {
            options.lines = entries(std::cin);
            continue;
        }
        const auto *flag = std::ranges::find(kFlags, std::string_view(arg), &FlagSpec::name);
        if (flag == kFlags.end()) {
            options.inputs.push_back(arg);
            continue;
        }
        if ((command.flags & flag_bit(flag->flag)) == 0) {
            throw ProbeError(std::string(command.name) + " does not read " + arg);
        }
        std::string value;
        if (!flag->value.empty()) {
            if (++i == args.size()) {
                throw ProbeError(arg + " needs " + std::string(flag->value));
            }
            value = args[i];
        }
        set_flag(flag->flag, value, options);
    }
    return options;
}

} // namespace

int main(int argc, char **argv) {
    const std::span<char *> raw(argv, static_cast<std::size_t>(argc));
    const std::vector<std::string> args(raw.begin() + 1, raw.end());
    if (args.empty()) {
        list_commands();
        return 0;
    }
    try {
        const Command &command = find_command(args[0]);
        const auto options = parse(command, std::span(args).subspan(1));
        if (options) {
            tcalc::probe::print_rows(std::cout, command.run(*options));
        }
        return 0;
    } catch (const ProbeError &error) {
        std::cerr << "native_probe: " << error.what() << '\n';
        return kExitUsage;
    }
}
