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
    using p::LatexKind;
    using p::LatexToken;
    using p::NumberToken;
    using p::OpToken;
    using p::ParenKind;
    using p::ParenToken;
    using p::ParenType;
    using p::Token;
    using p::TokenKind;
    using p::TokensBranch;
    using tcalc::ops::OpId;

    py::enum_<TokenKind>(m, "TokenKind", "Token categories produced by the native tokenizer.")
        .value("Number", TokenKind::Number)
        .value("Op", TokenKind::Op)
        .value("Paren", TokenKind::Paren)
        .value("Latex", TokenKind::Latex);

    py::enum_<LatexKind>(m, "LatexKind", "Expression kinds for compound Latex tokens.")
        .value("Frac", LatexKind::Frac)
        .value("Pow", LatexKind::Pow)
        .value("Root", LatexKind::Root)
        .value("Log", LatexKind::Log);

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
        .value("Ceil", OpId::Ceil)
        .value("Gcd", OpId::Gcd)
        .value("Lcm", OpId::Lcm);

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
        .def(
            py::init([](ParenType type, ParenKind kind) {
                return ParenToken{type, kind, tcalc::parser::kNoMatch};
            }),
            py::arg("type"),
            py::arg("kind"))
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

    // LatexToken — forward-declare, pickle added after Token
    py::class_<LatexToken> LatexToken_(m, "LatexToken");

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
                    }
                    return tok;
                }));

    py::class_<TokensBranch>(m, "TokensBranch", "Result of tokenization with metadata.")
        .def_readonly("tokens", &TokensBranch::tokens)
        .def_readonly("latex_indices", &TokensBranch::latex_indices)
        .def_readonly("open_paren_indices", &TokensBranch::open_paren_indices)
        .def_readonly("close_paren_indices", &TokensBranch::close_paren_indices)
        .def(
            py::pickle(
                [](const TokensBranch &r) {
                    return py::make_tuple(
                        r.tokens, r.latex_indices, r.open_paren_indices, r.close_paren_indices);
                },
                [](const py::tuple &t) {
                    if (t.size() != 4)
                        throw std::runtime_error("Invalid TokensBranch state");
                    TokensBranch r;
                    r.tokens = t[0].cast<std::vector<Token>>();
                    r.latex_indices = t[1].cast<std::vector<std::size_t>>();
                    r.open_paren_indices = t[2].cast<std::vector<std::size_t>>();
                    r.close_paren_indices = t[3].cast<std::vector<std::size_t>>();
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
        .def_property_readonly(
            "big_complex_supported",
            [](const tcalc::ops::OpSpec &op) { return tcalc::ops::big_complex_supported(op); })
        .def_property_readonly("rational_supported", [](const tcalc::ops::OpSpec &op) {
            return tcalc::ops::rational_supported(op);
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
    m.def("classify_tokens", &tcalc::parser::classify_tokens, py::arg("tokens"));
    m.def("shunting_yard", &tcalc::parser::shunting_yard, py::arg("tokens"));

    using p::ExprSplit;
    using p::ParenSplit;
    using p::StructuralSplit;
    using p::Token;

    const auto span_to_list = [](std::span<const Token> src) {
        py::list out;
        for (const Token &t : src) {
            out.append(py::cast(&t, py::return_value_policy::reference));
        }
        return out;
    };

    py::class_<ParenSplit>(m, "ParenSplit")
        .def_readonly("idx", &ParenSplit::idx)
        .def_readonly("open_tok", &ParenSplit::open_tok)
        .def_property_readonly(
            "close_tok",
            [](const ParenSplit &s) -> py::object {
                if (s.close_tok.has_value()) {
                    return py::cast(*s.close_tok);
                }
                return py::none();
            })
        .def_property_readonly("has_close", &ParenSplit::has_close)
        .def_property_readonly(
            "prefix", [span_to_list](const ParenSplit &s) { return span_to_list(s.prefix); })
        .def_property_readonly(
            "left", [span_to_list](const ParenSplit &s) { return span_to_list(s.left); })
        .def_property_readonly(
            "suffix", [span_to_list](const ParenSplit &s) { return span_to_list(s.suffix); });

    py::class_<ExprSplit>(m, "ExprSplit")
        .def_readonly("idx", &ExprSplit::idx)
        .def_readonly("kind", &ExprSplit::kind)
        .def_property_readonly(
            "prefix", [span_to_list](const ExprSplit &s) { return span_to_list(s.prefix); })
        .def_property_readonly(
            "left", [span_to_list](const ExprSplit &s) { return span_to_list(s.left); })
        .def_property_readonly(
            "right", [span_to_list](const ExprSplit &s) { return span_to_list(s.right); })
        .def_property_readonly(
            "suffix", [span_to_list](const ExprSplit &s) { return span_to_list(s.suffix); });

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
    using p::MathNodeKind;
    using p::ParenNode;
    using p::TextNode;

    py::enum_<MathNodeKind>(m, "MathNodeKind", "MathNode variant tag.")
        .value("Text", MathNodeKind::Text)
        .value("Paren", MathNodeKind::Paren)
        .value("Latex", MathNodeKind::Latex);

    // Forward-register MathNode so std::vector<MathNode> fields below render
    // as list[MathNode] in docstrings/stubs; accessors attached after leaves.
    py::class_<MathNode> MathNode_(
        m, "MathNode", "Render-tree element: text run, paren group, or latex expression.");

    py::class_<TextNode>(m, "TextNode", "Pre-formatted text run.")
        .def_readonly("text", &TextNode::text);

    auto ParenNode_ = py::class_<ParenNode>(m, "ParenNode", "Paren group with inner row.")
                          .def_readonly("kind", &ParenNode::kind)
                          .def_readonly("has_close", &ParenNode::has_close);
    def_readonly_ref(ParenNode_, "children", &ParenNode::children);

    auto LatexNode_ = py::class_<LatexNode>(m, "LatexNode", "Latex expression (frac/pow/root/log).")
                          .def_readonly("kind", &LatexNode::kind);
    def_readonly_ref(LatexNode_, "left", &LatexNode::left);
    def_readonly_ref(LatexNode_, "right", &LatexNode::right);

    MathNode_.def_property_readonly("kind", &MathNode::kind)
        .def("as_text", &math_as<TextNode>, py::return_value_policy::reference_internal)
        .def("as_paren", &math_as<ParenNode>, py::return_value_policy::reference_internal)
        .def("as_latex", &math_as<LatexNode>, py::return_value_policy::reference_internal);

    m.def(
        "build_math_nodes",
        &p::build_math_nodes,
        py::arg("branch"),
        py::arg("after_node") = false,
        "Build a flat row of MathNode descriptors from a TokensBranch — "
        "dispatch with node.kind and node.as_text()/as_paren()/as_latex().");

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
