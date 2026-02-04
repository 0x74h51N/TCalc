#include "parser/pub/parser.hpp"

#include <cctype>
#include <string>
#include <utility>

namespace tcalc::parser {

using namespace tcalc::ops;

namespace detail {

inline unsigned char as_uchar(char c) {
    return static_cast<unsigned char>(c);
}

std::string_view scan_number(std::string_view s, std::size_t start, std::size_t &out_next) {
    const std::size_t n = s.size();
    std::size_t i = start;
    bool saw_digit = false;

    while (i < n && std::isdigit(as_uchar(s[i])) != 0) {
        saw_digit = true;
        ++i;
    }

    if (i < n && s[i] == '.') {
        ++i;
        while (i < n && std::isdigit(as_uchar(s[i])) != 0) {
            saw_digit = true;
            ++i;
        }
    }

    if (!saw_digit) {
        return {};
    }

    if (i < n && (s[i] == 'e' || s[i] == 'E')) {
        std::size_t j = i + 1;
        if (j < n && (s[j] == '+' || s[j] == '-')) {
            ++j;
        }
        const std::size_t exp_start = j;
        while (j < n && std::isdigit(as_uchar(s[j])) != 0) {
            ++j;
        }
        if (j != exp_start) {
            i = j;
        }
    }

    out_next = i;
    return s.substr(start, i - start);
}

const OpSpec *match_op(std::string_view s, std::size_t i, std::size_t &out_len) {
    const std::string_view rest = s.substr(i);
    const OpSpec *best = nullptr;
    std::size_t best_len = 0;

    for (const auto &entry : kTokenTable) {
        if (entry.token.empty()) {
            continue;
        }
        if (entry.token.size() <= best_len) {
            continue;
        }
        if (rest.starts_with(entry.token)) {
            best = entry.spec;
            best_len = entry.token.size();
        }
    }
    out_len = best_len;
    return best;
}

/// Returns final expect_operand state after tokenizing
bool tokenize_core(
    std::string_view expression,
    std::vector<Token> &tokens,
    std::size_t base_offset = 0,
    bool expect_operand = true) {
    if (expression.empty()) {
        return expect_operand;
    }

    std::size_t i = 0;
    const std::size_t n = expression.size();

    while (i < n) {
        const unsigned char c = static_cast<unsigned char>(expression[i]);

        if (std::isspace(c) != 0) {
            ++i;
            continue;
        }

        const std::size_t tok_start = base_offset + i;

        if (expression[i] == '(') {
            tokens.push_back(
                Token{
                    .kind = TokenKind::LParen,
                    .start_pos = tok_start,
                    .end_pos = tok_start + 1,
                });
            ++i;
            expect_operand = true;
            continue;
        }

        if (expression[i] == ')') {
            tokens.push_back(
                Token{
                    .kind = TokenKind::RParen,
                    .start_pos = tok_start,
                    .end_pos = tok_start + 1,
                });
            ++i;
            expect_operand = false;
            continue;
        }

        std::size_t len = 0;
        const OpSpec *spec = match_op(expression, i, len);
        if (spec != nullptr && len != 0) {
            // Convert binary +/- to unary when expecting an operand
            if (spec->id == OpId::Add && expect_operand) {
                spec = op_spec(OpId::UnaryPlus);
            }
            if (spec->id == OpId::Sub && expect_operand) {
                spec = op_spec(OpId::Negate);
            }

            tokens.push_back(
                Token{
                    .kind = TokenKind::Op,
                    .op_id = spec->id,
                    .start_pos = tok_start,
                    .end_pos = tok_start + len,
                });
            i += len;
            expect_operand = (spec->arity != Arity::Postfix);
            continue;
        }

        if (std::isdigit(c) != 0 || expression[i] == '.') {
            std::size_t next = i;
            const std::string_view sv = detail::scan_number(expression, i, next);

            if (!sv.empty()) {
                std::string number(sv);
                std::size_t tok_end = base_offset + next;

                if (next < n && (expression[next] == 'i' || expression[next] == 'I')) {
                    number.push_back('i');
                    ++next;
                    tok_end = base_offset + next;
                }

                tokens.push_back(
                    Token{
                        .kind = TokenKind::Number,
                        .op_id = OpId::Count,
                        .value = std::move(number),
                        .start_pos = tok_start,
                        .end_pos = tok_end,
                    });
                i = next;
                expect_operand = false;
                continue;
            }
        }

        const std::size_t start = i;
        while (i < n) {
            const unsigned char cc = static_cast<unsigned char>(expression[i]);
            if (std::isspace(cc) != 0) {
                break;
            }

            if (expression[i] == '(' || expression[i] == ')') {
                break;
            }

            std::size_t op_len = 0;
            if (match_op(expression, i, op_len) != nullptr && op_len != 0) {
                break;
            }
            ++i;
        }

        if (start == i) {
            ++i;
            continue;
        }

        const std::string_view chunk = expression.substr(start, i - start);
        tokens.push_back(
            Token{
                .kind = TokenKind::Number,
                .op_id = OpId::Count,
                .value = std::string(chunk),
                .start_pos = tok_start,
                .end_pos = base_offset + i,
            });
        expect_operand = false;
    }
    return expect_operand;
}

} // namespace detail

namespace {

std::string_view
extract_brace_content(std::string_view s, std::size_t start, std::size_t &out_end) {
    if (start >= s.size() || s[start] != '{') {
        return {};
    }

    int depth = 1;
    std::size_t i = start + 1;
    const std::size_t content_start = i;

    while (i < s.size() && depth > 0) {
        if (s[i] == '{') {
            ++depth;
        } else if (s[i] == '}') {
            --depth;
        }
        ++i;
    }

    if (depth != 0) {
        return {};
    }

    out_end = i;
    return s.substr(content_start, i - content_start - 1);
}

struct MatchLatexArgs {
    std::string_view s;
    std::size_t i;

