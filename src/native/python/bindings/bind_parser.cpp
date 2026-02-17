#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

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

    py::class_<tcalc::parser::Paren>(m, "Paren")
        .def_readonly("symbol", &tcalc::parser::Paren::symbol)
        .def_readonly("type", &tcalc::parser::Paren::type)
        .def_readonly("kind", &tcalc::parser::Paren::kind);

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

    m.def(
        "parentheses",
        []() {
            py::list out;
            for (auto &p : tcalc::parser::kParens) {
                out.append(&p);
            }
            return out;
        },
        "Return list of native Paren objects",
        py::return_value_policy::reference);

    // NumberToken
    py::class_<NumberToken>(m, "NumberToken").def_readonly("value", &NumberToken::value);

    // OpToken
    py::class_<OpToken>(m, "OpToken").def_readonly("op_id", &OpToken::op_id);

    // ParenToken
    py::class_<ParenToken>(m, "ParenToken")
        .def_readonly("type", &ParenToken::type)
        .def_readonly("kind", &ParenToken::kind)
        .def_property_readonly("symbol", [](const ParenToken &p) -> std::string {
            for (auto &paren : tcalc::parser::kParens) {
                if (paren.type == p.type && paren.kind == p.kind)
                    return std::string(paren.symbol);
            }
            return "";
        });

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

        .def_property_readonly("symbol", [](const Token &tok) -> std::string {
            if (auto p = token_as<OpToken>(tok)) {
                const auto *spec = tcalc::ops::op_spec(p->op_id);
                return spec ? std::string(spec->symbol) : "";
            }
            return "";
        });

    // ExprToken
    ExprToken_.def_readonly("kind", &ExprToken::kind);
    def_readonly_ref(ExprToken_, "left", &ExprToken::left);
    def_readonly_ref(ExprToken_, "right", &ExprToken::right);

    py::class_<TokenizeResult>(m, "TokenizeResult", "Result of tokenization with metadata.")
        .def_readonly("tokens", &TokenizeResult::tokens)
        .def_readonly("expr_indices", &TokenizeResult::expr_indices);

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
        []() {
            py::list out;
            for (const auto &op : tcalc::ops::kOps) {
                out.append(&op);
            }
            return out;
        },
        "Return list of OpSpec objects from the native operation table.",
        py::return_value_policy::reference);

    m.def("tokenize_string", &tcalc::parser::tokenize, py::arg("expression"));
    m.def("shunting_yard", &tcalc::parser::shunting_yard, py::arg("tokens"));
}
