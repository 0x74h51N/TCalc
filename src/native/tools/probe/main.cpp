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

enum class Flag : std::uint8_t { Def, Defs, Time, Unit, NoClosedForms };
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
};

std::string_view unit_name(Unit unit) {
    return std::ranges::find(kUnits, unit, &UnitName::unit)->name;
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
        if (options.runs) {
            const auto ns = std::llround(tcalc::probe::median_ns(fn, *options.runs));
            row.extra.emplace_back(kTimeColumn, std::to_string(ns));
        }
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

/// The operands an op takes: a call's own count, two for a binary op, one otherwise.
std::size_t operand_count(const tcalc::ops::OpSpec &spec) {
    if (tcalc::ops::is_call_function(spec)) {
        return spec.call_arity;
    }
    switch (spec.arity) {
    case tcalc::ops::Arity::Binary:
        return 2;
    case tcalc::ops::Arity::Unary:
    case tcalc::ops::Arity::Postfix:
        return 1;
    }
    throw ProbeError("an Arity with no operand count");
}

/// apply drops an extra operand and reads past a missing one, so the count is checked here.
void check_count(const tcalc::ops::OpSpec &spec, std::size_t given) {
    if (tcalc::ops::is_variadic(spec)) {
        return;
    }
    const std::size_t takes = operand_count(spec);
    // apply fills the second operand of an op that names a stand-in (log's base)
    const bool defaulted = tcalc::ops::second_default_of(spec.id) != 0 && given + 1 == takes;
    if (given != takes && !defaulted) {
        throw ProbeError(
            std::string(spec.symbol) + " takes " + std::to_string(takes) + " operands, got " +
            std::to_string(given));
    }
}

Row apply_row(std::span<const std::string> words, const Options &options) {
    if (words.empty()) {
        throw ProbeError("apply needs an op and its operands");
    }
    const auto *spec = tcalc::ops::find_op(words[0]);
    if (spec == nullptr) {
        throw ProbeError(
            "no op '" + words[0] + "'; name it by its symbol or an alias, such as root or sin");
    }
    check_count(*spec, words.size() - 1);
    std::vector<Value> args;
    std::string input(spec->symbol);
    for (const auto &word : words.subspan(1)) {
        args.push_back(tcalc::probe::parse_operand(tcalc::probe::substitute(word, options.defs)));
        input += " " + tcalc::probe::operand_text(args.back());
    }
    const Calculator calc;
    return value_row(input, "apply", options, [&] {
        return tcalc::eval::apply(calc, spec->id, args, options.unit);
    });
}

std::vector<Row> run_apply(const Options &options) {
    std::vector<Row> rows;
    if (!options.inputs.empty()) {
        rows.push_back(apply_row(options.inputs, options));
    }
    for (const auto &line : options.lines) {
        rows.push_back(apply_row(words(line), options));
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
};

const Command &find_command(std::string_view name) {
    const auto *command = std::ranges::find(kCommands, name, &Command::name);
    if (command == kCommands.end()) {
        std::string names;
        for (const auto &c : kCommands) {
            names += (names.empty() ? "" : ", ") + std::string(c.name);
        }
        throw ProbeError("no command '" + std::string(name) + "'; the commands are " + names);
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
        std::string names;
        for (const auto &u : kUnits) {
            names += (names.empty() ? "" : ", ") + std::string(u.name);
        }
        throw ProbeError("no angle unit '" + std::string(text) + "'; the units are " + names);
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
