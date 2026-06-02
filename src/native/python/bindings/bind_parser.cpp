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
        .value("Latex", TokenKind::Latex)
        .value("Collection", TokenKind::Collection);

    py::enum_<p::CollectionKind>(
        m, "CollectionKind", "Bracket kind for CollectionToken: List ([...]) or Point ((...)).")
        .value("List", p::CollectionKind::List)
        .value("Point", p::CollectionKind::Point);

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
                        t[0].cast<ParenType>(),
                        t[1].cast<ParenKind>(),
                        t[2].cast<tcalc::parser::TokenIndex>()};
                }));

    // LatexToken — forward-declare, pickle added after Token
    py::class_<LatexToken> LatexToken_(m, "LatexToken");

    // CollectionToken — forward-declare, properties added after Token/TokensBranch
    py::class_<p::CollectionToken> CollectionToken_(
        m,
        "CollectionToken",
        "Tokenized collection ([...] List or (...) Point) with per-element token rows.");

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

        .def(
            "as_collection",
            &token_as<p::CollectionToken>,
            py::return_value_policy::reference_internal)

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
                    case TokenKind::Collection:
                        tok.data = t[1].cast<p::CollectionToken>();
                        break;
                    }
                    return tok;
                }));

    py::class_<TokensBranch>(m, "TokensBranch", "Result of tokenization with metadata.")
        .def_readonly("tokens", &TokensBranch::tokens)
        .def_readonly("latex_indices", &TokensBranch::latex_indices)
        .def_readonly("open_paren_indices", &TokensBranch::open_paren_indices)
        .def_readonly("close_paren_indices", &TokensBranch::close_paren_indices)
        .def_readonly("collection_indices", &TokensBranch::collection_indices)
        .def(
            py::pickle(
                [](const TokensBranch &r) {
                    return py::make_tuple(
                        r.tokens,
                        r.latex_indices,
                        r.open_paren_indices,
                        r.close_paren_indices,
                        r.collection_indices);
                },
                [](const py::tuple &t) {
                    constexpr std::size_t kTokensBranchPickleArity = 5;
                    if (t.size() != kTokensBranchPickleArity)
                        throw std::runtime_error("Invalid TokensBranch state");
                    TokensBranch r;
                    r.tokens = t[0].cast<std::vector<Token>>();
                    r.latex_indices = t[1].cast<std::vector<tcalc::parser::TokenIndex>>();
                    r.open_paren_indices = t[2].cast<std::vector<tcalc::parser::TokenIndex>>();
                    r.close_paren_indices = t[3].cast<std::vector<tcalc::parser::TokenIndex>>();
                    r.collection_indices = t[4].cast<std::vector<tcalc::parser::TokenIndex>>();
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

    // CollectionToken — properties + pickle
    CollectionToken_.def_readonly("kind", &p::CollectionToken::kind);
    CollectionToken_.def_readonly("closed", &p::CollectionToken::closed);
    def_readonly_ref(CollectionToken_, "elements", &p::CollectionToken::elements);
    CollectionToken_.def("rows", [](const p::CollectionToken &c) {
        py::list out;
        for (const auto &e : c.elements) {
            py::list row;
            if (e.index() == 0) {
                row.append(std::get<p::Token>(e));
            } else {
                for (const auto &t : std::get<std::vector<p::Token>>(e)) {
                    row.append(t);
                }
            }
            out.append(row);
        }
        return out;
    });
    CollectionToken_.def(
        py::pickle(
            [](const p::CollectionToken &t) {
                return py::make_tuple(t.kind, t.elements, t.closed);
            },
            [](const py::tuple &t) {
                constexpr std::size_t kCollectionTokenPickleArity = 3;
                if (t.size() != kCollectionTokenPickleArity)
                    throw std::runtime_error("Invalid CollectionToken state");
                // Manually iterate elements to avoid pybind11 default-constructing
                // a type_caster<variant<Token, vector<Token>>>
                std::vector<p::CollectionElement> elements;
                for (auto h : t[1]) {
                    auto obj = py::reinterpret_borrow<py::object>(h);
                    if (py::isinstance<p::Token>(obj)) {
                        elements.emplace_back(obj.cast<p::Token>());
                    } else {
                        elements.emplace_back(obj.cast<std::vector<p::Token>>());
                    }
                }
                return p::CollectionToken{
                    t[0].cast<p::CollectionKind>(), std::move(elements), t[2].cast<bool>()};
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

    using p::LatexSplit;
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
