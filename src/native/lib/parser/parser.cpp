/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

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

inline void push_number(
    std::vector<Token> &tokens, std::size_t start, std::size_t end, std::string number_str) {
    tokens.push_back(
        Token{
            .kind = TokenKind::Number,
            .data = NumberToken{std::move(number_str)},
            .start_pos = start,
            .end_pos = end,
        });
}

inline constexpr auto kParenKindCount = static_cast<std::size_t>(ParenKind::Bracket) + 1;
using ParenStacks = std::array<std::vector<std::size_t>, kParenKindCount>;

/// Returns final expect_operand state after tokenizing
bool tokenize_core(
    std::string_view expression,
    TokenizeResult &result,
    ParenStacks &paren_stacks,
    std::size_t base_offset = 0,
    bool expect_operand = true) {
    if (expression.empty()) {
        return expect_operand;
    }

    auto &tokens = result.tokens;
    std::size_t i = 0;
    const std::size_t n = expression.size();

    while (i < n) {
        const unsigned char c = static_cast<unsigned char>(expression[i]);

        if (std::isspace(c) != 0) {
            ++i;
            continue;
        }

        const std::size_t tok_start = base_offset + i;

        if (auto p = match_paren(expression[i])) {
            const std::size_t tok_idx = tokens.size();
            auto &stack = paren_stacks[static_cast<std::size_t>(p->kind)];

            if (p->type == ParenType::Open) {
                result.open_paren_indices.push_back(tok_idx);
                tokens.push_back(
                    Token{
                        .kind = TokenKind::Paren,
                        .data = ParenToken{p->type, p->kind},
                        .start_pos = tok_start,
                        .end_pos = tok_start + 1});
                stack.push_back(tok_idx);
            } else {
                result.close_paren_indices.push_back(tok_idx);
                std::size_t pair = kNoMatch;
                if (!stack.empty()) {
                    pair = stack.back();
                    stack.pop_back();
                    std::get<ParenToken>(tokens[pair].data).pair_idx = tok_idx;
                }
                tokens.push_back(
                    Token{
                        .kind = TokenKind::Paren,
                        .data = ParenToken{p->type, p->kind, pair},
                        .start_pos = tok_start,
                        .end_pos = tok_start + 1});
            }

            expect_operand = (p->type == ParenType::Open);
            ++i;
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
                    .data = OpToken{spec->id},
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
                if (next < n && (expression[next] == 'i' || expression[next] == 'I')) {
                    number.push_back('i');
                    ++next;
                }
                push_number(tokens, tok_start, base_offset + next, std::move(number));
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

            if (match_paren(expression[i]).has_value())
                break;

            std::size_t op_len = 0;
            if (match_op(expression, i, op_len) != nullptr && op_len != 0)
                break;

            ++i;
        }

        if (start == i) {
            ++i;
            continue;
        }

        const std::string_view chunk = expression.substr(start, i - start);
        std::string number = std::string(chunk);
        push_number(tokens, tok_start, base_offset + i, std::move(number));
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

bool match_latex_expr(const MatchLatexArgs &args) {
    const std::string_view rest = args.s.substr(args.i);

    std::size_t prefix_len = 0;
    const LatexEntry *matched = nullptr;

    for (const auto &entry : kLatexExprs) {
        if (rest.starts_with(entry.symbol)) {
            matched = &entry;
            prefix_len = entry.symbol.size();
            break;
        }
    }

    if (matched == nullptr) {
        return false;
    }

    *args.out_kind = matched->kind;
    const std::size_t pos = args.i + prefix_len;

    // Braces are optional - \frac alone is valid (empty left/right)
    std::size_t after_left = pos;
    const std::string_view left = extract_brace_content(args.s, pos, after_left);

    std::size_t after_right = after_left;
    const std::string_view right = extract_brace_content(args.s, after_left, after_right);

    *args.out_left = left;
    *args.out_right = right;
    *args.out_end = after_right;
    return true;
}

} // namespace

TokenizeResult tokenize(std::string_view s) {
    TokenizeResult result;
    result.tokens.reserve(s.size() / 2);
    detail::ParenStacks paren_stacks;

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
                std::vector<Token> left_tokens = tokenize(out_left).tokens;
                std::vector<Token> right_tokens = tokenize(out_right).tokens;

                ExprToken expr_tok{
                    .kind = out_kind,
                    .left = std::move(left_tokens),
                    .right = std::move(right_tokens)};

                result.tokens.push_back(
                    Token{
                        .kind = TokenKind::Expr,
                        .data = TokenData{expr_tok},
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

        expect_operand = detail::tokenize_core(
            s.substr(start, i - start), result, paren_stacks, start, expect_operand);
    }

    return result;
}

namespace detail {
std::vector<Token> normalize(std::vector<Token> raw) {
    std::vector<Token> normalized;
    normalized.reserve(raw.size());

    const auto is_plus_minus = [](const Token &t) -> bool {
        if (t.kind != TokenKind::Op)
            return false;
        const auto &op_token = std::get<OpToken>(t.data);
        return op_token.op_id == OpId::Add || op_token.op_id == OpId::Sub;
    };

    const auto ends_operand = [](const Token &t) -> bool {
        if (t.kind == TokenKind::Number || t.kind == TokenKind::Expr ||
            t.kind == TokenKind::Paren) {
            if (t.kind == TokenKind::Paren) {
                const auto &paren = std::get<ParenToken>(t.data);
                return paren.type == ParenType::Close;
            }
            return true;
        }
        if (t.kind == TokenKind::Op) {
            const auto &op_token = std::get<OpToken>(t.data);
            return op_spec(op_token.op_id)->arity == Arity::Postfix;
        }
        return false;
    };

    const auto starts_operand = [](const Token &t) -> bool {
        if (t.kind == TokenKind::Number || t.kind == TokenKind::Expr ||
            t.kind == TokenKind::Paren) {
            if (t.kind == TokenKind::Paren) {
                const auto &paren = std::get<ParenToken>(t.data);
                return paren.type == ParenType::Open;
            }
            return true;
        }
        if (t.kind == TokenKind::Op) {
            const auto &op_token = std::get<OpToken>(t.data);
            return op_spec(op_token.op_id)->arity == Arity::Unary;
        }
        return false;
    };

    for (auto &tok : raw) {
        if (!normalized.empty()) {
            const Token &last = normalized.back();

            if (is_plus_minus(tok) && is_plus_minus(last)) {
                auto &last_op = std::get<OpToken>(normalized.back().data);
                const auto &curr_op = std::get<OpToken>(tok.data);

                if (last_op.op_id == OpId::Sub) {
                    if (curr_op.op_id == OpId::Sub) {
                        last_op.op_id = OpId::Add;
                    }
                    continue;
                }

                last_op = curr_op; // + followed by +/- => replace with last
                continue;
            }

            if (ends_operand(last) && starts_operand(tok)) {
                // Implicit multiplication: "2(3)" -> "2 * (3)"
                normalized.push_back(
                    Token{.kind = TokenKind::Op, .data = TokenData{OpToken{OpId::Mul}}});
            }
        }

        normalized.push_back(std::move(tok));
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
    output.reserve(normalized.size());
    std::vector<Token> operator_stack;

    for (Token &tok : normalized) {
        switch (tok.kind) {
        case TokenKind::Number:
        case TokenKind::Expr:
            output.push_back(std::move(tok));
            break;
        case TokenKind::Paren: {
            const ParenToken &ptok = std::get<ParenToken>(tok.data);
            if (ptok.type == ParenType::Open) {
                operator_stack.push_back(tok);
            } else {
                while (!operator_stack.empty()) {
                    const Token &top = operator_stack.back();
                    if (top.kind == TokenKind::Paren) {
                        const ParenToken &top_ptok = std::get<ParenToken>(top.data);
                        if (top_ptok.type == ParenType::Open)
                            break;
                    }
                    output.push_back(top);
                    operator_stack.pop_back();
                }

                if (!operator_stack.empty()) {
                    operator_stack.pop_back();
                }
            }
            break;
        }
        case TokenKind::Op: {
            const OpToken &op_tok = std::get<OpToken>(tok.data);
            const OpSpec *op = op_spec(op_tok.op_id);

            while (!operator_stack.empty() && operator_stack.back().kind == TokenKind::Op) {
                const OpToken &top_tok = std::get<OpToken>(operator_stack.back().data);
                const OpSpec *top = op_spec(top_tok.op_id);

                if (op->id == OpId::Negate && top->arity == Arity::Unary &&
                    top->id != OpId::Negate) {
                    break;
                }

                const bool pop_left =
                    (op->associativity == Assoc::Left) && (op->precedence <= top->precedence);
                const bool pop_right =
                    (op->associativity == Assoc::Right) && (op->precedence < top->precedence);
                if (!(pop_left || pop_right))
                    break;

                output.push_back(operator_stack.back());
                operator_stack.pop_back();
            }

            operator_stack.push_back(tok);
            break;
        }
        }
    }

    while (!operator_stack.empty()) {
        output.push_back(operator_stack.back());
        operator_stack.pop_back();
    }

    return output;
}

// =============================================================================
// Text transformations
//
//
//  token_text
//  tokens_to_text
//  space_binary_op
// =============================================================================

namespace {

/// Display symbol for unary ops whose internal symbol (u-, u+) differs from
/// what the user sees (-, +).
constexpr std::string_view unary_display_symbol(ops::OpId id) {
    switch (id) {
    case ops::OpId::Negate:
        return ops::op_spec(ops::OpId::Sub)->symbol;
    case ops::OpId::UnaryPlus:
        return ops::op_spec(ops::OpId::Add)->symbol;
    default:
        return {};
    }
}

inline bool is_binary_op(ops::OpId op_id) {
    const auto *spec = ops::op_spec(op_id);
    return spec != nullptr && spec->arity == ops::Arity::Binary;
}

inline bool is_unary_as_binary(ops::OpId op_id) {
    return op_id == ops::OpId::Negate || op_id == ops::OpId::UnaryPlus;
}

} // namespace

std::string format_expr_str(ExprKind kind, std::string_view left, std::string_view right) {
    constexpr char open = paren_symbol(ParenType::Open, ParenKind::Brace);
    constexpr char close = paren_symbol(ParenType::Close, ParenKind::Brace);
    const auto sym = kLatexSymbols[static_cast<std::size_t>(kind)];

    std::string out;
    out.reserve(sym.size() + left.size() + right.size() + 4);
    out.append(sym);
    out.push_back(open);
    out.append(left);
    out.push_back(close);
    out.push_back(open);
    out.append(right);
    out.push_back(close);
    return out;
}

std::string token_text(const Token &tok) {
    return std::visit(
        [](const auto &data) -> std::string {
            using T = std::decay_t<decltype(data)>;

            if constexpr (std::is_same_v<T, ExprToken>) {
                return format_expr_str(
                    data.kind, tokens_to_text(data.left), tokens_to_text(data.right));
            } else if constexpr (std::is_same_v<T, NumberToken>) {
                return data.value;
            } else if constexpr (std::is_same_v<T, OpToken>) {
                const auto display = unary_display_symbol(data.op_id);
                if (!display.empty()) {
                    return std::string(display);
                }
                const auto *spec = ops::op_spec(data.op_id);
                return spec ? std::string(spec->symbol) : std::string{};
            } else if constexpr (std::is_same_v<T, ParenToken>) {
                return std::string(1, paren_symbol(data.type, data.kind));
            }

            return {};
        },
        tok.data);
}

std::string space_binary_op(ops::OpId op_id, const std::string &text, const bool &after_node) {
    if (is_binary_op(op_id) || (after_node && is_unary_as_binary(op_id))) {
        std::string out;
        out.reserve(text.size() + 2);
        out.push_back(' ');
        out.append(text);
        out.push_back(' ');
        return out;
    }
    return text;
}

std::string tokens_to_text(const std::vector<Token> &tokens, const bool &after_node) {
    std::string out;
    out.reserve(tokens.size() * 4);

    for (std::size_t i = 0; i < tokens.size(); ++i) {
        const auto &tok = tokens[i];

        if (tok.kind == TokenKind::Op) {
            const auto &op = std::get<OpToken>(tok.data);
            // after_node only matters for the first token
            const bool node_ctx = i == 0 && after_node;
            out.append(space_binary_op(op.op_id, token_text(tok), node_ctx));
        } else {
            out.append(token_text(tok));
        }
    }

    return out;
}

std::string token_flat_text(const Token &tok) {
    if (tok.kind == TokenKind::Expr) {
        const auto &expr = std::get<ExprToken>(tok.data);
        const Token open_par{
            .kind = TokenKind::Paren,
            .data = ParenToken{ParenType::Open, ParenKind::Brace},
            .start_pos = 0,
            .end_pos = 1,
        };
        const Token close_par{
            .kind = TokenKind::Paren,
            .data = ParenToken{ParenType::Close, ParenKind::Brace},
            .start_pos = 1,
            .end_pos = 2,
        };
        const auto build_flat = [&](const std::vector<Token> &side) {
            std::string text;
            text.reserve(side.size() * 4);
            bool has_op = false;
            for (std::size_t i = 0; i < side.size(); ++i) {
                const auto &t = side[i];
                if (t.kind == TokenKind::Op) {
                    has_op = true;
                    text.append(
                        space_binary_op(std::get<OpToken>(t.data).op_id, token_text(t), i == 0));
                } else {
                    text.append(token_flat_text(t));
                }
            }

            if (has_op) {
                const auto &open = std::get<ParenToken>(open_par.data);
                const auto &close = std::get<ParenToken>(close_par.data);
                std::string wrapped;
                wrapped.reserve(text.size() + 2);
                wrapped.push_back(paren_symbol(open.type, open.kind));
                wrapped.append(text);
                wrapped.push_back(paren_symbol(close.type, close.kind));
                return wrapped;
            }

            return text;
        };

        auto left = build_flat(expr.left);
        auto right = build_flat(expr.right);
        const auto &entry = kLatexExprs[static_cast<std::size_t>(expr.kind)];
        const auto *spec = ops::op_spec(entry.opid);

        std::string out;
        out.reserve(left.size() + right.size() + spec->symbol.size() + 2);
        out.append(left);
        out.push_back(' ');
        out.append(spec->symbol);
        out.push_back(' ');
        out.append(right);
        return out;
    }
    return token_text(tok);
}

std::string tokens_to_flat_text(const std::vector<Token> &tokens, const bool &after_node) {
    std::string out;
    out.reserve(tokens.size() * 4);

    for (std::size_t i = 0; i < tokens.size(); ++i) {
        const auto &tok = tokens[i];

        if (tok.kind == TokenKind::Op) {
            const auto &op = std::get<OpToken>(tok.data);
            const bool node_ctx = i == 0 && after_node;
            out.append(space_binary_op(op.op_id, token_text(tok), node_ctx));
        } else {
            out.append(token_flat_text(tok));
        }
    }

    return out;
}

} // namespace tcalc::parser
