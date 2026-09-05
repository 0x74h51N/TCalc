#include <functional>
#include <string>
#include <string_view>
#include <vector>

#include "eval/pub/eval.hpp"
#include "internal/parser_internal.hpp"
#include "internal/test_helpers.hpp"
#include "internal/token_factories.hpp"
#include "parser/pub/consts.hpp"
#include "parser/pub/ops.hpp"
#include "parser/pub/parser.hpp"

namespace p = tcalc::parser;
namespace o = tcalc::ops;
namespace d = p::detail;

using o::OpId;
using p::CallToken;
using p::CharToken;
using p::ConstToken;
using p::LatexKind;
using p::LatexToken;
using p::NumberToken;
using p::OpToken;
using p::ParenElement;
using p::ParenKind;
using p::ParenToken;
using p::StructuralSplit;
using p::Token;
using p::TokenKind;
using p::TokensBranch;

namespace {

/// Generic test-row template: id label, input value, expected value.
template <typename InputT, typename ExpectedT> struct Case {
    const char *id;
    InputT input;
    ExpectedT expected;
};

/// scan_number input pair: source text and start offset.
struct ScanInput {
    std::string_view text;
    std::size_t start;
};

/// scan_number expected output: matched view and post-scan cursor position.
struct ScanExpected {
    std::string_view view;
    std::size_t next;
};

/// structural_split expected output: discriminator + per-variant fields.
/// Paren: kind + has_open + has_close + elements (flat vec<vec<Token>>) + prefix/suffix.
/// Latex: latex_kind + left + right + prefix/suffix.
struct SplitExpected {
    enum class Kind { None, Paren, Latex };
    Kind kind = Kind::None;
    std::vector<Token> prefix;
    std::vector<Token> left;
    std::vector<Token> right;
    ParenKind paren_kind{};
    bool has_open = true;
    bool has_close = true;
    std::vector<std::vector<Token>> elements;
    std::vector<Token> suffix;
    p::LatexKind latex_kind{};
};

/// Case row for tokenize: raw source string -> expected token vector.
using TokCase = Case<const char *, std::vector<tcalc::parser::Token>>;
/// Case row for scan_number: ScanInput -> ScanExpected.
using ScanCase = Case<ScanInput, ScanExpected>;
/// Case row for normalize: input tokens -> normalized tokens.
using NormCase = Case<std::vector<Token>, std::vector<Token>>;
/// Case row for shunting_yard: infix tokens -> RPN tokens.
using ShuntCase = Case<std::vector<Token>, std::vector<Token>>;
/// Case row for structural_split: classified TokensBranch -> SplitExpected.
using SplitCase = Case<TokensBranch, SplitExpected>;

/// classify_tokens expected output: re-derived index vectors + has_latex_descendant.
struct ClassifyExpected {
    std::vector<p::TokenIndex> latex_indices;
    std::vector<p::TokenIndex> paren_indices;
    bool has_latex_descendant = false;
};

/// Case row for classify_tokens: raw token list -> ClassifyExpected.
using ClassifyCase = Case<std::vector<Token>, ClassifyExpected>;

/// tokenize position-tracking expected output: token count, latex indices, and
/// (token_idx, start_pos, end_pos) tuples for the indices we want to assert.
struct PositionExpected {
    std::size_t token_count;
    std::vector<p::TokenIndex> latex_indices;
    std::vector<std::tuple<p::TokenIndex, std::size_t, std::size_t>> positions;
};

/// Case row for tokenize position tests: source string -> PositionExpected.
using PositionCase = Case<const char *, PositionExpected>;

// Token factories. start/end default to 0
// pass them only when the test actually checks span info

// Token builders N / Op_ / Ch / Co / EN / EC / EV / Pr / Pp / Br / Bc are shared with
// the evaluator suite.
using namespace tcalc::test_tokens;
/// Token factory: CallToken (function call `f(arg0, arg1, ...)`).
inline Token
Cl(OpId op_id,
   std::vector<ParenElement> args,
   bool has_close = true,
   std::size_t start = 0,
   std::size_t end = 0) {
    return Token{TokenKind::Call, CallToken{op_id, std::move(args), has_close}, start, end};
}
/// Shorthand: stray close ParenToken (no open, has_close=true, empty elements).
inline Token StrayC(ParenKind kind) {
    return Token{
        TokenKind::Paren,
        ParenToken{
            kind,
            /*elements=*/{},
            /*has_open=*/false,
            /*has_close=*/true,
            /*has_latex_descendant=*/false},
        0,
        0};
}
/// Token factory: LatexToken of arbitrary kind/op with explicit left/right token rows.
inline Token
Lx(p::LatexKind kind,
   OpId op,
   std::vector<Token> left,
   std::vector<Token> right,
   std::size_t start = 0,
   std::size_t end = 0) {
    return Token{
        TokenKind::Latex, LatexToken{kind, op, std::move(left), std::move(right)}, start, end};
}
/// Token factory shorthand: \frac LatexToken (numerator, denominator).
inline Token Frac(
    std::vector<Token> numerator,
    std::vector<Token> denominator,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(
        p::LatexKind::Frac, OpId::Div, std::move(numerator), std::move(denominator), start, end);
}
/// Token factory shorthand: \pow / `^{}` LatexToken (base, exponent).
inline Token
Pow(std::vector<Token> base,
    std::vector<Token> exponent,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(p::LatexKind::Pow, OpId::Pow, std::move(base), std::move(exponent), start, end);
}
/// Token factory shorthand: \root LatexToken (radicand, degree).
inline Token Root(
    std::vector<Token> degree,
    std::vector<Token> radicand,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(p::LatexKind::Root, OpId::Root, std::move(degree), std::move(radicand), start, end);
}
/// Token factory shorthand: `_{}` LatexToken (base, subscript).
inline Token
Sub(std::vector<Token> base, std::vector<Token> sub, std::size_t start = 0, std::size_t end = 0) {
    return Lx(p::LatexKind::Subscript, OpId::Count, std::move(base), std::move(sub), start, end);
}
/// Token factory shorthand: \sum LatexToken (lower limit, upper limit).
inline Token
Sum(std::vector<Token> lower,
    std::vector<Token> upper,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(p::LatexKind::Sum, OpId::Count, std::move(lower), std::move(upper), start, end);
}
/// Token factory shorthand: \prod LatexToken (lower limit, upper limit).
inline Token Prod(
    std::vector<Token> lower,
    std::vector<Token> upper,
    std::size_t start = 0,
    std::size_t end = 0) {
    return Lx(p::LatexKind::Prod, OpId::Count, std::move(lower), std::move(upper), start, end);
}

/// Shorthand for tcalc::parser::ParenKind.
using PK = p::ParenKind;
/// Shorthand for tcalc::parser::LatexKind.
using LK = p::LatexKind;
/// Shorthand for tcalc::parser::MathNode.
using MN = p::MathNode;

/// MathNode factory: TextNode (plain text run).
inline MN T_(std::string s) {
    return MN{p::TextNode{std::move(s)}};
}
/// MathNode factory: ParenNode (paren/brace/bracket group, has_close=closed paren).
inline MN Pn(PK k, bool hc, std::vector<MN> ch) {
    return MN{p::ParenNode{k, hc, std::move(ch)}};
}
/// MathNode factory: LatexNode of arbitrary kind (frac/pow/root/log).
inline MN Ln(LK k, std::vector<MN> l, std::vector<MN> r) {
    return MN{p::LatexNode{k, std::move(l), std::move(r)}};
}
/// MathNode factory shorthand: Frac LatexNode (numerator l, denominator r).
inline MN Frn(std::vector<MN> l, std::vector<MN> r) {
    return Ln(LK::Frac, std::move(l), std::move(r));
}
/// MathNode factory shorthand: Pow LatexNode (base l, exponent r).
inline MN Pwn(std::vector<MN> l, std::vector<MN> r) {
    return Ln(LK::Pow, std::move(l), std::move(r));
}
/// MathNode factory shorthand: Root LatexNode (radicand l, degree r).
inline MN Rtn(std::vector<MN> l, std::vector<MN> r) {
    return Ln(LK::Root, std::move(l), std::move(r));
}

/// Case row for build_math_nodes: pre-classified TokensBranch -> expected node row.
using BuildNodesCase = Case<TokensBranch, std::vector<MN>>;
} // namespace

