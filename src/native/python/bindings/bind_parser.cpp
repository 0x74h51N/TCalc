/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/typing.h>

#include <string>

#include "bindings.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"

namespace py = pybind11;
namespace p = tcalc::parser;

void bind_parser(py::module_ &m) {
    using p::ExprKind;
    using p::ExprToken;
    using p::NumberToken;
    using p::OpToken;
    using p::ParenKind;
    using p::ParenToken;
    using p::ParenType;
    using p::Token;
    using p::TokenizeResult;
    using p::TokenKind;
    using tcalc::ops::OpId;

    py::enum_<TokenKind>(m, "TokenKind", "Token categories produced by the native tokenizer.")
        .value("Number", TokenKind::Number)
        .value("Op", TokenKind::Op)
        .value("Paren", TokenKind::Paren)
        .value("Expr", TokenKind::Expr);

    py::enum_<ExprKind>(m, "ExprKind", "Expression kinds for compound Expr tokens.")
        .value("Frac", ExprKind::Frac)
        .value("Pow", ExprKind::Pow)
        .value("Root", ExprKind::Root)
        .value("Log", ExprKind::Log);

    py::enum_<ParenType>(m, "ParenType")
        .value("Open", ParenType::Open)
        .value("Close", ParenType::Close);

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
        .value("Ceil", OpId::Ceil);

    py::class_<tcalc::parser::LatexEntry>(
        m, "LatexEntry", "LaTeX expression mapping: symbol -> ExprKind.")
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

    // ParenToken
    py::class_<ParenToken>(m, "ParenToken")
        .def_readonly("type", &ParenToken::type)
        .def_readonly("kind", &ParenToken::kind)
        .def_readonly("pair_idx", &ParenToken::pair_idx)
        .def_property_readonly(
            "symbol",
            [](const ParenToken &p) -> std::string {
                return std::string(1, tcalc::parser::paren_symbol(p.type, p.kind));
            })
        .def(
            py::pickle(
                [](const ParenToken &t) { return py::make_tuple(t.type, t.kind, t.pair_idx); },
                [](const py::tuple &t) {
                    if (t.size() != 3)
                        throw std::runtime_error("Invalid ParenToken state");
                    return ParenToken{
                        t[0].cast<ParenType>(), t[1].cast<ParenKind>(), t[2].cast<std::size_t>()};
                }));

    // ExprToken — forward-declare, pickle added after Token
    py::class_<ExprToken> ExprToken_(m, "ExprToken");

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

        .def("as_expr", &token_as<ExprToken>, py::return_value_policy::reference_internal)

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
                    case TokenKind::Expr:
                        tok.data = t[1].cast<ExprToken>();
                        break;
                    }
                    return tok;
                }));

    // ExprToken — properties + pickle (after Token so recursive list[Token] resolves)
    ExprToken_.def_readonly("kind", &ExprToken::kind);
    def_readonly_ref(ExprToken_, "left", &ExprToken::left);
    def_readonly_ref(ExprToken_, "right", &ExprToken::right);
    ExprToken_.def(
        py::pickle(
            [](const ExprToken &t) { return py::make_tuple(t.kind, t.left, t.right); },
            [](const py::tuple &t) {
                if (t.size() != 3)
                    throw std::runtime_error("Invalid ExprToken state");
                return ExprToken{
                    t[0].cast<ExprKind>(),
                    t[1].cast<std::vector<Token>>(),
                    t[2].cast<std::vector<Token>>()};
            }));

    py::class_<TokenizeResult>(m, "TokenizeResult", "Result of tokenization with metadata.")
        .def_readonly("tokens", &TokenizeResult::tokens)
        .def_readonly("expr_indices", &TokenizeResult::expr_indices)
        .def_readonly("open_paren_indices", &TokenizeResult::open_paren_indices)
        .def_readonly("close_paren_indices", &TokenizeResult::close_paren_indices)
        .def(
            py::pickle(
                [](const TokenizeResult &r) {
                    return py::make_tuple(
                        r.tokens, r.expr_indices, r.open_paren_indices, r.close_paren_indices);
                },
                [](const py::tuple &t) {
                    if (t.size() != 4)
                        throw std::runtime_error("Invalid TokenizeResult state");
                    TokenizeResult r;
                    r.tokens = t[0].cast<std::vector<Token>>();
                    r.expr_indices = t[1].cast<std::vector<std::size_t>>();
                    r.open_paren_indices = t[2].cast<std::vector<std::size_t>>();
                    r.close_paren_indices = t[3].cast<std::vector<std::size_t>>();
                    return r;
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
        .def_property_readonly(
            "angle_unit",
            [](const tcalc::ops::OpSpec &op) { return tcalc::ops::needs_angle_unit(op); })
        .def_property_readonly(
            "big_supported",
            [](const tcalc::ops::OpSpec &op) { return tcalc::ops::big_supported(op); })
        .def_property_readonly("big_complex_supported", [](const tcalc::ops::OpSpec &op) {
            return tcalc::ops::big_complex_supported(op);
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

    m.def(
        "paren_table",
        []() -> py::list {
            py::list out;
            for (std::size_t i = 0; i < p::kParenTable.size(); ++i) {
                if (const auto &entry = p::kParenTable[i]) {
                    out.append(
                        py::make_tuple(
                            std::string(1, static_cast<char>(i)), entry->type, entry->kind));
                }
            }
            return out;
        },
        "Return the native paren table as a list of (symbol, ParenType, ParenKind) tuples.");

    m.attr("PAREN_NO_MATCH") = tcalc::parser::kNoMatch;

    m.def("tokenize_string", &tcalc::parser::tokenize, py::arg("expression"));
    m.def("shunting_yard", &tcalc::parser::shunting_yard, py::arg("tokens"));
    m.def(
        "classify_tokens",
        &tcalc::parser::classify_tokens,
        py::arg("tokens"),
        "Classify a token list into a TokenizeResult with expr/paren indices. "
        "Recomputes local paren pairs without re-tokenizing the source text.");

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
        &tcalc::parser::tokens_to_text,
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
