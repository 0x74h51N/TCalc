#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <string>

#include "bindings.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"

namespace py = pybind11;

void bind_parser(py::module_ &m) {
    using tcalc::ops::OpId;
    using tcalc::parser::Token;
    using tcalc::parser::TokenKind;

    py::enum_<TokenKind>(m, "TokenKind", "Token categories produced by the native tokenizer.")
        .value("Number", TokenKind::Number)
        .value("Op", TokenKind::Op)
        .value("LParen", TokenKind::LParen)
        .value("RParen", TokenKind::RParen);

    py::enum_<OpId>(
        m, "OpId", "Operation identifiers used by tokens and op_table; maps to engine methods.")
        .value("Add", OpId::Add)
        .value("Sub", OpId::Sub)
        .value("Mul", OpId::Mul)
        .value("Div", OpId::Div)
        .value("Pow", OpId::Pow)
        .value("Percent", OpId::Percent)
        .value("Negate", OpId::Negate)
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

    py::class_<Token>(
        m, "Token", "Parser token. 'value' is text for numbers; 'symbol' is only for ops.")
        .def_readonly("kind", &Token::kind)
        .def_readonly("op_id", &Token::op_id)
        .def_readonly("value", &Token::value)
        .def_property_readonly("symbol", [](const Token &tok) {
            if (tok.kind != TokenKind::Op) {
                return std::string();
            }
            const auto *spec = tcalc::ops::op_spec(tok.op_id);
            return spec ? std::string(spec->symbol) : std::string();
        });

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