void unit_parser(TestContext &ctx) {

    // =========================================================================
    // Tokenizations
    // =========================================================================
    const std::vector<TokCase> tok_cases = {
        {.id = "basic add",
         .input = "1+2",
         .expected = {N("1", 0, 1), Op_(OpId::Add, 1, 2), N("2", 2, 3)}},

        {.id = "leading negate decimal",
         .input = "-3.5",
         .expected = {Op_(OpId::Negate, 0, 1), N("3.5", 1, 4)}},

        {.id = "negate then plus",
         .input = "-+2",
         .expected = {Op_(OpId::Negate, 0, 1), Op_(OpId::UnaryPlus, 1, 2), N("2", 2, 3)}},

        {.id = "func parens imag",
         .input = "sin(2i)",
         .expected = {Cl(OpId::Sin, {EN("2i")}, true, 0, 7)}},

        {.id = "spacing and unicode",
         .input = "-2 ³√( 3 ( π ",
         .expected =
             {Op_(OpId::Negate, 0, 1),
              N("2", 1, 2),
              Cl(OpId::Cbrt,
                 {EV({N("3"), Pp({EC(tcalc::consts::ConstId::Pi)}, false)})},
                 false,
                 3,
                 13)}},

        {.id = "sci notation imag", .input = "1.2e-3i", .expected = {N("1.2e-3i", 0, 7)}},

        {.id = "binary plus unary minus",
         .input = "1+-2",
         .expected = {N("1", 0, 1), Op_(OpId::Add, 1, 2), Op_(OpId::Negate, 2, 3), N("2", 3, 4)}},

        {.id = "negate in parens",
         .input = "(-2)",
         .expected = {Pp({EV({Op_(OpId::Negate), N("2")})})}},

        {.id = "asinh parens",
         .input = "asinh(2)",
         .expected = {Cl(OpId::Asinh, {EN("2")}, true, 0, 8)}},

        {.id = "sqrt parens",
         .input = "sqrt(2)",
         .expected = {Cl(OpId::Sqrt, {EN("2")}, true, 0, 7)}},

        {.id = "postfix unicode", .input = "2³", .expected = {N("2", 0, 1), Op_(OpId::Cube, 1, 2)}},

        // == Paren types ==============================================

        {.id = "curly braces",
         .input = "{1+2}",
         .expected = {Pr(
             ParenKind::Brace,
             {EV({N("1", 1, 2), Op_(OpId::Add, 2, 3), N("2", 3, 4)})},
             /*has_open=*/true,
             /*has_close=*/true,
             0,
             5)}},

        {.id = "square brackets",
         .input = "[3+4]",
         .expected = {Br({EV({N("3"), Op_(OpId::Add), N("4")})})}},

        {.id = "mixed paren kinds", .input = "({[1]})", .expected = {Pp({Bc({Br({EN("1")})})})}},

        {.id = "negate inside curly",
         .input = "{-2}",
         .expected = {Pr(
             ParenKind::Brace,
             {EV({Op_(OpId::Negate, 1, 2), N("2", 2, 3)})},
             /*has_open=*/true,
             /*has_close=*/true,
             0,
             4)}},

        // == LatexToken (LaTeX) ========================================

        {.id = "frac simple",
         .input = "\\frac{2}{3}",
         .expected = {Frac({N("2")}, {N("3")}, 0, 11)}},

        {.id = "pow simple", .input = "5^{2}", .expected = {Pow({N("5")}, {N("2")}, 0, 10)}},

        {.id = "root simple",
         .input = "\\root{8}{3}",
         .expected = {Root({N("8")}, {N("3")}, 0, 11)}},

        // `log` has no latex spelling: it matches the op table, and the script after it folds
        // onto it the way a script folds onto a name, because a logarithm's script is the base
        // it is taken in. fold_script skips every other operator, so a script over anything
        // else stays that name's index, which is what keeps `log y_{2}` a log of a variable.
        {.id = "log_{2}8 folds the op into the script",
         .input = "log_{2}8",
         .expected = {Sub({Op_(OpId::Log)}, {N("2")}), N("8")}},
        {.id = "log8 carries no script", .input = "log8", .expected = {Op_(OpId::Log), N("8")}},
        {.id = "log y_{2} leaves the script on the name",
         .input = "log y_{2}",
         .expected = {Op_(OpId::Log), Sub({Ch('y')}, {N("2")})}},

        {.id = "pow caret simple", .input = "2^{3}", .expected = {Pow({N("2")}, {N("3")}, 0, 5)}},
        {.id = "pow caret paren base",
         .input = "(2+5)^{4}",
         .expected = {Pow({Pp({EV({N("2"), Op_(OpId::Add), N("5")})})}, {N("4")})}},
        {.id = "pow caret prefix",
         .input = "1+2^{3}",
         .expected = {N("1"), Op_(OpId::Add), Pow({N("2")}, {N("3")})}},
        {.id = "pow caret nested",
         .input = "2^{3^{2}}",
         .expected = {Pow({N("2")}, {Pow({N("3")}, {N("2")})})}},
        {.id = "pow caret flat chain",
         .input = "2^{3}^{2}",
         .expected = {Pow({Pow({N("2")}, {N("3")})}, {N("2")})}},
        {.id = "pow caret bare no base", .input = "^3", .expected = {Pow({}, {}), N("3")}},
        // No preceding operand: `^{}` still folds, with an empty base (an empty
        // PowWidget placeholder), not a bare Op(Pow) + brace group.
        {.id = "pow caret empty base", .input = "^{3}", .expected = {Pow({}, {N("3")})}},
        {.id = "pow caret empty base and exp", .input = "^{}", .expected = {Pow({}, {})}},
        // Live typing: an unclosed '{' must NOT hang the tokenizer (regression —
        // extract_brace_content once left out_end unset → tokenize looped forever).
        // The unclosed brace is swallowed: content runs to end, end_pos = input len.
        {.id = "pow caret unclosed empty", .input = "a^{", .expected = {Pow({Ch('a')}, {}, 0, 3)}},
        {.id = "pow caret unclosed exp",
         .input = "2^{3",
         .expected = {Pow({N("2")}, {N("3")}, 0, 4)}},

        // Note: base uses 'y', not 'x' — 'x' is a reserved multiplication-symbol
        // operator (see ops.hpp), so "x_{2}" tokenizes as Op(Mul) + free text,
        // not as a Char('x') operand for the fold. 'y' has no such collision.
        {.id = "subscript var", .input = "y_{2}", .expected = {Sub({Ch('y')}, {N("2")}, 0, 5)}},
        {.id = "subscript then letter",
         .input = "a_{2}b",
         .expected = {Sub({Ch('a')}, {N("2")}), Ch('b')}},
        {.id = "subscript on number folds",
         .input = "2_{3}",
         .expected = {Sub({N("2")}, {N("3")})}},
        // Bare '_' folds like bare '^': an empty-script Subscript on the preceding
        // operand (an empty placeholder the UI fills in), not inert free text.
        {.id = "bare underscore folds empty",
         .input = "a_b",
         .expected = {Sub({Ch('a')}, {}), Ch('b')}},
        {.id = "subscript empty base", .input = "_{2}", .expected = {Sub({}, {N("2")})}},
        // Live typing: unclosed '_{' must not hang either; brace swallowed to end.
        {.id = "subscript unclosed empty", .input = "a_{", .expected = {Sub({Ch('a')}, {}, 0, 3)}},
        {.id = "subscript unclosed content",
         .input = "y_{2",
         .expected = {Sub({Ch('y')}, {N("2")}, 0, 4)}},

        {.id = "sum carries only its limits",
         .input = "\\sum_{n=1}^{5} n^{2}",
         .expected =
             {Sum({Ch('n'), Op_(OpId::Assign), N("1")}, {N("5")}), Pow({Ch('n')}, {N("2")})}},
        {.id = "sum reverse script order",
         .input = "\\sum^{5}_{n=1} n",
         .expected = {Sum({Ch('n'), Op_(OpId::Assign), N("1")}, {N("5")}), Ch('n')}},
        {.id = "sum body stays outside the token",
         .input = "2 + \\sum_{n=1}^{3} 2n+5",
         .expected =
             {N("2"),
              Op_(OpId::Add),
              Sum({Ch('n'), Op_(OpId::Assign), N("1")}, {N("3")}),
              N("2"),
              Ch('n'),
              Op_(OpId::Add),
              N("5")}},
        {.id = "sum missing upper limit leaves right empty",
         .input = "\\sum_{n=1}^{}",
         .expected = {Sum({Ch('n'), Op_(OpId::Assign), N("1")}, {})}},
        {.id = "sum mid-typing (no upper script) leaves right empty",
         .input = "\\sum_{n=1}",
         .expected = {Sum({Ch('n'), Op_(OpId::Assign), N("1")}, {})}},
        // Note: bound var uses 'm', not 'k' — 'k' is the reserved Boltzmann-constant
        // symbol (see consts.hpp), so "k=1" would tokenize 'k' as a ConstToken, not a
        // Char('k') operand. 'm' has no such collision.
        {.id = "prod carries only its limits",
         .input = "\\prod_{m=1}^{5} m",
         .expected = {Prod({Ch('m'), Op_(OpId::Assign), N("1")}, {N("5")}), Ch('m')}},

        {.id = "frac with inner expr",
         .input = "\\frac{2+3}{4}",
         .expected = {Frac({N("2"), Op_(OpId::Add), N("3")}, {N("4")}, 0, 13)}},

        {.id = "frac nested in frac",
         .input = "\\frac{\\frac{1}{2}}{3}",
         .expected = {Frac({Frac({N("1")}, {N("2")})}, {N("3")}, 0, 21)}},

        {.id = "frac with pow inside",
         .input = "\\frac{4^{2}}{3}",
         .expected = {Frac({Pow({N("4")}, {N("2")})}, {N("3")}, 0, 20)}},

        // == Mixed: plain tokens + LatexToken ==========================

        {.id = "number then frac",
         .input = "1+\\frac{2}{3}",
         .expected = {N("1", 0, 1), Op_(OpId::Add, 1, 2), Frac({N("2")}, {N("3")}, 2, 13)}},

        {.id = "frac between numbers",
         .input = "1+\\frac{2}{3}+4",
         .expected =
             {N("1", 0, 1),
              Op_(OpId::Add, 1, 2),
              Frac({N("2")}, {N("3")}, 2, 13),
              Op_(OpId::Add, 13, 14),
              N("4", 14, 15)}},

        // == User curly braces inside LaTeX args ======================

        {.id = "user brace inside frac numerator",
         .input = "\\frac{{1+2}}{3}",
         .expected = {Frac({Bc({EV({N("1"), Op_(OpId::Add), N("2")})})}, {N("3")}, 0, 15)}},

        {.id = "user brace around frac",
         .input = "{\\frac{1}{2}}",
         .expected = {Pr(
             ParenKind::Brace,
             {Frac({N("1")}, {N("2")}, 1, 12)},
             /*has_open=*/true,
             /*has_close=*/true,
             0,
             13)}},
        {.id = "non closed brace around frac",
         .input = "{\\frac{1}{2})",
         .expected =
             {Pr(ParenKind::Brace,
                 {Frac({N("1")}, {N("2")}, 1, 12)},
                 /*has_open=*/true,
                 /*has_close=*/false,
                 0,
                 13),
              Pr(ParenKind::Paren,
                 {},
                 /*has_open=*/false,
                 /*has_close=*/true,
                 13,
                 14)}},
        {.id = "complex nested: frac with user brace and inner pow",
         .input = "\\frac{{4^{2}}}{3}",
         .expected = {Frac({Bc({Pow({N("4")}, {N("2")})})}, {N("3")}, 0, 22)}},

        {.id = "curly brace then number plain",
         .input = "2{3+4}+5",
         .expected =
             {N("2", 0, 1),
              Pr(ParenKind::Brace,
                 {EV({N("3", 2, 3), Op_(OpId::Add, 3, 4), N("4", 4, 5)})},
                 /*has_open=*/true,
                 /*has_close=*/true,
                 1,
                 6),
              Op_(OpId::Add, 6, 7),
              N("5", 7, 8)}},

        {"paren_grouping_is_point_arity1", "(1+2)", {Pp({EV({N("1"), Op_(OpId::Add), N("2")})})}},

        // -----------------------------------------------------------------
        // Paren collection tokenization (lists, points)
        // -----------------------------------------------------------------

        // List: top-level comma in `[...]`
        {.id = "collection :: list 3 nums",
         .input = "[1, 2, 3]",
         .expected = {Br({EN("1"), EN("2"), EN("3")})}},

        {"collection :: list trailing comma kept", "[1,]", {Br({EN("1"), EV({})})}},

        {"collection :: list unclosed full",
         "[1, 2, 3",
         {Br({EN("1"), EN("2"), EN("3")}, /*closed=*/false)}},

        {"collection :: list unclosed trailing comma",
         "[1, 2, ",
         {Br({EN("1"), EN("2"), EV({})}, false)}},

        {"collection :: list with expression element",
         "[2+3, 4*5]",
         {Br({EV({N("2"), Op_(OpId::Add), N("3")}), EV({N("4"), Op_(OpId::Mul), N("5")})})}},

        {"collection :: list with latex element",
         "[\\frac{1}{2}, 3]",
         {Br({Frac({N("1")}, {N("2")}), EN("3")})}},

        {"collection :: list with scalar suffix",
         "[2,5] + 4",
         {Br({EN("2"), EN("5")}), Op_(OpId::Add), N("4")}},

        // List(1) promotion: `[X]` with no comma, X reduces to a NumberToken
        // after stripping leading unary +/-.
        {"collection :: list of single number", "[2]", {Br({EN("2")})}},

        {"collection :: list of negated number", "[-5]", {Br({EV({Op_(OpId::Negate), N("5")})})}},

        {"collection :: list of unary-plus number",
         "[+3]",
         {Br({EV({Op_(OpId::UnaryPlus), N("3")})})}},

        // `[X]` single-element list cases (no fall-through under unconditional model).
        {"collection :: list with expression single element",
         "[2+3]",
         {Br({EV({N("2"), Op_(OpId::Add), N("3")})})}},

        {"collection :: list with latex single element",
         "[\\frac{1}{2}]",
         {Br({Frac({N("1")}, {N("2")})})}},

        {"collection :: list with point arity-1 element",
         "[(1+2)]",
         {Br({Pp({EV({N("1"), Op_(OpId::Add), N("2")})})})}},

        {.id = "collection :: empty list", .input = "[]", .expected = {Br({})}},

        // Empty paren / brace — symmetric to empty list.
        {.id = "collection :: empty paren", .input = "()", .expected = {Pp({})}},

        {.id = "collection :: empty brace", .input = "{}", .expected = {Bc({})}},

        // Kind-strict mismatch: ']' doesn't match '(' so scan stops; outer Paren
        // is unclosed and ']' surfaces as stray close at top level.
        {.id = "mismatched close kind: ( ... ]",
         .input = "(2+4]",
         .expected =
             {Pp({EV({N("2"), Op_(OpId::Add), N("4")})}, /*has_close=*/false),
              StrayC(ParenKind::Bracket)}},

        // A stray close acts as an operand for the operator that follows it:
        // the next '+' must be binary Add, not UnaryPlus. Regression guard for
        // the _try_close_paren dissolve flow (binary op spacing).
        {.id = "stray close followed by + is binary Add",
         .input = "5)+3",
         .expected = {N("5"), StrayC(ParenKind::Paren), Op_(OpId::Add), N("3")}},

        // A close paren whose innermost open is the wrong kind still closes a
        // matching open deeper in the stack; intervening unmatched opens are
        // recovered as unclosed groups inside.
        {.id = "outer brace closes over inner unclosed paren",
         .input = "{1+(2+3}",
         .expected = {Bc({EV(
             {N("1"),
              Op_(OpId::Add),
              Pp({EV({N("2"), Op_(OpId::Add), N("3")})}, /*has_close=*/false)})})}},

        {.id = "outer brace closes over inner unclosed paren with frac",
         .input = "{1 + (2 + \\frac{3}{4} + 4 +5}",
         .expected = {Bc({EV(
             {N("1"),
              Op_(OpId::Add),
              Pp({EV(
                     {N("2"),
                      Op_(OpId::Add),
                      Frac({N("3")}, {N("4")}),
                      Op_(OpId::Add),
                      N("4"),
                      Op_(OpId::Add),
                      N("5")})},
                 /*has_close=*/false)})})}},

        // Point: `(X, Y, ...)` with top-level comma.
        {"collection :: point arity 2", "(1, 2)", {Pp({EN("1"), EN("2")})}},

        {"collection :: point arity 3", "(1, 2, 3)", {Pp({EN("1"), EN("2"), EN("3")})}},

        {"collection :: point unclosed", "(1, 2", {Pp({EN("1"), EN("2")}, false)}},

        {"collection :: point arity 1 closed (eval rejects)", "(1,)", {Pp({EN("1"), EV({})})}},

        // Paren grouping unchanged: `(X)` no comma stays as paren tokens.
        {"collection :: nested point in list",
         "[(1, 2), (3, 4)]",
         {Br({Pp({EN("1"), EN("2")}), Pp({EN("3"), EN("4")})})}},

        /// TODO: Add more latex and paren tokenize edge cases

        // == Const and Char tokenize ==================================

        {.id = "const pi (alias) -> Const(Pi)",
         .input = "pi",
         .expected = {Co(tcalc::consts::ConstId::Pi)}},
        {.id = "const pi (symbol) -> Const(Pi)",
         .input = "π",
         .expected = {Co(tcalc::consts::ConstId::Pi)}},
        {.id = "const tau -> Const(Tau)",
         .input = "tau",
         .expected = {Co(tcalc::consts::ConstId::Tau)}},
        {.id = "const e -> Const(EulerNumber)",
         .input = "e",
         .expected = {Co(tcalc::consts::ConstId::EulerNumber)}},
        {.id = "const j -> Const(Imaginary)",
         .input = "j",
         .expected = {Co(tcalc::consts::ConstId::Imaginary)}},
        {.id = "const hbar -> Const(PlanckHbar)",
         .input = "ℏ",
         .expected = {Co(tcalc::consts::ConstId::PlanckHbar)}},
        {.id = "const Z0 -> Const(VacuumImpedance)",
         .input = "Z₀",
         .expected = {Co(tcalc::consts::ConstId::VacuumImpedance)}},
        {.id = "const m_e -> Const(ElectronMass)",
         .input = "mₑ",
         .expected = {Co(tcalc::consts::ConstId::ElectronMass)}},
        {.id = "const R -> Const(GasConstant)",
         .input = "R",
         .expected = {Co(tcalc::consts::ConstId::GasConstant)}},
        {.id = "Rydberg subscript: R_{∞} folds to Subscript(R, ∞)",
         .input = "R_{∞}",
         .expected = {Sub({Co(tcalc::consts::ConstId::GasConstant)}, {N("∞")})}},
        {.id = "non-const letter p stays Char", .input = "p", .expected = {Ch('p')}},
        {.id = "sci notation 2e3 one Number", .input = "2e3", .expected = {N("2e3")}},
        {.id = "2e -> Number then Const(EulerNumber)",
         .input = "2e",
         .expected = {N("2"), Co(tcalc::consts::ConstId::EulerNumber)}},
        {.id = "2i stays one imaginary Number", .input = "2i", .expected = {N("2i")}},
        {.id = "ab -> two CharTokens", .input = "ab", .expected = {Ch('a'), Ch('b')}},
        {.id = "2A -> Number then Char", .input = "2A", .expected = {N("2"), Ch('A')}},
    };

    for (std::size_t i = 0; i < tok_cases.size(); ++i) {
        const auto &tc = tok_cases[i];
        test_detail::with_case(ctx, std::string("tokenize :: ") + tc.id, [&] {
            EXPECT_EQ(ctx, p::tokenize(tc.input).tokens, tc.expected);
        });
    }

    // -----------------------------------------------------------------
    // CallToken tokenization (call-function `(`)
    // -----------------------------------------------------------------

    test_detail::with_case(ctx, "tokenize :: sin(45) -> CallToken 1 arg", [&] {
        const auto branch = p::tokenize("sin(45)");
        EXPECT_EQ(ctx, branch.tokens.size(), std::size_t{1});
        EXPECT_EQ(ctx, branch.tokens[0].kind, p::TokenKind::Call);
        const auto &c = std::get<p::CallToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, c.op_id, o::OpId::Sin);
        EXPECT_EQ(ctx, c.args.size(), std::size_t{1});
    });

    test_detail::with_case(ctx, "tokenize :: mean(1,2) -> CallToken 2 args", [&] {
        const auto branch = p::tokenize("mean(1,2)");
        EXPECT_EQ(ctx, branch.tokens[0].kind, p::TokenKind::Call);
        const auto &c = std::get<p::CallToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, c.op_id, o::OpId::Mean);
        EXPECT_EQ(ctx, c.args.size(), std::size_t{2});
    });

    test_detail::with_case(ctx, "tokenize :: gcd(12,8) -> CallToken 2 args", [&] {
        const auto branch = p::tokenize("gcd(12,8)");
        EXPECT_EQ(ctx, branch.tokens[0].kind, p::TokenKind::Call);
        const auto &c = std::get<p::CallToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, c.op_id, o::OpId::Gcd);
        EXPECT_EQ(ctx, c.args.size(), std::size_t{2});
    });

    test_detail::with_case(ctx, "tokenize :: lcm(4,6,8) -> CallToken 3 args", [&] {
        const auto branch = p::tokenize("lcm(4,6,8)");
        EXPECT_EQ(ctx, branch.tokens[0].kind, p::TokenKind::Call);
        const auto &c = std::get<p::CallToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, c.op_id, o::OpId::Lcm);
        EXPECT_EQ(ctx, c.args.size(), std::size_t{3});
    });

    test_detail::with_case(ctx, "tokenize :: mod(7,3) -> CallToken Mod 2 args", [&] {
        const auto branch = p::tokenize("mod(7,3)");
        EXPECT_EQ(ctx, branch.tokens[0].kind, p::TokenKind::Call);
        const auto &c = std::get<p::CallToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, c.op_id, o::OpId::Mod);
        EXPECT_EQ(ctx, c.args.size(), std::size_t{2});
    });

    test_detail::with_case(ctx, "tokenize :: nCr(5,2) -> CallToken Choose 2 args", [&] {
        const auto branch = p::tokenize("nCr(5,2)");
        EXPECT_EQ(ctx, branch.tokens[0].kind, p::TokenKind::Call);
        const auto &c = std::get<p::CallToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, c.op_id, o::OpId::Choose);
        EXPECT_EQ(ctx, c.args.size(), std::size_t{2});
    });

    test_detail::with_case(ctx, "tokenize :: bare (1,2) stays Paren/Point", [&] {
        const auto branch = p::tokenize("(1,2)");
        EXPECT_EQ(ctx, branch.tokens[0].kind, p::TokenKind::Paren);
    });

    test_detail::with_case(ctx, "tokenize :: mean[1,2,3] stays Op + Paren (not call)", [&] {
        const auto branch = p::tokenize("mean[1,2,3]");
        EXPECT_EQ(ctx, branch.tokens[0].kind, p::TokenKind::Op);
    });

    // =========================================================================
    // tokenize position tests
    // =========================================================================
    {
        const std::vector<PositionCase> position_cases = {
            {.id = "simple expr",
             .input = "3 + 5",
             .expected = {.token_count = 3, .positions = {{0, 0, 1}, {1, 2, 3}, {2, 4, 5}}}},

            {.id = "frac expr",
             .input = "\\frac{2}{3}",
             .expected = {.token_count = 1, .latex_indices = {0}, .positions = {{0, 0, 11}}}},

            {.id = "mixed",
             .input = "1 + \\frac{2}{3} + 4",
             .expected =
                 {.token_count = 5,
                  .latex_indices = {2},
                  .positions = {{0, 0, 1}, {1, 2, 3}, {2, 4, 15}, {3, 16, 17}, {4, 18, 19}}}},

            {.id = "multiple expr",
             .input = "\\frac{1}{2} + 3^{4}",
             .expected =
                 {.token_count = 3,
                  .latex_indices = {0, 2},
                  .positions = {{0, 0, 11}, {2, 14, 19}}}},
        };

        for (const auto &tc : position_cases) {
            test_detail::with_case(ctx, std::string("positions :: ") + tc.id, [&] {
                const auto result = p::tokenize(tc.input);
                const auto &exp = tc.expected;

                EXPECT_EQ(ctx, result.tokens.size(), exp.token_count);
                EXPECT_EQ(ctx, result.latex_indices, exp.latex_indices);
                for (const auto &[idx, start, end] : exp.positions) {
                    EXPECT_EQ(ctx, result.tokens[idx].start_pos, start);
                    EXPECT_EQ(ctx, result.tokens[idx].end_pos, end);
                }
            });
        }
    }

    // =========================================================================
    // Scanifications
    // =========================================================================
    const std::vector<ScanCase> scan_cases = {
        {.id = "integer",
         .input = {.text = "123", .start = 0},
         .expected = {.view = "123", .next = 3}},
        {.id = "decimal",
         .input = {.text = "12.34", .start = 0},
         .expected = {.view = "12.34", .next = 5}},
        {.id = "leading dot",
         .input = {.text = ".5", .start = 0},
         .expected = {.view = ".5", .next = 2}},
        {.id = "trailing dot",
         .input = {.text = "5.", .start = 0},
         .expected = {.view = "5.", .next = 2}},
        {.id = "sci basic",
         .input = {.text = "1e10", .start = 0},
         .expected = {.view = "1e10", .next = 4}},
        {.id = "sci negative exp",
         .input = {.text = "1e-3", .start = 0},
         .expected = {.view = "1e-3", .next = 4}},
        {.id = "sci positive exp",
         .input = {.text = "1e+0", .start = 0},
         .expected = {.view = "1e+0", .next = 4}},
        {.id = "sci incomplete",
         .input = {.text = "1e+", .start = 0},
         .expected = {.view = "1", .next = 1}},
        {.id = "sci imag prefix",
         .input = {.text = "1e-3i", .start = 0},
         .expected = {.view = "1e-3", .next = 4}},
        {.id = "scan mid string",
         .input = {.text = "xx12.3", .start = 2},
         .expected = {.view = "12.3", .next = 6}},
        {.id = "no number",
         .input = {.text = "abc", .start = 0},
         .expected = {.view = "", .next = 0}},
        {.id = "dot only", .input = {.text = ".", .start = 0}, .expected = {.view = "", .next = 0}},
    };

    for (std::size_t i = 0; i < scan_cases.size(); ++i) {
        const auto &tc = scan_cases[i];
        test_detail::with_case(ctx, std::string("scan number :: ") + tc.id, [&] {
            std::size_t next = tc.input.start;
            const std::string_view view = d::scan_number(tc.input.text, tc.input.start, next);
            EXPECT_EQ(ctx, view, tc.expected.view);
            EXPECT_EQ(ctx, next, tc.expected.next);
        });
    }

    // =========================================================================
    // match_parens (structural shape under unified Paren model)
    // =========================================================================
    {
        // Under the unified Paren model paren matching is implicit in the
        // kapsayıcı structure (no per-character pairing index). A matched group
        // becomes a single
        // ParenToken {kind, elements, has_open=true, has_close=true}; an unclosed
        // open keeps has_close=false; a stray close becomes a standalone
        // ParenToken with has_open=false and empty elements.
        //
        // ParenCheck: descriptor for one ParenToken reached via a path from the
        // top-level result.tokens vector. path = {top_idx, elem_idx, [token_idx_in_EV],
        // elem_idx, ...}. Even-indexed steps index ParenToken.elements; the step
        // after a multi-token EV element selects which Token inside the vector.
        // For arm 0 (single-Token element) the path skips straight to the next
        // elements layer (so {0, 0, 0} means "outer.elements[0] as Token (arm 0),
        // then that Token is a ParenToken whose elements[0]..."). The runner walks
        // the path step-by-step; see below.
        struct ParenCheck {
            std::vector<std::size_t> path;
            ParenKind kind{};
            bool has_open = true;
            bool has_close = true;
        };
        struct MatchParensExpected {
            std::size_t top_level_token_count = 0;
            std::vector<p::TokenIndex> paren_indices{};
            std::vector<ParenCheck> paren_checks{};
        };
        // Inline case struct: local scope sees both global ::Case (from
        // test_helpers.hpp) and the anonymous-namespace Case in this file,
        // making `Case<...>` ambiguous. Skip the template alias.
        struct MatchParensCase {
            const char *id;
            const char *input;
            MatchParensExpected expected;
        };

        const std::vector<MatchParensCase> match_parens_cases = {
            // (1+2) -> single matched Paren wrapping EV({N,Op,N}).
            {.id = "simple parens become single Paren",
             .input = "(1+2)",
             .expected =
                 {.top_level_token_count = 1,
                  .paren_indices = {0},
                  .paren_checks =
                      {{.path = {0}, .kind = PK::Paren, .has_open = true, .has_close = true}}}},

            // ((1)) -> outer Paren with one element (arm 0 single Token = inner Paren).
            {.id = "nested same kind: outer+inner matched",
             .input = "((1))",
             .expected =
                 {.top_level_token_count = 1,
                  .paren_indices = {0},
                  .paren_checks =
                      {{.path = {0}, .kind = PK::Paren, .has_open = true, .has_close = true},
                       // outer.elements[0] is arm 0 Token = inner Paren.
                       {.path = {0, 0}, .kind = PK::Paren, .has_open = true, .has_close = true}}}},

            // ({[1]}) -> Paren( Brace( Bracket( N(1) ) ) ); all matched.
            {.id = "mixed kinds nested all matched",
             .input = "({[1]})",
             .expected =
                 {.top_level_token_count = 1,
                  .paren_indices = {0},
                  .paren_checks =
                      {{.path = {0}, .kind = PK::Paren, .has_open = true, .has_close = true},
                       {.path = {0, 0}, .kind = PK::Brace, .has_open = true, .has_close = true},
                       {.path = {0, 0, 0},
                        .kind = PK::Bracket,
                        .has_open = true,
                        .has_close = true}}}},

            // (1)+(2) -> Pp, Op, Pp. paren_indices = {0, 2}.
            {.id = "sequential groups Pp Op Pp",
             .input = "(1)+(2)",
             .expected =
                 {.top_level_token_count = 3,
                  .paren_indices = {0, 2},
                  .paren_checks =
                      {{.path = {0}, .kind = PK::Paren, .has_open = true, .has_close = true},
                       {.path = {2}, .kind = PK::Paren, .has_open = true, .has_close = true}}}},

            // (1+2 -> single Paren with has_close=false.
            {.id = "unmatched open Paren unclosed",
             .input = "(1+2",
             .expected =
                 {.top_level_token_count = 1,
                  .paren_indices = {0},
                  .paren_checks =
                      {{.path = {0}, .kind = PK::Paren, .has_open = true, .has_close = false}}}},

            // 1+2) -> N, Op, N, StrayC(Paren). Stray close: has_open=false.
            {.id = "unmatched close stays as stray Paren",
             .input = "1+2)",
             .expected =
                 {.top_level_token_count = 4,
                  .paren_indices = {3},
                  .paren_checks =
                      {{.path = {3}, .kind = PK::Paren, .has_open = false, .has_close = true}}}},

            // [(34+5)*(4*{3+5})+4] -> single outer Bracket; every nested paren
            // (Pp1 around 34+5, Pp2 around 4*{3+5}, inner Bc around 3+5) verified
            // matched at its correct depth via path navigation.
            {.id = "complex expression nested parens all matched",
             .input = "[(34+5)*(4*{3+5})+4]",
             .expected =
                 {.top_level_token_count = 1,
                  .paren_indices = {0},
                  .paren_checks =
                      {{.path = {0}, .kind = PK::Bracket, .has_open = true, .has_close = true},
                       // Pp1: outer.elements[0] (vec)[0]
                       {.path = {0, 0, 0}, .kind = PK::Paren, .has_open = true, .has_close = true},
                       // Pp2: outer.elements[0] (vec)[2]
                       {.path = {0, 0, 2}, .kind = PK::Paren, .has_open = true, .has_close = true},
                       // Bc inside Pp2: Pp2.elements[0] (vec)[2]
                       {.path = {0, 0, 2, 0, 2},
                        .kind = PK::Brace,
                        .has_open = true,
                        .has_close = true}}}},

            // 1+2 -> no parens at all.
            {.id = "no parens",
             .input = "1+2",
             .expected = {.top_level_token_count = 3, .paren_indices = {}}},

            // Deep nested mismatched closure stress:
            {.id = "deep nested mismatched closure",
             .input = "[2+(\\frac{2}{3}*{\\frac{4}{5}}-[3+5] +(\\frac{2}{3}) -(4",
             .expected =
                 {.top_level_token_count = 1,
                  .paren_indices = {0},
                  .paren_checks =
                      {{.path = {0}, .kind = PK::Bracket, .has_open = true, .has_close = false},
                       // outer Paren wrapping rest, unclosed at EOF
                       {.path = {0, 0, 2}, .kind = PK::Paren, .has_open = true, .has_close = false},
                       // {\pow{4}{5}} closed Brace
                       {.path = {0, 0, 2, 0, 2},
                        .kind = PK::Brace,
                        .has_open = true,
                        .has_close = true},
                       // [3+5] closed Bracket
                       {.path = {0, 0, 2, 0, 4},
                        .kind = PK::Bracket,
                        .has_open = true,
                        .has_close = true},
                       // (\frac{2}{3}) closed Paren
                       {.path = {0, 0, 2, 0, 6},
                        .kind = PK::Paren,
                        .has_open = true,
                        .has_close = true},
                       // (4 unclosed innermost Paren
                       {.path = {0, 0, 2, 0, 8},
                        .kind = PK::Paren,
                        .has_open = true,
                        .has_close = false}}}},
        };

        // Walks the path from result.tokens and returns a pointer to the
        // ParenToken at the leaf, or nullptr if the path is invalid.
        const auto resolve_paren = [](const std::vector<Token> &tokens,
                                      const std::vector<std::size_t> &path) -> const ParenToken * {
            if (path.empty() || path[0] >= tokens.size())
                return nullptr;
            const Token *cur = &tokens[path[0]];
            for (std::size_t step = 1; step < path.size(); ++step) {
                if (cur->kind != p::TokenKind::Paren)
                    return nullptr;
                const auto &pt = std::get<ParenToken>(cur->data);
                const std::size_t elem_idx = path[step];
                if (elem_idx >= pt.elements.size())
                    return nullptr;
                const auto &elem = pt.elements[elem_idx];
                if (std::holds_alternative<Token>(elem)) {
                    cur = &std::get<Token>(elem);
                } else {
                    const auto &vec = std::get<std::vector<Token>>(elem);
                    // For multi-token EV elements, the next step picks an index
                    // inside the vector; consume one extra path step.
                    ++step;
                    if (step >= path.size() || path[step] >= vec.size())
                        return nullptr;
                    cur = &vec[path[step]];
                }
            }
            if (cur->kind != p::TokenKind::Paren)
                return nullptr;
            return &std::get<ParenToken>(cur->data);
        };

        for (const auto &tc : match_parens_cases) {
            test_detail::with_case(ctx, std::string("match_parens :: ") + tc.id, [&] {
                const auto result = p::tokenize(tc.input);
                const auto &exp = tc.expected;

                EXPECT_EQ(ctx, result.tokens.size(), exp.top_level_token_count);
                if (result.tokens.size() != exp.top_level_token_count)
                    return;
                EXPECT_EQ(ctx, result.paren_indices, exp.paren_indices);

                for (const auto &chk : exp.paren_checks) {
                    const ParenToken *pt = resolve_paren(result.tokens, chk.path);
                    EXPECT_TRUE(ctx, pt != nullptr);
                    if (!pt)
                        continue;
                    EXPECT_EQ(ctx, pt->kind, chk.kind);
                    EXPECT_EQ(ctx, pt->has_open, chk.has_open);
                    EXPECT_EQ(ctx, pt->has_close, chk.has_close);
                }
            });
        }
    }

    // =========================================================================
    // classify_tokens
    // =========================================================================
    {
        const std::vector<ClassifyCase> classify_cases = {
            {.id = "empty", .input = {}, .expected = {}},

            // "1+2"
            {.id = "plain expr no parens no latex",
             .input = {N("1"), Op_(OpId::Add), N("2")},
             .expected = {}},

            // "\frac{1}{2}"
            {.id = "frac alone populates latex_indices",
             .input = {Frac({N("1")}, {N("2")})},
             .expected = {.latex_indices = {0}}},

            // "(\frac{2}{3})" -> Pp({Frac(...)}); latex lives INSIDE paren so
            // top-level latex_indices is empty but has_latex_descendant is true.
            {.id = "matched paren wraps frac",
             .input = {Pp({Frac({N("2")}, {N("3")})})},
             .expected = {.latex_indices = {}, .paren_indices = {0}, .has_latex_descendant = true}},

            // "(1)+(2)" -> Pp({EN("1")}) + Pp({EN("2")})
            {.id = "two sibling paren groups",
             .input = {Pp({EN("1")}), Op_(OpId::Add), Pp({EN("2")})},
             .expected =
                 {.latex_indices = {}, .paren_indices = {0, 2}, .has_latex_descendant = false}},

            // "(1)+\frac{2}{3})" -> Pp({EN("1")}) + Frac(...) StrayC(Paren)
            // Frac is top-level latex here, plus a trailing stray close paren.
            // has_latex_descendant tracks nested latex inside parens; the top-level
            // Frac is in latex_indices, not aggregated into has_latex_descendant.
            {.id = "trailing unmatched close after frac",
             .input = {Pp({EN("1")}), Op_(OpId::Add), Frac({N("2")}, {N("3")}), StrayC(PK::Paren)},
             .expected =
                 {.latex_indices = {2}, .paren_indices = {0, 3}, .has_latex_descendant = false}},

            // "{+\frac{2}{3}" -> Bc({EV({UnaryPlus, Frac})}, has_close=false)
            // Brace owns the +frac as a multi-token element; latex is descendant.
            {.id = "unmatched brace open before frac",
             .input = {Bc(
                 {EV({Op_(OpId::UnaryPlus), Frac({N("2")}, {N("3")})})},
                 /*has_close=*/false)},
             .expected = {.latex_indices = {}, .paren_indices = {0}, .has_latex_descendant = true}},

            // "{\frac{2}{3})" -> Bc({Frac(...)}, has_close=false) then StrayC(Paren)
            // The kinds-don't-match scenario: unclosed brace followed by stray
            // round close. Frac sits inside the brace as descendant.
            {.id = "mixed kinds neither matches",
             .input = {Bc({Frac({N("2")}, {N("3")})}, /*has_close=*/false), StrayC(PK::Paren)},
             .expected =
                 {.latex_indices = {}, .paren_indices = {0, 1}, .has_latex_descendant = true}},

            // "(1)+{2+[\pow{2}{3}]+4}" -> Pp({EN("1")}) + Bc({EV({2 + Br({Pow}) + 4})})
            // Three top-level tokens: paren, op, brace. Brace contains a bracket
            // with a Pow descendant.
            {.id = "three nested mixed kinds all matched",
             .input =
                 {Pp({EN("1")}),
                  Op_(OpId::Add),
                  Bc({EV(
                      {N("2"),
                       Op_(OpId::Add),
                       Br({Pow({N("2")}, {N("3")})}),
                       Op_(OpId::Add),
                       N("4")})})},
             .expected =
                 {.latex_indices = {}, .paren_indices = {0, 2}, .has_latex_descendant = true}},

            // Slice [5..12) of "(1)+{2+[\pow{2}{3}]+4}" re-classified standalone
            // -> 2 + Br({Pow}) + 4. Top-level paren is Br; latex is descendant.
            {.id = "rebase nested slice pairs",
             .input =
                 {N("2"), Op_(OpId::Add), Br({Pow({N("2")}, {N("3")})}), Op_(OpId::Add), N("4")},
             .expected = {.latex_indices = {}, .paren_indices = {2}, .has_latex_descendant = true}},

            // Slice [1..5) of "({[1]})" -> Bc({Br({EN("1")})}, has_close=false)
            // Outer brace lost its close; inner bracket still pairs locally.
            // Only one top-level Paren token.
            {.id = "unmatched outer pair stays open",
             .input = {Bc({Br({EN("1")})}, /*has_close=*/false)},
             .expected =
                 {.latex_indices = {}, .paren_indices = {0}, .has_latex_descendant = false}},

            // Brace contents of "(1)+{2+[\frac{2}{3}+4+(\pow{2}{3}" (build_nodes
            // edge case): three different unmatched opens stacked, two latex.
            // Under the new unified model this becomes a single unclosed Brace
            // wrapping an unclosed Bracket wrapping the rest. All paren kinds
            // remain unclosed; both Frac and Pow are descendants.
            {.id = "all unmatched nested opens with latex",
             .input = {Bc(
                 {EV(
                     {N("2"),
                      Op_(OpId::Add),
                      Br({EV(
                             {Frac({N("2")}, {N("3")}),
                              Op_(OpId::Add),
                              N("4"),
                              Op_(OpId::Add),
                              Pp({Pow({N("2")}, {N("3")})}, /*has_close=*/false)})},
                         /*has_close=*/false)})},
                 /*has_close=*/false)},
             .expected = {.latex_indices = {}, .paren_indices = {0}, .has_latex_descendant = true}},
        };

        for (const auto &tc : classify_cases) {
            test_detail::with_case(ctx, std::string("classify_tokens :: ") + tc.id, [&] {
                auto got = p::classify_tokens(tc.input);
                const auto &exp = tc.expected;

                EXPECT_EQ(ctx, got.latex_indices, exp.latex_indices);
                EXPECT_EQ(ctx, got.paren_indices, exp.paren_indices);
                EXPECT_EQ(ctx, got.has_latex_descendant, exp.has_latex_descendant);
            });
        }
    }

    // paren_indices + has_latex_descendant

    test_detail::with_case(ctx, "paren_indices :: no parens", [&] {
        auto result = p::tokenize("1+2");
        EXPECT_EQ(ctx, result.paren_indices.size(), 0UL);
        EXPECT_EQ(ctx, result.has_latex_descendant, false);
    });

    test_detail::with_case(ctx, "paren_indices :: simple parens single top-level Paren", [&] {
        // (1+2) -> [Pp({EV({...})})]   1 top-level ParenToken at index 0.
        auto result = p::tokenize("(1+2)");
        EXPECT_EQ(ctx, result.tokens.size(), 1UL);
        EXPECT_EQ(ctx, result.paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.paren_indices[0], 0UL);
        EXPECT_EQ(ctx, result.has_latex_descendant, false);
    });

    // Nested-structure scenarios (((, ({[1]}), (1+(2, etc.) are covered by
    // match_parens cases above via path-based ParenCheck assertions; not duplicated
    // here because top-level paren_indices.size() does not reflect nested correctness.

    test_detail::with_case(ctx, "paren_indices :: brace wrapping latex has descendant", [&] {
        // {\frac{1}{2}} -> [Bc({Frac(...)})] single top-level Brace
        // with has_latex_descendant=true (Frac inside).
        auto result = p::tokenize("{\\frac{1}{2}}");
        EXPECT_EQ(ctx, result.tokens.size(), 1UL);
        EXPECT_EQ(ctx, result.paren_indices.size(), 1UL);
        EXPECT_EQ(ctx, result.paren_indices[0], 0UL);
        EXPECT_EQ(ctx, result.has_latex_descendant, true);
        EXPECT_EQ(ctx, result.latex_indices.size(), 0UL);
    });

    test_detail::with_case(ctx, "paren_indices :: latex only no parens", [&] {
        auto result = p::tokenize("\\frac{1}{2}");
        EXPECT_EQ(ctx, result.paren_indices.size(), 0UL);
        EXPECT_EQ(ctx, result.has_latex_descendant, false);
        EXPECT_EQ(ctx, result.latex_indices.size(), 1UL);
    });

    // =========================================================================
    // tokens_to_text
    // =========================================================================

    test_detail::with_case(ctx, "tokens_to_text :: simple binary", [&] {
        std::vector<Token> toks = {
            N("2"),
            Op_(OpId::Add),
            N("3"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("2 + 3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: leading negate", [&] {
        std::vector<Token> toks = {
            Op_(OpId::Negate),
            N("5"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("-5"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: binary then negate", [&] {
        std::vector<Token> toks = {
            N("1"),
            Op_(OpId::Add),
            Op_(OpId::Negate),
            N("2"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("1 + -2"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: unary plus no after_node", [&] {
        std::vector<Token> toks = {
            Op_(OpId::UnaryPlus),
            N("3"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("+3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: unary plus with after_node", [&] {
        std::vector<Token> toks = {
            Op_(OpId::UnaryPlus),
            N("3"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string(" + 3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: negate with after_node", [&] {
        std::vector<Token> toks = {
            Op_(OpId::Negate),
            N("3"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string(" - 3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: after_node only affects first token", [&] {
        std::vector<Token> toks = {
            N("3"),
            Op_(OpId::Add),
            N("5"),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string("3 + 5"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: parens preserved", [&] {
        std::vector<Token> toks = {Pp({EV({N("1"), Op_(OpId::Add), N("2")})})};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("(1 + 2)"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: frac round-trip", [&] {
        std::vector<Token> toks = {Frac({N("2")}, {N("3")})};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("\\frac{2}{3}"));
    });

    // A based log prints as the op carrying its own script, which is what it was typed as,
    // so the editor round-trip is the ordinary one. A multi-token base makes the point:
    // token_text spaces the Div ("log_{1 / 2}") and the tokenizer skips whitespace, so the
    // printed string is not literally the input and the tokens are what must match.
    test_detail::with_case(ctx, "round-trip :: log_{1/2}8 with a multi-token base", [&] {
        const auto branch = p::tokenize("log_{1/2}8");
        const auto reparsed = p::tokenize(p::tokens_to_text(branch.tokens));
        EXPECT_EQ(ctx, reparsed.tokens, branch.tokens);
    });

    test_detail::with_case(ctx, "tokens_to_text :: postfix no spacing", [&] {
        std::vector<Token> toks = {
            N("5"),
            Op_(OpId::Fact),
        };
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("5!"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: empty", [&] {
        std::vector<Token> empty;
        EXPECT_EQ(ctx, p::tokens_to_text(empty), std::string(""));
    });

    test_detail::with_case(ctx, "tokens_to_text :: paren single number", [&] {
        std::vector<Token> toks = {Br({EN("5")})};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("[5]"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: paren multi element comma joined", [&] {
        std::vector<Token> toks = {Br({EN("1"), EN("2"), EN("3")})};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("[1, 2, 3]"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: paren element with binary op", [&] {
        std::vector<Token> toks = {Pp({EV({N("1"), Op_(OpId::Add), N("2")}), EN("3")})};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("(1 + 2, 3)"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: paren unclosed retains opening only", [&] {
        std::vector<Token> toks = {Br({EN("1"), EN("2")}, false)};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("[1, 2"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: bare comma always spaced", [&] {
        std::vector<Token> toks = {N(",")};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string(", "));
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string(", "));
    });

    test_detail::with_case(ctx, "tokens_to_text :: leading comma+digits spaced", [&] {
        std::vector<Token> toks = {N(",3")};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string(", 3"));
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string(", 3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: non-comma number unchanged", [&] {
        std::vector<Token> toks = {N("3")};
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string("3"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: multi comma values spaced everywhere", [&] {
        std::vector<Token> toks = {N(",3,4,5")};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string(", 3, 4, 5"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: trailing comma kept", [&] {
        std::vector<Token> toks = {N("2,3,3,3,")};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("2, 3, 3, 3, "));
    });

    test_detail::with_case(ctx, "tokens_to_text :: comma between digits no leading", [&] {
        std::vector<Token> toks = {N("1,2")};
        EXPECT_EQ(ctx, p::tokens_to_text(toks), std::string("1, 2"));
    });

    test_detail::with_case(ctx, "tokens_to_text :: every comma in every number token", [&] {
        std::vector<Token> toks = {N(",3"), Op_(OpId::Add), N(",5")};
        EXPECT_EQ(ctx, p::tokens_to_text(toks, true), std::string(", 3 + , 5"));
    });

    // =========================================================================
    // structural_split
    // =========================================================================
    {
        using K = SplitExpected::Kind;

        const auto branch = [](std::vector<Token> toks) {
            return p::classify_tokens(std::move(toks));
        };

        // Flatten ParenSplit.elements span into a vector<vector<Token>> for
        // structural comparison against SplitExpected::elements.
        const auto element_tokens = [](std::span<const ParenElement> els) {
            std::vector<std::vector<Token>> out;
            out.reserve(els.size());
            for (const auto &e : els) {
                if (e.index() == 0) {
                    out.push_back({std::get<Token>(e)});
                } else {
                    out.push_back(std::get<std::vector<Token>>(e));
                }
            }
            return out;
        };

        const std::vector<SplitCase> split_cases = {
            // -- nullopt: no latex tokens at all
            {.id = "nullopt :: empty branch", .input = branch({}), .expected = {.kind = K::None}},

            {.id = "nullopt :: plain expr no latex",
             .input = branch({N("1"), Op_(OpId::Add), N("2")}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: paren only no latex",
             .input = branch({Pp({EV({N("1"), Op_(OpId::Add), N("2")})})}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: division op only",
             .input = branch({N("4"), Op_(OpId::Div), N("5")}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: paren mixed ops",
             .input = branch({Pp({EV(
                 {N("2"),
                  Op_(OpId::Add),
                  N("5"),
                  Op_(OpId::Div),
                  N("5"),
                  Op_(OpId::Mul),
                  N("4")})})}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: nested parens no latex",
             .input = branch({Pp({Pp({EN("1")})})}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: two paren groups no latex",
             .input = branch(
                 {Pp({EV({N("1"), Op_(OpId::Add), N("2")})}),
                  Op_(OpId::Mul),
                  Pp({EV({N("3"), Op_(OpId::Add), N("4")})})}),
             .expected = {.kind = K::None}},

            {.id = "nullopt :: unmatched paren no latex",
             .input = branch({Pp({EV({N("1"), Op_(OpId::Add), N("2")})}, /*has_close=*/false)}),
             .expected = {.kind = K::None}},

            // -- LatexSplit: filled latex with no surrounding
            {.id = "latex :: filled frac alone",
             .input = branch({Frac({N("2")}, {N("3")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("2")},
                  .right = {N("3")},
                  .latex_kind = p::LatexKind::Frac}},

            {.id = "latex :: empty frac alone",
             .input = branch({Frac({}, {})}),
             .expected = {.kind = K::Latex, .latex_kind = p::LatexKind::Frac}},

            // -- LatexSplit: operand pickup when latex left/right empty
            // 1+2\frac -> prefix=[1,+], left=[2]
            {.id = "latex :: trailing number becomes left",
             .input = branch({N("1"), Op_(OpId::Add), N("2"), Frac({}, {})}),
             .expected =
                 {.kind = K::Latex,
                  .prefix = {N("1"), Op_(OpId::Add)},
                  .left = {N("2")},
                  .latex_kind = p::LatexKind::Frac}},

            // \frac{}{}+2 ... wait: \frac 2+3 -> right=[2], suffix=[+,3]
            {.id = "latex :: leading number becomes right",
             .input = branch({Frac({}, {}), N("2"), Op_(OpId::Add), N("3")}),
             .expected =
                 {.kind = K::Latex,
                  .right = {N("2")},
                  .suffix = {Op_(OpId::Add), N("3")},
                  .latex_kind = p::LatexKind::Frac}},

            // \frac{1}{}+2 -> left from latex, right empty (op blocks pickup)
            {.id = "latex :: leading op blocks right pickup",
             .input = branch({Frac({N("1")}, {}), Op_(OpId::Add), N("2")}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .suffix = {Op_(OpId::Add), N("2")},
                  .latex_kind = p::LatexKind::Frac}},

            // 1+\frac{}{2} -> left empty (op blocks), right from latex
            {.id = "latex :: trailing op blocks left pickup",
             .input = branch({N("1"), Op_(OpId::Add), Frac({}, {N("2")})}),
             .expected =
                 {.kind = K::Latex,
                  .prefix = {N("1"), Op_(OpId::Add)},
                  .right = {N("2")},
                  .latex_kind = p::LatexKind::Frac}},

            // (2+5)+\frac{}{} -> closed paren BEFORE latex (no latex descendant)
            // stays in prefix as a single Paren token; no ParenSplit triggers.
            {.id = "latex :: closed paren before frac stays in prefix",
             .input =
                 branch({Pp({EV({N("2"), Op_(OpId::Add), N("5")})}), Op_(OpId::Add), Frac({}, {})}),
             .expected =
                 {.kind = K::Latex,
                  .prefix = {Pp({EV({N("2"), Op_(OpId::Add), N("5")})}), Op_(OpId::Add)},
                  .latex_kind = p::LatexKind::Frac}},

            // -- LatexSplit: trailing operand is a paren group
            // 1\frac{}{} -> left=[1], suffix=[]
            {.id = "latex :: trailing num before latex",
             .input = branch({N("1"), Frac({}, {})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {},
                  .latex_kind = p::LatexKind::Frac}},

            // \frac{1}{}(2+3) -> trailing paren picked up into right.
            // Paren has no latex descendant so it does not become a ParenSplit;
            // split_operand grabs it as the right operand of the frac.
            {.id = "latex :: trailing paren group becomes right",
             .input = branch({Frac({N("1")}, {}), Pp({EV({N("2"), Op_(OpId::Add), N("3")})})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {Pp({EV({N("2"), Op_(OpId::Add), N("3")})})},
                  .latex_kind = p::LatexKind::Frac}},
            // 1\frac{}{}(2+3) -> right=[(2+3)], left=[1].
            {.id = "latex :: trailing num and paren group becomes right and left",
             .input = branch({N("1"), Frac({}, {}), Pp({EV({N("2"), Op_(OpId::Add), N("3")})})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {Pp({EV({N("2"), Op_(OpId::Add), N("3")})})},
                  .latex_kind = p::LatexKind::Frac}},

            // -- Sum/Prod: empty limit is never a pickup site (unlike Frac above).
            // \sum_{n=1} n -> mid-typing, no upper limit yet: right stays empty,
            // the body `n` stays in suffix instead of being stolen as the upper limit.
            {.id = "sum :: empty upper limit does not steal the body",
             .input = branch(p::tokenize("\\sum_{n=1} n").tokens),
             .expected =
                 {.kind = K::Latex,
                  .left = {Ch('n'), Op_(OpId::Assign), N("1")},
                  .suffix = {Ch('n')},
                  .latex_kind = p::LatexKind::Sum}},

            // -- ParenSplit cases (reactivated under unified ParenToken model).

            // (\frac{2}{3}) -> ParenSplit wraps one element [Frac].
            {.id = "paren :: matched paren wraps frac",
             .input = branch({Pp({Frac({N("2")}, {N("3")})})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Frac({N("2")}, {N("3")})}}}},

            // (1+\frac{2}{3} -> unmatched open (has_close=false).
            {.id = "paren :: unmatched open before frac",
             .input = branch(
                 {Pp({EV({N("1"), Op_(OpId::Add), Frac({N("2")}, {N("3")})})},
                     /*has_close=*/false)}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = false,
                  .elements = {{N("1"), Op_(OpId::Add), Frac({N("2")}, {N("3")})}}}},

            // (2+\frac{2}{})\frac{}{} -> outer paren wraps first frac (has_latex),
            // second frac is in suffix.
            {.id = "paren :: wrap first frac, second frac in suffix",
             .input =
                 branch({Pp({EV({N("2"), Op_(OpId::Add), Frac({N("2")}, {})})}), Frac({}, {})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{N("2"), Op_(OpId::Add), Frac({N("2")}, {})}},
                  .suffix = {Frac({}, {})}}},

            // ((1)+\frac{2}{3}) -> outer paren is the candidate; the inner (1)
            // paren without latex remains as a Token inside the outer's element.
            {.id = "paren :: outer paren picked over inner",
             .input = branch({Pp({EV({Pp({EN("1")}), Op_(OpId::Add), Frac({N("2")}, {N("3")})})})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Pp({EN("1")}), Op_(OpId::Add), Frac({N("2")}, {N("3")})}}}},

            // -- Sibling latex (no parens): first wins, rest goes to suffix --
            {.id = "latex :: sibling fracs first wins",
             .input = branch({Frac({N("1")}, {N("2")}), Op_(OpId::Add), Frac({N("3")}, {N("4")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {N("2")},
                  .suffix = {Op_(OpId::Add), Frac({N("3")}, {N("4")})},
                  .latex_kind = p::LatexKind::Frac}},

            // Paren AFTER first latex doesn't trigger ParenSplit; the trailing
            // paren (with latex inside) sits past latex_first so is ignored,
            // staying in the LatexSplit suffix.
            {.id = "latex :: paren after first frac stays in suffix",
             .input =
                 branch({Frac({N("1")}, {N("2")}), Op_(OpId::Add), Pp({Frac({N("3")}, {N("4")})})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {N("2")},
                  .suffix = {Op_(OpId::Add), Pp({Frac({N("3")}, {N("4")})})},
                  .latex_kind = p::LatexKind::Frac}},

            // -- Nested latex (top-level token has nested Latex inside)
            // \frac{\frac{1}{2}}{3} -> outer wins; nested frac is one element of left
            {.id = "latex :: nested frac in left",
             .input = branch({Frac({Frac({N("1")}, {N("2")})}, {N("3")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {Frac({N("1")}, {N("2")})},
                  .right = {N("3")},
                  .latex_kind = p::LatexKind::Frac}},

            // \frac{1}{\frac{2}{3}} -> outer wins; nested frac sits in right
            {.id = "latex :: nested frac in right",
             .input = branch({Frac({N("1")}, {Frac({N("2")}, {N("3")})})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {Frac({N("2")}, {N("3")})},
                  .latex_kind = p::LatexKind::Frac}},

            // -- Nested parens around a latex --
            // ((1+\frac{2}{3})) -> outermost paren wraps everything; inner paren
            // becomes the sole element (also carries has_latex_descendant=true).
            {.id = "paren :: doubly nested wraps frac",
             .input = branch({Pp({Pp({EV({N("1"), Op_(OpId::Add), Frac({N("2")}, {N("3")})})})})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Pp({EV({N("1"), Op_(OpId::Add), Frac({N("2")}, {N("3")})})})}}}},

            // 1+(2+\frac{3}{4})*5 -> paren wraps frac; prefix=[1,+], suffix=[*,5].
            {.id = "paren :: wrap frac with ops on both sides",
             .input = branch(
                 {N("1"),
                  Op_(OpId::Add),
                  Pp({EV({N("2"), Op_(OpId::Add), Frac({N("3")}, {N("4")})})}),
                  Op_(OpId::Mul),
                  N("5")}),
             .expected =
                 {.kind = K::Paren,
                  .prefix = {N("1"), Op_(OpId::Add)},
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{N("2"), Op_(OpId::Add), Frac({N("3")}, {N("4")})}},
                  .suffix = {Op_(OpId::Mul), N("5")}}},

            // -- Sibling: more than two
            // \frac{1}{2}+\frac{3}{4}+\frac{5}{6} -> first wins, rest in suffix
            {.id = "latex :: three sibling fracs",
             .input = branch(
                 {Frac({N("1")}, {N("2")}),
                  Op_(OpId::Add),
                  Frac({N("3")}, {N("4")}),
                  Op_(OpId::Add),
                  Frac({N("5")}, {N("6")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {N("2")},
                  .suffix =
                      {Op_(OpId::Add),
                       Frac({N("3")}, {N("4")}),
                       Op_(OpId::Add),
                       Frac({N("5")}, {N("6")})},
                  .latex_kind = p::LatexKind::Frac}},

            // (\frac{1}{2}+\frac{3}{4}) -> single paren element wraps two fracs
            // separated by an operator.
            {.id = "paren :: wrap two sibling fracs",
             .input = branch(
                 {Pp({EV({Frac({N("1")}, {N("2")}), Op_(OpId::Add), Frac({N("3")}, {N("4")})})})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements =
                      {{Frac({N("1")}, {N("2")}), Op_(OpId::Add), Frac({N("3")}, {N("4")})}}}},

            // -- Sibling + nested mix
            // \frac{1}{\frac{2}{3}}+\frac{4}{5} -> first frac wins
            {.id = "latex :: nested-right then sibling",
             .input = branch(
                 {Frac({N("1")}, {Frac({N("2")}, {N("3")})}),
                  Op_(OpId::Add),
                  Frac({N("4")}, {N("5")})}),
             .expected =
                 {.kind = K::Latex,
                  .left = {N("1")},
                  .right = {Frac({N("2")}, {N("3")})},
                  .suffix = {Op_(OpId::Add), Frac({N("4")}, {N("5")})},
                  .latex_kind = p::LatexKind::Frac}},

            // (\frac{1}{2})+\frac{3}{4} -> first (paren-with-latex) wins; trailing
            // sibling frac goes to suffix.
            {.id = "paren :: wrapped frac plus sibling outside",
             .input =
                 branch({Pp({Frac({N("1")}, {N("2")})}), Op_(OpId::Add), Frac({N("3")}, {N("4")})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Frac({N("1")}, {N("2")})}},
                  .suffix = {Op_(OpId::Add), Frac({N("3")}, {N("4")})}}},

            // -- Two sibling ParenSplits: first one wins
            {.id = "paren :: two sibling paren-wrapped fracs",
             .input = branch(
                 {Pp({Frac({N("1")}, {N("2")})}), Op_(OpId::Add), Pp({Frac({N("3")}, {N("4")})})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Frac({N("1")}, {N("2")})}},
                  .suffix = {Op_(OpId::Add), Pp({Frac({N("3")}, {N("4")})})}}},

            {.id = "paren :: two sibling paren groups with inner ops",
             .input = branch(
                 {Pp({EV({Frac({N("1")}, {N("2")}), Op_(OpId::Add), N("1")})}),
                  Op_(OpId::Mul),
                  Pp({EV({N("2"), Op_(OpId::Sub), Frac({N("3")}, {N("4")})})})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Frac({N("1")}, {N("2")}), Op_(OpId::Add), N("1")}},
                  .suffix =
                      {Op_(OpId::Mul),
                       Pp({EV({N("2"), Op_(OpId::Sub), Frac({N("3")}, {N("4")})})})}}},

            {.id = "paren :: three sibling paren-wrapped fracs",
             .input = branch(
                 {Pp({Frac({N("1")}, {N("2")})}),
                  Op_(OpId::Add),
                  Pp({Frac({N("3")}, {N("4")})}),
                  Op_(OpId::Mul),
                  Pp({Frac({N("5")}, {N("6")})})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Frac({N("1")}, {N("2")})}},
                  .suffix =
                      {Op_(OpId::Add),
                       Pp({Frac({N("3")}, {N("4")})}),
                       Op_(OpId::Mul),
                       Pp({Frac({N("5")}, {N("6")})})}}},

            // Outer paren wraps a nested (paren-with-frac + N) group, plus two
            // more sibling paren-wrapped fracs outside.
            {.id = "paren :: four paren groups, first has nested wrap",
             .input = branch(
                 {Pp({EV({Pp({EV({Frac({N("1")}, {N("2")}), Op_(OpId::Add), N("1")})})})}),
                  Op_(OpId::Add),
                  Pp({Frac({N("3")}, {N("4")})}),
                  Op_(OpId::Add),
                  Pp({Frac({N("5")}, {N("6")})})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Pp({EV({Frac({N("1")}, {N("2")}), Op_(OpId::Add), N("1")})})}},
                  .suffix =
                      {Op_(OpId::Add),
                       Pp({Frac({N("3")}, {N("4")})}),
                       Op_(OpId::Add),
                       Pp({Frac({N("5")}, {N("6")})})}}},

            // -- Collection (List/Point) variants of ParenSplit --
            // [\frac{1}{2}, 3] -> ParenSplit with Bracket kind, two elements.
            {.id = "bracket :: list of latex",
             .input = branch({Br({Frac({N("1")}, {N("2")}), EN("3")})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Bracket,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Frac({N("1")}, {N("2")})}, {N("3")}}}},

            // (\frac{1}{2}, 3) -> Point: ParenSplit with Paren kind, two elements.
            {.id = "paren-collection :: point of latex",
             .input = branch({Pp({Frac({N("1")}, {N("2")}), EN("3")})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Paren,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Frac({N("1")}, {N("2")})}, {N("3")}}}},

            // {\frac{1}{2}} (user brace around frac) -> ParenSplit with Brace kind.
            {.id = "brace :: wraps frac",
             .input = branch({Bc({Frac({N("1")}, {N("2")})})}),
             .expected =
                 {.kind = K::Paren,
                  .paren_kind = ParenKind::Brace,
                  .has_open = true,
                  .has_close = true,
                  .elements = {{Frac({N("1")}, {N("2")})}}}},
        };

        const auto to_vec = [](std::span<const Token> a) {
            return std::vector<Token>(a.begin(), a.end());
        };

        for (const auto &tc : split_cases) {
            test_detail::with_case(ctx, std::string("structural_split :: ") + tc.id, [&] {
                const auto got = p::structural_split(tc.input);
                const auto &exp = tc.expected;

                if (exp.kind == K::None) {
                    EXPECT_TRUE(ctx, !got.has_value());
                    return;
                }
                EXPECT_TRUE(ctx, got.has_value());
                if (!got.has_value())
                    return;

                std::visit(
                    [&](const auto &s) {
                        using T = std::decay_t<decltype(s)>;
                        if constexpr (std::is_same_v<T, p::ParenSplit>) {
                            EXPECT_TRUE(ctx, exp.kind == K::Paren);
                            EXPECT_EQ(ctx, to_vec(s.prefix), exp.prefix);
                            EXPECT_EQ(ctx, to_vec(s.suffix), exp.suffix);
                            EXPECT_TRUE(ctx, s.kind == exp.paren_kind);
                            EXPECT_TRUE(ctx, s.has_open == exp.has_open);
                            EXPECT_TRUE(ctx, s.has_close == exp.has_close);
                            EXPECT_EQ(ctx, element_tokens(s.elements), exp.elements);
                        } else {
                            EXPECT_TRUE(ctx, exp.kind == K::Latex);
                            EXPECT_EQ(ctx, to_vec(s.prefix), exp.prefix);
                            EXPECT_EQ(ctx, to_vec(s.left), exp.left);
                            EXPECT_EQ(ctx, to_vec(s.suffix), exp.suffix);
                            EXPECT_TRUE(ctx, s.kind == exp.latex_kind);
                            EXPECT_EQ(ctx, to_vec(s.right), exp.right);
                        }
                    },
                    *got);
            });
        }
    }

    // =========================================================================
    // build_math_nodes
    // =========================================================================
    {
        const auto branch = [](std::vector<Token> toks) {
            return p::classify_tokens(std::move(toks));
        };

        const std::vector<BuildNodesCase> build_nodes_cases = {
            {.id = "fracNode-0", .input = branch({Frac({}, {})}), .expected = {Frn({}, {})}},
            {.id = "powNode-0", .input = branch({Pow({}, {})}), .expected = {Pwn({}, {})}},
            {.id = "rootNode-0", .input = branch({Root({}, {})}), .expected = {Rtn({}, {})}},

            {.id = "fracNode-1",
             .input = branch({Frac({N("1")}, {N("2")})}),
             .expected = {Frn({T_("1")}, {T_("2")})}},
            {.id = "powNode-1",
             .input = branch({Pow({N("2")}, {N("3")})}),
             .expected = {Pwn({T_("2")}, {T_("3")})}},
            {.id = "rootNode-1",
             .input = branch({Root({N("2")}, {N("3")})}),
             .expected = {Rtn({T_("2")}, {T_("3")})}},

            {.id = "frac-plus",
             .input = branch({N("1"), Op_(OpId::Add), Frac({N("1")}, {N("2")})}),
             .expected = {T_("1 + "), Frn({T_("1")}, {T_("2")})}},

            {.id = "frac-plus-frac",
             .input = branch({Frac({N("1")}, {N("2")}), Op_(OpId::Add), Frac({N("3")}, {N("4")})}),
             .expected = {Frn({T_("1")}, {T_("2")}), T_(" + "), Frn({T_("3")}, {T_("4")})}},

            {.id = "pow-plus",
             .input = branch({N("1"), Op_(OpId::Add), Pow({N("2")}, {N("3")})}),
             .expected = {T_("1 + "), Pwn({T_("2")}, {T_("3")})}},
            {.id = "root-plus",
             .input = branch({N("1"), Op_(OpId::Add), Root({N("2")}, {N("3")})}),
             .expected = {T_("1 + "), Rtn({T_("2")}, {T_("3")})}},

            {.id = "implicit-multiplation-nodes",
             .input = branch({Frac({N("1")}, {N("2")}), Root({N("2")}, {N("3")})}),
             .expected = {Frn({T_("1")}, {T_("2")}), Rtn({T_("2")}, {T_("3")})}},

            {.id = "frac-nested-left",
             .input = branch({Frac({Frac({N("1")}, {N("2")})}, {N("3")})}),
             .expected = {Frn({Frn({T_("1")}, {T_("2")})}, {T_("3")})}},

            {.id = "frac-nested-both",
             .input = branch({Frac({Frac({N("1")}, {N("2")})}, {Frac({N("3")}, {N("4")})})}),
             .expected = {Frn({Frn({T_("1")}, {T_("2")})}, {Frn({T_("3")}, {T_("4")})})}},

            {.id = "pow-nested-exp",
             .input = branch({Pow({N("2")}, {Pow({N("3")}, {N("4")})})}),
             .expected = {Pwn({T_("2")}, {Pwn({T_("3")}, {T_("4")})})}},

            {.id = "pow-nested-base",
             .input = branch({Pow({Pow({N("2")}, {N("3")})}, {N("4")})}),
             .expected = {Pwn({Pwn({T_("2")}, {T_("3")})}, {T_("4")})}},

            {.id = "root-nested-radicand",
             .input = branch({Root({N("2")}, {Root({N("3")}, {N("4")})})}),
             .expected = {Rtn({T_("2")}, {Rtn({T_("3")}, {T_("4")})})}},

            {.id = "root-nested-degree",
             .input = branch({Root({Root({N("2")}, {N("3")})}, {N("4")})}),
             .expected = {Rtn({Rtn({T_("2")}, {T_("3")})}, {T_("4")})}},

            {.id = "frac-with-two-pows",
             .input = branch({Frac({Pow({N("2")}, {N("3")})}, {Pow({N("4")}, {N("5")})})}),
             .expected = {Frn({Pwn({T_("2")}, {T_("3")})}, {Pwn({T_("4")}, {T_("5")})})}},

            {.id = "frac-with-pow-root",
             .input = branch({Frac({Pow({N("2")}, {N("3")})}, {Root({N("4")}, {N("5")})})}),
             .expected = {Frn({Pwn({T_("2")}, {T_("3")})}, {Rtn({T_("4")}, {T_("5")})})}},

            {.id = "pow-with-frac-root",
             .input = branch({Pow({Frac({N("1")}, {N("2")})}, {Root({N("2")}, {N("3")})})}),
             .expected = {Pwn({Frn({T_("1")}, {T_("2")})}, {Rtn({T_("2")}, {T_("3")})})}},

            // "\root{2}{\frac{\pow{3}{4}}{5}}"
            {.id = "root-with-frac-pow",
             .input = branch({Root({N("2")}, {Frac({Pow({N("3")}, {N("4")})}, {N("5")})})}),
             .expected = {Rtn({T_("2")}, {Frn({Pwn({T_("3")}, {T_("4")})}, {T_("5")})})}},

            // "\frac{1+\pow{2}{3}}{4}"
            {.id = "frac-nested-with-text",
             .input = branch({Frac({N("1"), Op_(OpId::Add), Pow({N("2")}, {N("3")})}, {N("4")})}),
             .expected = {Frn({T_("1 + "), Pwn({T_("2")}, {T_("3")})}, {T_("4")})}},

            // "\pow{1+\frac{2}{3}}{4}"
            {.id = "pow-nested-with-text",
             .input = branch({Pow({N("1"), Op_(OpId::Add), Frac({N("2")}, {N("3")})}, {N("4")})}),
             .expected = {Pwn({T_("1 + "), Frn({T_("2")}, {T_("3")})}, {T_("4")})}},

            // "\root{1+\pow{2}{3}}{4}"
            {.id = "root-nested-with-text",
             .input = branch({Root({N("1"), Op_(OpId::Add), Pow({N("2")}, {N("3")})}, {N("4")})}),
             .expected = {Rtn({T_("1 + "), Pwn({T_("2")}, {T_("3")})}, {T_("4")})}},

            // -- Caret fold end-to-end: tokenize(^{}) → Pow LatexNode --

            // "2^{3}" folds to LatexToken(Pow) at tokenize, then renders as a Pow node.
            {.id = "pow-caret-node",
             .input = branch(p::tokenize("2^{3}").tokens),
             .expected = {Pwn({T_("2")}, {T_("3")})}},

            // "\frac{2^{3}}{4}" — caret fold nested inside a frac numerator.
            {.id = "pow-caret-in-frac",
             .input = branch(p::tokenize("\\frac{2^{3}}{4}").tokens),
             .expected = {Frn({Pwn({T_("2")}, {T_("3")})}, {T_("4")})}},

            // -- Paren cases (unified ParenToken model) --

            // "(1)+\frac{2}{3}"  — Paren has no latex descendant, stays as text prefix.
            {.id = "non-parenNode",
             .input = branch({Pp({EN("1")}), Op_(OpId::Add), Frac({N("2")}, {N("3")})}),
             .expected = {T_("(1) + "), Frn({T_("2")}, {T_("3")})}},

            // "(1)+\frac{2}{3})"  — Paren text + Frac + stray ')' (StrayC has has_open=false).
            {.id = "non-parenNode-w-close",
             .input = branch(
                 {Pp({EN("1")}), Op_(OpId::Add), Frac({N("2")}, {N("3")}), StrayC(PK::Paren)}),
             .expected = {T_("(1) + "), Frn({T_("2")}, {T_("3")}), T_(")")}},

            // "(1)+(\frac{2}{3})"  — first paren prefix text, second wraps Frac → ParenNode.
            {.id = "render-parenNode",
             .input = branch({Pp({EN("1")}), Op_(OpId::Add), Pp({Frac({N("2")}, {N("3")})})}),
             .expected = {T_("(1) + "), Pn(PK::Paren, true, {Frn({T_("2")}, {T_("3")})})}},

            // "(1)+(2+\frac{2}{3})"  — second paren contains "2 + Frac" → ParenNode.
            {.id = "paren-with-prefix-text",
             .input = branch(
                 {Pp({EN("1")}),
                  Op_(OpId::Add),
                  Pp({EV({N("2"), Op_(OpId::Add), Frac({N("2")}, {N("3")})})})}),
             .expected =
                 {T_("(1) + "), Pn(PK::Paren, true, {T_("2 + "), Frn({T_("2")}, {T_("3")})})}},

            // "{\frac{2}{3}}"  — Brace wraps Frac → ParenNode(Brace).
            {.id = "brace-widget",
             .input = branch({Bc({Frac({N("2")}, {N("3")})})}),
             .expected = {Pn(PK::Brace, true, {Frn({T_("2")}, {T_("3")})})}},

            // "{\frac{2}{3})"  — Brace unclosed (kind-strict scan stops at ')'),
            //                   ')' becomes top-level StrayC.
            {.id = "non-closed-brace-widget",
             .input = branch({Bc({Frac({N("2")}, {N("3")})}, false), StrayC(PK::Paren)}),
             .expected = {Pn(PK::Brace, false, {Frn({T_("2")}, {T_("3")})}), T_(")")}},

            // "{+\frac{2}{3}"  — brace stays open; leading + becomes UnaryPlus inside.
            {.id = "open-brace-leading-op",
             .input = branch({Bc({EV({Op_(OpId::UnaryPlus), Frac({N("2")}, {N("3")})})}, false)}),
             .expected = {Pn(PK::Brace, false, {T_("+"), Frn({T_("2")}, {T_("3")})})}},

            // "(1)+{2+\root{2}{3}}"
            {.id = "brace-in-sum",
             .input = branch(
                 {Pp({EN("1")}),
                  Op_(OpId::Add),
                  Bc({EV({N("2"), Op_(OpId::Add), Root({N("2")}, {N("3")})})})}),
             .expected =
                 {T_("(1) + "), Pn(PK::Brace, true, {T_("2 + "), Rtn({T_("2")}, {T_("3")})})}},

            // "[\frac{2}{3}]"
            {.id = "bracket-widget",
             .input = branch({Br({Frac({N("2")}, {N("3")})})}),
             .expected = {Pn(PK::Bracket, true, {Frn({T_("2")}, {T_("3")})})}},

            // "(1)+{2+[\pow{2}{3}]+4}"
            {.id = "outer-first-nested-parens",
             .input = branch(
                 {Pp({EN("1")}),
                  Op_(OpId::Add),
                  Bc({EV(
                      {N("2"),
                       Op_(OpId::Add),
                       Br({Pow({N("2")}, {N("3")})}),
                       Op_(OpId::Add),
                       N("4")})})}),
             .expected =
                 {T_("(1) + "),
                  Pn(PK::Brace,
                     true,
                     {T_("2 + "),
                      Pn(PK::Bracket, true, {Pwn({T_("2")}, {T_("3")})}),
                      T_(" + 4")})}},

            // "(1)+{2+[\frac{2}{3}+4+(\pow{2}{3})]}"
            {.id = "nested-brace-bracket-paren",
             .input = branch(
                 {Pp({EN("1")}),
                  Op_(OpId::Add),
                  Bc({EV(
                      {N("2"),
                       Op_(OpId::Add),
                       Br({EV(
                           {Frac({N("2")}, {N("3")}),
                            Op_(OpId::Add),
                            N("4"),
                            Op_(OpId::Add),
                            Pp({Pow({N("2")}, {N("3")})})})})})})}),
             .expected =
                 {T_("(1) + "),
                  Pn(PK::Brace,
                     true,
                     {T_("2 + "),
                      Pn(PK::Bracket,
                         true,
                         {Frn({T_("2")}, {T_("3")}),
                          T_(" + 4 + "),
                          Pn(PK::Paren, true, {Pwn({T_("2")}, {T_("3")})})})})}},

            // "(1)+{2+[\frac{2}{3}+4+(\pow{2}{3}"   — every wrapper unclosed at EOF.
            {.id = "nested-brace-bracket-paren-open-only",
             .input = branch(
                 {Pp({EN("1")}),
                  Op_(OpId::Add),
                  Bc({EV(
                         {N("2"),
                          Op_(OpId::Add),
                          Br({EV(
                                 {Frac({N("2")}, {N("3")}),
                                  Op_(OpId::Add),
                                  N("4"),
                                  Op_(OpId::Add),
                                  Pp({Pow({N("2")}, {N("3")})}, false)})},
                             false)})},
                     false)}),
             .expected =
                 {T_("(1) + "),
                  Pn(PK::Brace,
                     false,
                     {T_("2 + "),
                      Pn(PK::Bracket,
                         false,
                         {Frn({T_("2")}, {T_("3")}),
                          T_(" + 4 + "),
                          Pn(PK::Paren, false, {Pwn({T_("2")}, {T_("3")})})})})}},

            // "\frac{1}{2} + sin(90)" — sin(90) Paren has no latex descendant, text.
            {.id = "trig-parens-non-paren",
             .input =
                 branch({Frac({N("1")}, {N("2")}), Op_(OpId::Add), Op_(OpId::Sin), Pp({EN("90")})}),
             .expected = {Frn({T_("1")}, {T_("2")}), T_(" + sin(90)")}},

            // "1 + \frac{2}{3 + cos(90)}" — Paren in Frac.right (no latex desc), text.
            {.id = "trig-parens-non-paren-2",
             .input = branch(
                 {N("1"),
                  Op_(OpId::Add),
                  Frac({N("2")}, {N("3"), Op_(OpId::Add), Op_(OpId::Cos), Pp({EN("90")})})}),
             .expected = {T_("1 + "), Frn({T_("2")}, {T_("3 + cos(90)")})}},

            // "[1, 2\frac{}{}"
            {.id = "bracket-comma-trailing-frac",
             .input = branch({Br({EN("1"), EV({N("2"), Frac({}, {})})}, false)}),
             .expected = {Pn(PK::Bracket, false, {T_("1, "), Frn({T_("2")}, {})})}},

            // "[1, 2, 3, 4\frac{}{}" arity-4 variant.
            {.id = "bracket-arity4-comma-trailing-frac",
             .input = branch({Br({EN("1"), EN("2"), EN("3"), EV({N("4"), Frac({}, {})})}, false)}),
             .expected = {Pn(PK::Bracket, false, {T_("1, 2, 3, "), Frn({T_("4")}, {})})}},

            // "[\frac, 2]" Latex first, then number. Bridge: latex to text.
            {.id = "bracket-latex-first",
             .input = branch({Br({EV({Frac({}, {})}), EN("2")}, true)}),
             .expected = {Pn(PK::Bracket, true, {Frn({}, {}), T_(", 2")})}},

            // "[2, \frac, 3, 4]" Latex middle, text before+after.
            {.id = "bracket-latex-middle-arity4",
             .input = branch({Br({EN("2"), EV({Frac({}, {})}), EN("3"), EN("4")}, true)}),
             .expected = {Pn(PK::Bracket, true, {T_("2, "), Frn({}, {}), T_(", 3, 4")})}},

            // "[1, \frac, \frac, 4]" Latex-latex bridge needs ", " between two latex nodes.
            {.id = "bracket-latex-latex-bridge",
             .input =
                 branch({Br({EN("1"), EV({Frac({}, {})}), EV({Frac({}, {})}), EN("4")}, true)}),
             .expected = {Pn(
                 PK::Bracket, true, {T_("1, "), Frn({}, {}), T_(", "), Frn({}, {}), T_(", 4")})}},

            // "[2, \frac{}{} + 5, 3]" Latex element has trailing op+number; outer
            // flush appends ", 3" onto recursion's Text(" + 5") (back-merge).
            {.id = "bracket-latex-with-suffix-op",
             .input =
                 branch({Br({EN("2"), EV({Frac({}, {}), Op_(OpId::Add), N("5")}), EN("3")}, true)}),
             .expected = {Pn(PK::Bracket, true, {T_("2, "), Frn({}, {}), T_(" + 5, 3")})}},

            // "[(4+5), (4+4)-\frac{}{}]" outer non-latex bundle followed by
            // vector element whose LatexSplit prefix emits its own Text.
            // emit_text MUST merge bundle Text with prefix Text.
            {.id = "bracket-paren-bundle-then-vec-latex-prefix",
             .input = branch({Br(
                 {Pp({EV({N("4"), Op_(OpId::Add), N("5")})}),
                  EV({Pp({EV({N("4"), Op_(OpId::Add), N("4")})}), Op_(OpId::Sub), Frac({}, {})})},
                 true)}),
             .expected = {Pn(PK::Bracket, true, {T_("(4 + 5), (4 + 4) - "), Frn({}, {})})}},

            // "[2, (\frac{3}{4})]" element 1 is a ParenToken (grouping) whose
            // own descendant has latex. Outer ParenSplit recurses and emits
            // a nested ParenNode inside the bundle.
            {.id = "bracket-nested-paren-with-latex",
             .input = branch({Br({EN("2"), Pp({EV({Frac({N("3")}, {N("4")})})})}, true)}),
             .expected = {Pn(
                 PK::Bracket,
                 true,
                 {T_("2, "), Pn(PK::Paren, true, {Frn({T_("3")}, {T_("4")})})})}},

            // "[(2+3)+\frac{}{}]" arity-1 vector element with paren-prefix
            // before binary op + Frac. LatexSplit prefix carries the Paren
            // token through tokens_to_text + emit_text.
            {.id = "bracket-vec-latex-with-paren-prefix-arity1",
             .input = branch({Br(
                 {EV({Pp({EV({N("2"), Op_(OpId::Add), N("3")})}), Op_(OpId::Add), Frac({}, {})})},
                 true)}),
             .expected = {Pn(PK::Bracket, true, {T_("(2 + 3) + "), Frn({}, {})})}},

            // "[2, [\frac{3}{4}+5], 6]" element 1 is a ParenToken whose inner
            // element is a vector with latex+text suffix. Tests deep nesting
            // through outer ParenSplit -> inner ParenSplit recursion.
            {.id = "bracket-deep-nested-paren-bracket-latex",
             .input = branch({Br(
                 {EN("2"), Br({EV({Frac({N("3")}, {N("4")}), Op_(OpId::Add), N("5")})}), EN("6")},
                 true)}),
             .expected = {Pn(
                 PK::Bracket,
                 true,
                 {T_("2, "),
                  Pn(PK::Bracket, true, {Frn({T_("3")}, {T_("4")}), T_(" + 5")}),
                  T_(", 6")})}},

            // The renderer draws a script's base from the node's left row, so a logarithm
            // that did not carry its own would be drawn with an empty base slot next to a
            // loose "log" -- which is what the editor showed before fold_script claimed it.
            {.id = "log-base-fills-the-script-base",
             .input = p::tokenize("log_{2}8"),
             .expected = {Ln(LK::Subscript, {T_("log")}, {T_("2")}), T_("8")}},

            // -- Call cases (CallToken lowered render-only to Op(symbol) + Paren) --
            // "mean([2, \frac{1}{2}])": latex inside a function call must render
            // structurally. Input via tokenize so has_call / has_latex_descendant are
            // set as in real use; the symbol "x̄" rides the paren's prefix as text.
            {.id = "call-with-latex-arg",
             .input = p::tokenize("mean([2, \\frac{1}{2}])"),
             .expected =
                 {T_("x̄"),
                  Pn(PK::Paren,
                     true,
                     {Pn(PK::Bracket, true, {T_("2, "), Frn({T_("1")}, {T_("2")})})})}},
        };

        for (const auto &tc : build_nodes_cases) {
            test_detail::with_case(ctx, std::string("build_math_nodes :: ") + tc.id, [&] {
                const auto got = p::build_math_nodes(tc.input);
                EXPECT_EQ(ctx, got, tc.expected);
            });
        }
    }

    test_detail::with_case(ctx, "variant :: bare numbers all arm 0", [&] {
        auto branch = p::tokenize("[1, 2, 3]");
        const auto &col = std::get<p::ParenToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, col.elements.size(), 3u);
        for (std::size_t i = 0; i < 3; ++i) {
            EXPECT_EQ(ctx, col.elements[i].index(), 0u);
        }
    });

    test_detail::with_case(ctx, "variant :: unary plus stays arm 1 (UnaryPlus preserved)", [&] {
        auto branch = p::tokenize("[+3]");
        const auto &col = std::get<p::ParenToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, col.elements[0].index(), 1u);
        const auto &row = std::get<std::vector<p::Token>>(col.elements[0]);
        EXPECT_EQ(ctx, row.size(), 2u);
        EXPECT_EQ(ctx, row[0].kind, p::TokenKind::Op);
        EXPECT_EQ(ctx, row[1].kind, p::TokenKind::Number);
    });

    test_detail::with_case(ctx, "variant :: unary minus is arm 1", [&] {
        auto branch = p::tokenize("[-5]");
        const auto &col = std::get<p::ParenToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, col.elements[0].index(), 1u);
    });

    test_detail::with_case(ctx, "variant :: expression is arm 1", [&] {
        auto branch = p::tokenize("[1+2]");
        const auto &col = std::get<p::ParenToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, col.elements[0].index(), 1u);
    });

    test_detail::with_case(ctx, "variant :: single latex element is arm 0", [&] {
        auto branch = p::tokenize("[\\frac{1}{2}]");
        const auto &col = std::get<p::ParenToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, col.elements[0].index(), 0u);
        EXPECT_EQ(ctx, std::get<p::Token>(col.elements[0]).kind, p::TokenKind::Latex);
    });

    test_detail::with_case(ctx, "variant :: nested collection element is arm 0", [&] {
        auto branch = p::tokenize("[(1,2)]");
        const auto &col = std::get<p::ParenToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, col.elements[0].index(), 0u);
        EXPECT_EQ(ctx, std::get<p::Token>(col.elements[0]).kind, p::TokenKind::Paren);
    });

    test_detail::with_case(ctx, "variant :: empty element is arm 1 empty vector", [&] {
        auto branch = p::tokenize("[1,]");
        const auto &col = std::get<p::ParenToken>(branch.tokens[0].data);
        EXPECT_EQ(ctx, col.elements.size(), 2u);
        EXPECT_EQ(ctx, col.elements[0].index(), 0u);
        EXPECT_EQ(ctx, col.elements[1].index(), 1u);
        EXPECT_TRUE(ctx, std::get<std::vector<p::Token>>(col.elements[1]).empty());
    });

    test_detail::with_case(ctx, "round-trip :: list of signed numbers", [&] {
        EXPECT_EQ(ctx, p::tokens_to_text(p::tokenize("[+5, -3]").tokens), std::string("[+5, -3]"));
    });

    test_detail::with_case(ctx, "round-trip :: list of bare numbers", [&] {
        EXPECT_EQ(
            ctx, p::tokens_to_text(p::tokenize("[1, 2, 3]").tokens), std::string("[1, 2, 3]"));
    });

    test_detail::with_case(
        ctx, "variant :: arm 0 and arm 1 wrapping same token are not equal", [&] {
            // Canonicalization invariant: a single-Token element MUST be stored in arm 0.
            // An arm-1 wrapping of the same Token is a different variant alternative and
            // does NOT compare equal — locks the invariant so tests catch construction-site
            // drift.
            p::ParenElement arm_zero{N("1")};
            p::ParenElement arm_one{std::vector<Token>{N("1")}};
            EXPECT_TRUE(ctx, !(arm_zero == arm_one));
        });

    // =========================================================================
    // CharToken equality
    // =========================================================================
    test_detail::with_case(ctx, "CharToken :: equal same value", [&] {
        Token a{TokenKind::Char, CharToken{'a'}};
        Token b{TokenKind::Char, CharToken{'a'}};
        Token c{TokenKind::Char, CharToken{'b'}};
        EXPECT_TRUE(ctx, a == b);
        EXPECT_TRUE(ctx, !(a == c));
    });

    // =========================================================================
    // OpId::Assign tokenization
    // =========================================================================
    test_detail::with_case(ctx, "tokenize :: '=' -> Op(Assign)", [&] {
        auto r = p::tokenize("=");
        EXPECT_TRUE(ctx, r.tokens.size() == 1);
        EXPECT_TRUE(ctx, r.tokens[0].kind == TokenKind::Op);
        EXPECT_TRUE(ctx, std::get<OpToken>(r.tokens[0].data).op_id == OpId::Assign);
    });

    test_detail::with_case(ctx, "tokenize :: '==' -> Equal", [&] {
        auto r = p::tokenize("==");
        EXPECT_TRUE(ctx, r.tokens.size() == 1);
        EXPECT_TRUE(ctx, std::get<OpToken>(r.tokens[0].data).op_id == OpId::Equal);
    });

    // =========================================================================
    // CharToken free-text fallback (Task 3)
    // =========================================================================
    test_detail::with_case(ctx, "tokenize :: '∑' -> one Number token value='∑'", [&] {
        auto sm = p::tokenize("∑"); // U+2211, 3 UTF-8 bytes \xE2\x88\x91
        EXPECT_TRUE(ctx, sm.tokens.size() == 1);
        EXPECT_TRUE(ctx, sm.tokens[0].kind == TokenKind::Number);
        EXPECT_TRUE(ctx, std::get<NumberToken>(sm.tokens[0].data).value == "∑");
    });

    test_detail::with_case(ctx, "tokenize :: 'sin' -> one Op token", [&] {
        auto sin = p::tokenize("sin");
        EXPECT_TRUE(ctx, sin.tokens.size() == 1 && sin.tokens[0].kind == TokenKind::Op);
    });

    // =========================================================================
    // CharToken as operand + flat-text render arms (Task 4)
    // =========================================================================
    test_detail::with_case(ctx, "char operand :: lone 'A' shunts to single Char", [&] {
        auto rpn1 = tcalc::eval::shunting_yard(p::tokenize("A").tokens);
        EXPECT_TRUE(ctx, rpn1.size() == 1 && rpn1[0].kind == TokenKind::Char);
    });

    test_detail::with_case(ctx, "char operand :: token_text(Char 'a') == \"a\"", [&] {
        Token ch{TokenKind::Char, CharToken{'a'}};
        EXPECT_TRUE(ctx, p::token_text(ch) == "a");
    });

    test_detail::with_case(ctx, "const :: token_text(Const Pi) == \"π\"", [&] {
        p::Token t{p::TokenKind::Const, p::ConstToken{tcalc::consts::ConstId::Pi}, 0, 1};
        EXPECT_TRUE(ctx, p::token_text(t) == "π");
    });

    // =========================================================================
    // token_flat_text :: Pow/Subscript flat display strips the script braces
    // =========================================================================
    // Flat text is history's FLAT-mode display string (never re-tokenized), so
    // the 2D {} are dropped: 2^{3} shows as 2^3, 2_{3} as 2_3.
    test_detail::with_case(ctx, "flat_text :: Pow strips braces to base^exp", [&] {
        auto branch = p::tokenize("2^{3}");
        EXPECT_EQ(ctx, p::tokens_to_flat_text(branch.tokens), std::string("2^3"));
    });

    test_detail::with_case(ctx, "flat_text :: Subscript strips braces to base_sub", [&] {
        auto branch = p::tokenize("2_{3}");
        EXPECT_EQ(ctx, p::tokens_to_flat_text(branch.tokens), std::string("2_3"));
    });

    // A Pow base that is itself a Pow is still grouped by wrap_side, so the flat
    // display keeps the (2^3)^2 grouping: "2^{3}^{2}" -> "{2^3}^2".
    test_detail::with_case(ctx, "flat_text :: Pow chain groups the Pow base", [&] {
        auto branch = p::tokenize("2^{3}^{2}");
        EXPECT_EQ(ctx, p::tokens_to_flat_text(branch.tokens), std::string("{2^3}^2"));
    });

    // Sum/Prod always show braced limits (both scripts keep their {}).
    test_detail::with_case(ctx, "flat_text :: sum -> glyph with braced limits", [&] {
        const auto branch = p::tokenize("\\sum_{n=1}^{5}");
        EXPECT_EQ(ctx, p::token_flat_text(branch.tokens.at(0)), std::string("Σ_{n=1}^{5}"));
    });
}
