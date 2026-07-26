/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <pybind11/complex.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/typing.h>

#include <string>
#include <variant>

#include "bindings.hpp"
#include "eval/pub/eval.hpp"
#include "parser/pub/consts.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"

namespace py = pybind11;
namespace p = tcalc::parser;

namespace {
py::list math_nodes_to_list(const std::vector<p::MathNode> &nodes);

py::tuple math_node_to_tuple(const p::MathNode &n) {
    return std::visit(
        [](const auto &v) -> py::tuple {
            using T = std::decay_t<decltype(v)>;
            if constexpr (std::is_same_v<T, p::TextNode>) {
                return py::make_tuple(0, v.text);
            } else if constexpr (std::is_same_v<T, p::ParenNode>) {
                return py::make_tuple(1, v.kind, v.has_close, math_nodes_to_list(v.children));
            } else {
                return py::make_tuple(
                    2, v.kind, math_nodes_to_list(v.left), math_nodes_to_list(v.right));
            }
        },
        n.data);
}

py::list math_nodes_to_list(const std::vector<p::MathNode> &nodes) {
    py::list out;
    for (const auto &n : nodes) {
        out.append(math_node_to_tuple(n));
    }
    return out;
}
} // namespace

void bind_parser(py::module_ &m) {
    using p::CallToken;
    using p::CharToken;
    using p::ConstToken;
    using p::LatexKind;
    using p::LatexToken;
    using p::NumberToken;
    using p::OpToken;
    using p::ParenKind;
    using p::ParenToken;
    using p::Token;
    using p::TokenKind;
    using p::TokensBranch;
    using tcalc::consts::CategoryId;
    using tcalc::consts::ConstId;
    using tcalc::consts::ConstSpec;
    using tcalc::ops::OpId;

    py::enum_<TokenKind>(m, "TokenKind", "Token categories produced by the native tokenizer.")
        .value("Number", TokenKind::Number)
        .value("Op", TokenKind::Op)
        .value("Paren", TokenKind::Paren)
        .value("Latex", TokenKind::Latex)
        .value("Call", TokenKind::Call)
        .value("Char", TokenKind::Char)
        .value("Const", TokenKind::Const);

    py::enum_<LatexKind>(m, "LatexKind", "Expression kinds for compound Latex tokens.")
        .value("Frac", LatexKind::Frac)
        .value("Pow", LatexKind::Pow)
        .value("Root", LatexKind::Root)
        .value("Log", LatexKind::Log)
        .value("Subscript", LatexKind::Subscript)
        .value("Sum", LatexKind::Sum)
        .value("Prod", LatexKind::Prod);

    py::enum_<ParenKind>(m, "ParenKind")
        .value("Paren", ParenKind::Paren)
        .value("Brace", ParenKind::Brace)
        .value("Bracket", ParenKind::Bracket);

    py::enum_<OpId>(
        m, "OpId", "Operation identifiers used by tokens and op_table; maps to engine methods.")
        .value("Add", OpId::Add)
        .value("Sub", OpId::Sub)
        .value("Mul", OpId::Mul)
        .value("Div", OpId::Div)
        .value("Pow", OpId::Pow)
        .value("Percent", OpId::Percent)
        .value("Negate", OpId::Negate)
        .value("UnaryPlus", OpId::UnaryPlus)
        .value("Sqrt", OpId::Sqrt)
        .value("Sin", OpId::Sin)
        .value("Cos", OpId::Cos)
        .value("Tan", OpId::Tan)
        .value("Sinh", OpId::Sinh)
        .value("Cosh", OpId::Cosh)
        .value("Tanh", OpId::Tanh)
        .value("Asin", OpId::Asin)
        .value("Acos", OpId::Acos)
        .value("Atan", OpId::Atan)
        .value("Asinh", OpId::Asinh)
        .value("Acosh", OpId::Acosh)
        .value("Atanh", OpId::Atanh)
        .value("Polar", OpId::Polar)
        .value("Log", OpId::Log)
        .value("Ln", OpId::Ln)
        .value("Recip", OpId::Recip)
        .value("Fact", OpId::Fact)
        .value("Mod", OpId::Mod)
        .value("IntDiv", OpId::IntDiv)
        .value("Choose", OpId::Choose)
        .value("Permute", OpId::Permute)
        .value("Gamma", OpId::Gamma)
        .value("Cbrt", OpId::Cbrt)
        .value("Sqr", OpId::Sqr)
        .value("Cube", OpId::Cube)
        .value("Root", OpId::Root)
        .value("Exp", OpId::Exp)
        .value("Pow10", OpId::Pow10)
        .value("Trunc", OpId::Trunc)
        .value("Floor", OpId::Floor)
        .value("Ceil", OpId::Ceil)
        .value("Gcd", OpId::Gcd)
        .value("Lcm", OpId::Lcm)
        .value("Mean", OpId::Mean)
        .value("Median", OpId::Median)
        .value("Min", OpId::Min)
        .value("Max", OpId::Max)
        .value("Sum", OpId::Sum)
        .value("Var", OpId::Var)
        .value("VarP", OpId::VarP)
        .value("Std", OpId::Std)
        .value("StdP", OpId::StdP)
        .value("Assign", OpId::Assign)
        .value("Equal", OpId::Equal);

    py::enum_<ConstId>(m, "ConstId", "Constant identifiers used by ConstToken and const_table.")
        .value("Pi", ConstId::Pi)
        .value("EulerNumber", ConstId::EulerNumber)
        .value("Imaginary", ConstId::Imaginary)
        .value("GoldenRatio", ConstId::GoldenRatio)
        .value("Tau", ConstId::Tau)
        .value("SpeedOfLight", ConstId::SpeedOfLight)
        .value("PlanckH", ConstId::PlanckH)
        .value("PlanckHbar", ConstId::PlanckHbar)
        .value("Gravitation", ConstId::Gravitation)
        .value("VacuumPermittivity", ConstId::VacuumPermittivity)
        .value("VacuumPermeability", ConstId::VacuumPermeability)
        .value("VacuumImpedance", ConstId::VacuumImpedance)
        .value("ElementaryCharge", ConstId::ElementaryCharge)
        .value("FineStructure", ConstId::FineStructure)
        .value("BohrRadius", ConstId::BohrRadius)
        .value("Rydberg", ConstId::Rydberg)
        .value("ElectronMass", ConstId::ElectronMass)
        .value("ProtonMass", ConstId::ProtonMass)
        .value("NeutronMass", ConstId::NeutronMass)
        .value("GasConstant", ConstId::GasConstant)
        .value("Boltzmann", ConstId::Boltzmann)
        .value("Avogadro", ConstId::Avogadro)
        .value("Faraday", ConstId::Faraday)
        .value("AtomicMass", ConstId::AtomicMass)
        .value("StefanBoltzmann", ConstId::StefanBoltzmann)
        .value("WienDisplacement", ConstId::WienDisplacement)
        .value("VonKlitzing", ConstId::VonKlitzing)
        .value("Josephson", ConstId::Josephson)
        .value("BohrMagneton", ConstId::BohrMagneton)
        .value("NuclearMagneton", ConstId::NuclearMagneton);

    py::enum_<CategoryId>(m, "CategoryId", "Constant category for GUI menu grouping.")
        .value("Mathematics", CategoryId::Mathematics)
        .value("Universal", CategoryId::Universal)
        .value("Electromagnetism", CategoryId::Electromagnetism)
        .value("AtomicNuclear", CategoryId::AtomicNuclear)
        .value("Thermodynamics", CategoryId::Thermodynamics)
        .value("Chemistry", CategoryId::Chemistry);

    py::class_<tcalc::parser::LatexEntry>(
        m, "LatexEntry", "LaTeX expression mapping: symbol -> LatexKind.")
        .def_property_readonly(
            "symbol", [](const tcalc::parser::LatexEntry &e) { return std::string(e.symbol); })
        .def_readonly("kind", &tcalc::parser::LatexEntry::kind)
        .def_readonly("opid", &tcalc::parser::LatexEntry::opid);

    m.def(
        "latex_exprs",
        []() {
            py::list out;
            for (const auto &entry : tcalc::parser::kLatexExprs) {
                out.append(&entry);
            }
            return out;
        },
        "Return list of LatexEntry objects from the native LaTeX expression table.",
        py::return_value_policy::reference);

    // NumberToken
    py::class_<NumberToken>(m, "NumberToken")
        .def_readonly("value", &NumberToken::value)
        .def(
            py::pickle(
                [](const NumberToken &t) { return py::make_tuple(t.value); },
                [](const py::tuple &t) {
                    if (t.size() != 1)
                        throw std::runtime_error("Invalid NumberToken state");
                    return NumberToken{t[0].cast<std::string>()};
                }));

    // CharToken
    py::class_<CharToken>(m, "CharToken")
        .def_property_readonly("value", [](const CharToken &t) { return std::string(1, t.value); })
        .def(
            py::pickle(
                [](const CharToken &t) { return py::make_tuple(std::string(1, t.value)); },
                [](const py::tuple &t) {
                    if (t.size() != 1)
                        throw std::runtime_error("Invalid CharToken state");
                    return CharToken{t[0].cast<std::string>().at(0)};
                }));

    // ConstToken
    py::class_<ConstToken>(m, "ConstToken")
        .def_readonly("id", &ConstToken::id)
        .def(
            py::pickle(
                [](const ConstToken &t) { return py::make_tuple(t.id); },
                [](const py::tuple &t) {
                    if (t.size() != 1)
                        throw std::runtime_error("Invalid ConstToken state");
                    return ConstToken{t[0].cast<ConstId>()};
                }));

    // OpToken
    py::class_<OpToken>(m, "OpToken")
        .def_readonly("op_id", &OpToken::op_id)
        .def(
            py::pickle(
                [](const OpToken &t) { return py::make_tuple(t.op_id); },
                [](const py::tuple &t) {
                    if (t.size() != 1)
                        throw std::runtime_error("Invalid OpToken state");
                    return OpToken{t[0].cast<OpId>()};
                }));

    // LatexToken — forward-declare, pickle added after Token
    py::class_<LatexToken> LatexToken_(m, "LatexToken");

    // ParenToken — forward-declare, properties added after Token (recursive elements
    // reference Token).
    py::class_<ParenToken> ParenToken_(
        m,
        "ParenToken",
        "Unified paren token: '(...)', '[...]', '{...}', unclosed open, or stray close.");

    // CallToken — forward-declare, properties added after Token (recursive args
    // reference Token, same as ParenToken's elements).
    py::class_<CallToken> CallToken_(m, "CallToken", "Function call: op + argument token lists.");

    auto Token_ = py::class_<Token>(m, "Token")
                      .def_readonly("kind", &Token::kind)
                      .def_readonly("start_pos", &Token::start_pos)
                      .def_readonly("end_pos", &Token::end_pos);

    def_readonly_ref(Token_, "data", &Token::data)

        .def_property_readonly(
            "data",
            [](const Token &tok) -> py::object {
                return std::visit([](auto &&v) -> py::object { return py::cast(v); }, tok.data);
            })

        // ---- Typed accessors ----

        .def("as_number", &token_as<NumberToken>, py::return_value_policy::reference_internal)

        .def("as_op", &token_as<OpToken>, py::return_value_policy::reference_internal)

        .def("as_paren", &token_as<ParenToken>, py::return_value_policy::reference_internal)

        .def("as_latex", &token_as<LatexToken>, py::return_value_policy::reference_internal)

        .def("as_call", &token_as<CallToken>, py::return_value_policy::reference_internal)

        .def("as_char", &token_as<CharToken>, py::return_value_policy::reference_internal)

        .def("as_const", &token_as<ConstToken>, py::return_value_policy::reference_internal)

        .def_property_readonly(
            "symbol",
            [](const Token &tok) -> std::string {
                if (auto p = token_as<OpToken>(tok)) {
                    const auto *spec = tcalc::ops::op_spec(p->op_id);
                    return spec ? std::string(spec->symbol) : "";
                }
                return "";
            })
        .def(
            py::pickle(
                [](const Token &tok) -> py::tuple {
                    py::object data = std::visit(
                        [](const auto &v) -> py::object { return py::cast(v); }, tok.data);
                    return py::make_tuple(tok.kind, data, tok.start_pos, tok.end_pos);
                },
                [](const py::tuple &t) -> Token {
                    if (t.size() != 4)
                        throw std::runtime_error("Invalid Token state");
                    Token tok;
                    tok.kind = t[0].cast<TokenKind>();
                    tok.start_pos = t[2].cast<std::size_t>();
                    tok.end_pos = t[3].cast<std::size_t>();
                    switch (tok.kind) {
                    case TokenKind::Number:
                        tok.data = t[1].cast<NumberToken>();
                        break;
                    case TokenKind::Op:
                        tok.data = t[1].cast<OpToken>();
                        break;
                    case TokenKind::Paren:
                        tok.data = t[1].cast<ParenToken>();
                        break;
                    case TokenKind::Latex:
                        tok.data = t[1].cast<LatexToken>();
                        break;
                    case TokenKind::Call:
                        tok.data = t[1].cast<CallToken>();
                        break;
                    case TokenKind::Char:
                        tok.data = t[1].cast<CharToken>();
                        break;
                    case TokenKind::Const:
                        tok.data = t[1].cast<ConstToken>();
                        break;
                    }
                    return tok;
                }));

    py::class_<TokensBranch>(m, "TokensBranch", "Result of tokenization with metadata.")
        .def_readonly("tokens", &TokensBranch::tokens)
        .def_readonly("latex_indices", &TokensBranch::latex_indices)
        .def_readonly("paren_indices", &TokensBranch::paren_indices)
        .def_readonly("has_latex_descendant", &TokensBranch::has_latex_descendant)
        .def_readonly("has_call", &TokensBranch::has_call)
        .def(
            py::pickle(
                [](const TokensBranch &r) {
                    return py::make_tuple(
                        r.tokens,
                        r.latex_indices,
                        r.paren_indices,
                        r.has_latex_descendant,
                        r.has_call);
                },
                [](const py::tuple &t) {
                    constexpr std::size_t kTokensBranchPickleArity = 5;
                    if (t.size() != kTokensBranchPickleArity)
                        throw std::runtime_error("Invalid TokensBranch state");
                    TokensBranch r;
                    r.tokens = t[0].cast<std::vector<Token>>();
                    r.latex_indices = t[1].cast<std::vector<tcalc::parser::TokenIndex>>();
                    r.paren_indices = t[2].cast<std::vector<tcalc::parser::TokenIndex>>();
                    r.has_latex_descendant = t[3].cast<bool>();
                    r.has_call = t[4].cast<bool>();
                    return r;
                }));

    // LatexToken — properties + pickle (after TokensBranch so left/right resolve)
    LatexToken_.def_readonly("kind", &LatexToken::kind);
    LatexToken_.def_readonly("op_id", &LatexToken::op_id);
    def_readonly_ref(LatexToken_, "left", &LatexToken::left);
    def_readonly_ref(LatexToken_, "right", &LatexToken::right);
    LatexToken_.def(
        py::pickle(
            [](const LatexToken &t) { return py::make_tuple(t.kind, t.op_id, t.left, t.right); },
            [](const py::tuple &t) {
                if (t.size() != 4)
                    throw std::runtime_error("Invalid LatexToken state");
                return LatexToken{
                    t[0].cast<LatexKind>(),
                    t[1].cast<OpId>(),
                    t[2].cast<std::vector<Token>>(),
                    t[3].cast<std::vector<Token>>()};
            }));

    // ParenToken — properties + pickle
    ParenToken_.def_readonly("kind", &ParenToken::kind);
    ParenToken_.def_readonly("has_open", &ParenToken::has_open);
    ParenToken_.def_readonly("has_close", &ParenToken::has_close);
    ParenToken_.def_readonly("has_latex_descendant", &ParenToken::has_latex_descendant);
    def_readonly_ref(ParenToken_, "elements", &ParenToken::elements);
    ParenToken_.def("rows", [](const ParenToken &p) {
        py::list out;
        for (const auto &e : p.elements) {
            py::list row;
            if (e.index() == 0) {
                row.append(std::get<Token>(e));
            } else {
                for (const auto &t : std::get<std::vector<Token>>(e)) {
                    row.append(t);
                }
            }
            out.append(row);
        }
        return out;
    });
    ParenToken_.def(
        py::pickle(
            [](const ParenToken &t) {
                return py::make_tuple(
                    t.kind, t.elements, t.has_open, t.has_close, t.has_latex_descendant);
            },
            [](const py::tuple &t) {
                constexpr std::size_t kParenTokenPickleArity = 5;
                if (t.size() != kParenTokenPickleArity)
                    throw std::runtime_error("Invalid ParenToken state");
                // Manually iterate elements to avoid pybind11 default-constructing
                // a type_caster<variant<Token, vector<Token>>>.
                std::vector<p::ParenElement> elements;
                for (auto h : t[1]) {
                    auto obj = py::reinterpret_borrow<py::object>(h);
                    if (py::isinstance<Token>(obj)) {
                        elements.emplace_back(obj.cast<Token>());
                    } else {
                        elements.emplace_back(obj.cast<std::vector<Token>>());
                    }
                }
                return ParenToken{
                    t[0].cast<ParenKind>(),
                    std::move(elements),
                    t[2].cast<bool>(),
                    t[3].cast<bool>(),
                    t[4].cast<bool>()};
            }));

    // CallToken — properties + pickle
    CallToken_.def_readonly("op_id", &CallToken::op_id);
    CallToken_.def_readonly("has_close", &CallToken::has_close);
    CallToken_.def_readonly("has_latex_descendant", &CallToken::has_latex_descendant);
    def_readonly_ref(CallToken_, "args", &CallToken::args);
    CallToken_.def(
        py::pickle(
            [](const CallToken &t) {
                return py::make_tuple(t.op_id, t.args, t.has_close, t.has_latex_descendant);
            },
            [](const py::tuple &t) {
                constexpr std::size_t kCallTokenPickleArity = 4;
                if (t.size() != kCallTokenPickleArity)
                    throw std::runtime_error("Invalid CallToken state");
                // Manually iterate args to avoid pybind11 default-constructing
                // a type_caster<variant<Token, vector<Token>>>.
                std::vector<p::ParenElement> args;
                for (auto h : t[1]) {
                    auto obj = py::reinterpret_borrow<py::object>(h);
                    if (py::isinstance<Token>(obj)) {
                        args.emplace_back(obj.cast<Token>());
                    } else {
                        args.emplace_back(obj.cast<std::vector<Token>>());
                    }
                }
                return CallToken{
                    t[0].cast<OpId>(), std::move(args), t[2].cast<bool>(), t[3].cast<bool>()};
            }));

    py::enum_<tcalc::ops::Assoc>(m, "OpAssoc", "Operator associativity.")
        .value("Left", tcalc::ops::Assoc::Left)
        .value("Right", tcalc::ops::Assoc::Right);

    py::enum_<tcalc::ops::Arity>(m, "OpArity", "Operator arity: unary, binary, or postfix.")
        .value("Binary", tcalc::ops::Arity::Binary)
        .value("Unary", tcalc::ops::Arity::Unary)
        .value("Postfix", tcalc::ops::Arity::Postfix);

    // Bind OpSpec structure
    py::class_<tcalc::ops::OpSpec>(m, "OpSpec", "Operator specification from native op table.")
        .def_readonly("id", &tcalc::ops::OpSpec::id, "Operation identifier")
        .def_property_readonly(
            "symbol", [](const tcalc::ops::OpSpec &op) { return std::string(op.symbol); })
        .def_readonly("precedence", &tcalc::ops::OpSpec::precedence, "Operator precedence")
        .def_readonly("associativity", &tcalc::ops::OpSpec::associativity, "Operator associativity")
        .def_readonly("arity", &tcalc::ops::OpSpec::arity, "Operator arity")
        .def_property_readonly(
            "aliases",
            [](const tcalc::ops::OpSpec &op) {
                py::list out;
                for (const auto alias : op.aliases) {
                    if (!alias.empty()) {
                        out.append(std::string(alias));
                    }
                }
                return out;
            })
        .def_property_readonly(
            "method", [](const tcalc::ops::OpSpec &op) { return std::string(op.method); })
        .def_readonly("call_arity", &tcalc::ops::OpSpec::call_arity, "Call argument count")
        .def_property_readonly("is_variadic", [](const tcalc::ops::OpSpec &op) {
            return tcalc::ops::is_variadic(op);
        });

    m.def(
        "op_table",
        []() -> py::typing::List<tcalc::ops::OpSpec> {
            py::typing::List<tcalc::ops::OpSpec> out;
            for (const auto &op : tcalc::ops::kOps) {
                out.append(&op);
            }
            return out;
        },
        "Return list of OpSpec objects from the native operation table.",
        py::return_value_policy::reference);

    py::class_<ConstSpec>(m, "ConstSpec", "Constant specification from the native constant table.")
        .def_readonly("id", &ConstSpec::id)
        .def_readonly("category", &ConstSpec::category)
        .def_property_readonly("symbol", [](const ConstSpec &c) { return std::string(c.symbol); })
        .def_property_readonly(
            "aliases",
            [](const ConstSpec &c) {
                py::list out;
                for (const auto a : c.aliases)
                    if (!a.empty())
                        out.append(std::string(a));
                return out;
            })
        .def_property_readonly("value", [](const ConstSpec &c) -> py::object {
            return std::visit([](auto v) -> py::object { return py::cast(v); }, c.value);
        });

    m.def(
        "const_table",
        []() -> py::typing::List<ConstSpec> {
            py::typing::List<ConstSpec> out;
            for (const auto &c : tcalc::consts::kConstants)
                out.append(&c);
            return out;
        },
        "Return list of ConstSpec objects from the native constant table.",
        py::return_value_policy::reference);

    m.def("tokenize_string", &tcalc::parser::tokenize, py::arg("expression"));
    m.def("classify_tokens", &tcalc::parser::classify_tokens, py::arg("tokens"));
    m.def(
        "shunting_yard",
        [](const std::vector<tcalc::parser::Token> &tokens) {
            return tcalc::eval::shunting_yard(tokens);
        },
        py::arg("tokens"));

    using p::LatexSplit;
    using p::ParenSplit;

    const auto span_to_list = [](std::span<const Token> src) {
        py::list out;
        for (const Token &t : src) {
            out.append(py::cast(&t, py::return_value_policy::reference));
        }
        return out;
    };

    py::class_<ParenSplit>(m, "ParenSplit")
        .def_readonly("kind", &ParenSplit::kind)
        .def_readonly("has_open", &ParenSplit::has_open)
        .def_readonly("has_close", &ParenSplit::has_close)
        .def_property_readonly(
            "prefix", [span_to_list](const ParenSplit &s) { return span_to_list(s.prefix); })
        .def_property_readonly(
            "suffix", [span_to_list](const ParenSplit &s) { return span_to_list(s.suffix); })
        .def_property_readonly("elements", [](const ParenSplit &s) {
            py::list out;
            for (const auto &e : s.elements) {
                if (e.index() == 0) {
                    out.append(py::cast(&std::get<Token>(e), py::return_value_policy::reference));
                } else {
                    py::list inner;
                    for (const auto &t : std::get<std::vector<Token>>(e)) {
                        inner.append(py::cast(&t, py::return_value_policy::reference));
                    }
                    out.append(inner);
                }
            }
            return out;
        });

    py::class_<LatexSplit>(m, "LatexSplit")
        .def_readonly("kind", &LatexSplit::kind)
        .def_property_readonly(
            "prefix", [span_to_list](const LatexSplit &s) { return span_to_list(s.prefix); })
        .def_property_readonly(
            "left", [span_to_list](const LatexSplit &s) { return span_to_list(s.left); })
        .def_property_readonly(
            "right", [span_to_list](const LatexSplit &s) { return span_to_list(s.right); })
        .def_property_readonly(
            "suffix", [span_to_list](const LatexSplit &s) { return span_to_list(s.suffix); });

    m.def(
        "structural_split",
        [](const p::TokensBranch &branch) -> py::object {
            auto result = p::structural_split(branch);
            if (!result.has_value()) {
                return py::none();
            }
            return std::visit([](auto &&v) -> py::object { return py::cast(v); }, *result);
        },
        py::arg("branch"),
        py::keep_alive<0, 1>(),
        "Find the next structural split point in a TokensBranch.");

    m.def(
        "split_operand",
        [](const std::vector<p::Token> &tokens, bool lead) {
            auto [a, b] = p::split_operand(tokens, 0, tokens.size(), lead);
            return py::make_tuple(
                std::vector<p::Token>(a.begin(), a.end()),
                std::vector<p::Token>(b.begin(), b.end()));
        },
        py::arg("tokens"),
        py::arg("lead") = false,
        "Extract leading/trailing operand; trailing returns (prefix, operand), "
        "leading returns (operand, suffix).");

    using p::LatexNode;
    using p::MathNode;
    using p::ParenNode;
    using p::TextNode;

    // MathNode flat tuple shape (single boundary crossing per node):
    //   Text:  (MATH_TAG_TEXT,  str)
    //   Paren: (MATH_TAG_PAREN, ParenKind, has_close, list)
    //   Latex: (MATH_TAG_LATEX, LatexKind, list, list)
    m.attr("MATH_TAG_TEXT") = 0;
    m.attr("MATH_TAG_PAREN") = 1;
    m.attr("MATH_TAG_LATEX") = 2;

    m.def(
        "build_math_nodes",
        [](const TokensBranch &branch, bool after_node) {
            return math_nodes_to_list(p::build_math_nodes(branch, after_node));
        },
        py::arg("branch"),
        py::arg("after_node") = false,
        "Build a flat tuple-tree from a TokensBranch. Each node:\n"
        "  (MATH_TAG_TEXT,  str)\n"
        "  (MATH_TAG_PAREN, ParenKind, has_close, list)\n"
        "  (MATH_TAG_LATEX, LatexKind, left_list, right_list)");

    // format_expr_str / token_text / tokens_to_text / space_binary_op

    m.def(
        "format_expr_str",
        &tcalc::parser::format_expr_str,
        py::arg("kind"),
        py::arg("left"),
        py::arg("right"),
        "Format a LaTeX expression string: \\\\symbol{left}{right}.");

    m.def(
        "token_text",
        &tcalc::parser::token_text,
        py::arg("token"),
        "Convert a single token to its display text representation.");

    m.def(
        "tokens_to_text",
        [](const std::vector<p::Token> &tokens, bool after_node) {
            return p::tokens_to_text(tokens, after_node);
        },
        py::arg("tokens"),
        py::arg("after_node") = false,
        "Convert a token list to display text with proper binary-op spacing.");

    m.def(
        "tokens_to_flat_text",
        &tcalc::parser::tokens_to_flat_text,
        py::arg("tokens"),
        "Convert tokens to flat display text — LaTeX expressions use op symbols.");

    m.def(
        "space_binary_op",
        &tcalc::parser::space_binary_op,
        py::arg("op_id"),
        py::arg("text"),
        py::arg("after_node") = false,
        "Format a single operator with binary-op spacing if applicable.");
}