    ExprKind *out_kind;
    std::string_view *out_left;
    std::string_view *out_right;
    std::size_t *out_end;
};
constexpr std::size_t kFracLen = 5;
constexpr std::size_t kPowLen = 4;

bool match_latex_expr(const MatchLatexArgs &args) {
    const std::string_view rest = args.s.substr(args.i);

    std::size_t prefix_len = 0;

    if (rest.starts_with("\\frac")) {
        *args.out_kind = ExprKind::Frac;
        prefix_len = kFracLen;
    } else if (rest.starts_with("\\pow")) {
        *args.out_kind = ExprKind::Pow;
        prefix_len = kPowLen;
    } else {
        return false;
    }

    const std::size_t pos = args.i + prefix_len;

    std::size_t after_left = 0;
    const std::string_view left = extract_brace_content(args.s, pos, after_left);

    if (after_left == 0) {
        return false;
    }

    std::size_t after_right = 0;
    const std::string_view right = extract_brace_content(args.s, after_left, after_right);

    if (after_right == 0) {
        return false;
    }

    *args.out_left = left;
    *args.out_right = right;
    *args.out_end = after_right;
    return true;
}

} // namespace

TokenizeResult tokenize(std::string_view s) {
    TokenizeResult result;
    result.tokens.reserve(s.size() / 2);

    std::size_t i = 0;
    bool expect_operand = true;

    while (i < s.size()) {
        if (s[i] == '\\') {
            ExprKind out_kind = ExprKind::Frac;
            std::string_view out_left{};
            std::string_view out_right{};
            std::size_t out_end = 0;

            if (match_latex_expr({s, i, &out_kind, &out_left, &out_right, &out_end})) {
                const std::size_t expr_idx = result.tokens.size();
                result.expr_indices.push_back(expr_idx);

                result.tokens.push_back(
                    Token{
                        .kind = TokenKind::Expr,
                        .expr_kind = out_kind,
                        .left_tokens = tokenize(out_left).tokens,
                        .right_tokens = tokenize(out_right).tokens,
                        .start_pos = i,
                        .end_pos = out_end,
                    });
                i = out_end;
                expect_operand = false; // Expr acts as operand, next token is operator
                continue;
            }

            ++i;
            continue;
        }

        const std::size_t start = i;
        while (i < s.size() && s[i] != '\\') {
            ++i;
        }

        expect_operand =
            detail::tokenize_core(s.substr(start, i - start), result.tokens, start, expect_operand);
    }

    return result;
}

namespace detail {
std::vector<Token> normalize(const std::vector<Token> &raw) {
    std::vector<Token> normalized;
    normalized.reserve(raw.size());

    const auto is_plus_minus = [](const Token &t) -> bool {
        return t.kind == TokenKind::Op && (t.op_id == OpId::Add || t.op_id == OpId::Sub);
    };

    const auto ends_operand = [](const Token &t) -> bool {
        return t.kind == TokenKind::Number || t.kind == TokenKind::RParen ||
               t.kind == TokenKind::Expr ||
               (t.kind == TokenKind::Op && op_spec(t.op_id)->arity == Arity::Postfix);
    };

    const auto starts_operand = [](const Token &t) -> bool {
        return t.kind == TokenKind::Number || t.kind == TokenKind::LParen ||
               t.kind == TokenKind::Expr ||
               (t.kind == TokenKind::Op && op_spec(t.op_id)->arity == Arity::Unary);
    };

    for (const auto &tok : raw) {
        if (!normalized.empty()) {
            const Token &last = normalized.back();

            if (is_plus_minus(tok) && is_plus_minus(last)) {
                if (last.op_id == OpId::Sub) {
                    // - followed by - => +
                    // - followed by + => keep -
                    if (tok.op_id == OpId::Sub) {
                        normalized.back().op_id = OpId::Add;
                    }
                    continue;
                }

                // + followed by +/- => replace with last
                normalized.back() = tok;
                continue;
            }

            if (ends_operand(last) && starts_operand(tok)) {
                // Implicit multiplication: "2(3)" -> "2 * (3)"
                normalized.push_back(Token{TokenKind::Op, OpId::Mul});
            }
        }

        normalized.push_back(tok);
    }

    return normalized;
}

} // namespace detail

//
// Shunting Yard Algorithm
// RIP Edsger Dijkstra
//
// Ref: https://www.sunshine2k.de/articles/coding/shuntingyardalgorithm/shunting_yard_algorithm.html
//
std::vector<Token> shunting_yard(const std::vector<Token> &tokens) {
    std::vector<Token> normalized = detail::normalize(tokens);

    std::vector<Token> output;
    std::vector<Token> operator_stack;

    for (const Token &tok : normalized) {
        switch (tok.kind) {
        case TokenKind::Number:
        case TokenKind::Expr:
            output.push_back(tok);
            break;
        case TokenKind::LParen:
            operator_stack.push_back(tok);
            break;
        case TokenKind::RParen:
            while (!operator_stack.empty() && operator_stack.back().kind != TokenKind::LParen) {
                output.push_back(operator_stack.back());
                operator_stack.pop_back();
            }
            if (!operator_stack.empty() && operator_stack.back().kind == TokenKind::LParen) {
                operator_stack.pop_back();
            }
            break;
        case TokenKind::Op: {
            const OpSpec *op = op_spec(tok.op_id);

            while (!operator_stack.empty() && operator_stack.back().kind == TokenKind::Op) {
                const OpSpec *top = op_spec(operator_stack.back().op_id);

                if (op->id == OpId::Negate && top->arity == Arity::Unary &&
                    top->id != OpId::Negate) {
                    break;
                }

                const bool pop_left =
                    (op->associativity == Assoc::Left) && (op->precedence <= top->precedence);
                const bool pop_right =
                    (op->associativity == Assoc::Right) && (op->precedence < top->precedence);
                if (!(pop_left || pop_right)) {
                    break;
                }

                output.push_back(operator_stack.back());
                operator_stack.pop_back();
            }

            operator_stack.push_back(tok);
            break;
        }
        }
    }

    while (!operator_stack.empty()) {
        if (operator_stack.back().kind == TokenKind::Op) {
            output.push_back(operator_stack.back());
        }
        operator_stack.pop_back();
    }

    return output;
}

} // namespace tcalc::parser
