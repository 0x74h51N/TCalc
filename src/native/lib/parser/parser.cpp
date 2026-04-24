/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "parser/pub/parser.hpp"

#include <algorithm>
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

void classify_paren(TokensBranch &result, ParenStacks &paren_stacks, std::size_t tok_idx) {
    auto &paren = std::get<ParenToken>(result.tokens[tok_idx].data);
    paren.pair_idx = kNoMatch;

    auto &stack = paren_stacks[static_cast<std::size_t>(paren.kind)];
    if (paren.type == ParenType::Open) {
        result.open_paren_indices.push_back(tok_idx);
        stack.push_back(tok_idx);
        return;
    }

    result.close_paren_indices.push_back(tok_idx);
    if (stack.empty()) {
        return;
    }

    const std::size_t pair = stack.back();
    stack.pop_back();

    paren.pair_idx = pair;
    std::get<ParenToken>(result.tokens[pair].data).pair_idx = tok_idx;
}

bool tokenize_core(
    std::string_view expression,
    TokensBranch &result,
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
            tokens.push_back(
                Token{
                    .kind = TokenKind::Paren,
                    .data = ParenToken{p->type, p->kind},
                    .start_pos = tok_start,
                    .end_pos = tok_start + 1});
            classify_paren(result, paren_stacks, tok_idx);

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

    LatexKind *out_kind;
    OpId *out_op_id;
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
    *args.out_op_id = matched->opid;
    const std::size_t pos = args.i + prefix_len;

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

TokensBranch tokenize(std::string_view s) {
    TokensBranch result;
    result.tokens.reserve(s.size() / 2);
    detail::ParenStacks paren_stacks;

    std::size_t i = 0;
    const std::size_t n = s.size();
    bool expect_operand = true;

    while (i < n) {
        if (s[i] == '\\') {
            LatexKind out_kind = LatexKind::Frac;
            OpId op_id = OpId::Div;
            std::string_view out_left{};
            std::string_view out_right{};
            std::size_t out_end = 0;

            if (match_latex_expr({s, i, &out_kind, &op_id, &out_left, &out_right, &out_end})) {
                const std::size_t expr_idx = result.tokens.size();
                result.latex_indices.push_back(expr_idx);
                auto left_branch = tokenize(out_left);
                auto right_branch = tokenize(out_right);

                LatexToken latex{
                    .kind = out_kind,
                    .op_id = op_id,
                    .left = std::move(left_branch.tokens),
                    .right = std::move(right_branch.tokens)};

                result.tokens.push_back(
                    Token{
                        .kind = TokenKind::Latex,
                        .data = std::move(latex),
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

OperandSplit
split_operand(std::span<const Token> tokens, std::size_t begin, std::size_t end, bool lead) {
    if (begin >= end) {
        return {};
    }

    std::size_t split_at = 0;

    if (lead) {
        const Token &first = tokens[begin];
        if (first.kind == TokenKind::Paren) {
            const auto &paren = std::get<ParenToken>(first.data);
            if (paren.type == ParenType::Open) {
                split_at = (paren.pair_idx != kNoMatch) ? (paren.pair_idx + 1) : end;
                return {
                    tokens.subspan(begin, split_at - begin),
                    tokens.subspan(split_at, end - split_at),
                };
            }
        }
        if (first.kind == TokenKind::Number) {
            return {
                tokens.subspan(begin, 1),
                tokens.subspan(begin + 1, end - begin - 1),
            };
        }
        return {{}, tokens.subspan(begin, end - begin)};
    }

    const Token &last = tokens[end - 1];
    if (last.kind == TokenKind::Paren) {
        const auto &paren = std::get<ParenToken>(last.data);
        if (paren.type == ParenType::Close) {
            split_at = (paren.pair_idx != kNoMatch) ? paren.pair_idx : begin;
            return {
                tokens.subspan(begin, split_at - begin),
                tokens.subspan(split_at, end - split_at),
            };
        }
    }
    if (last.kind == TokenKind::Number) {
        return {
            tokens.subspan(begin, end - begin - 1),
            tokens.subspan(end - 1, 1),
        };
    }
    return {tokens.subspan(begin, end - begin), {}};
}

std::optional<StructuralSplit> structural_split(const TokensBranch &branch) {
    if (branch.latex_indices.empty()) {
        return std::nullopt;
    }

    const auto &tokens = branch.tokens;
    const std::size_t n = tokens.size();
    const std::size_t expr_first = branch.latex_indices.front();

    std::optional<std::size_t> candidate;
    for (const std::size_t ind : branch.open_paren_indices) {
        if (ind >= expr_first) {
            continue;
        }
        const std::size_t pair = std::get<ParenToken>(tokens[ind].data).pair_idx;
        if (pair == kNoMatch || pair > expr_first) {
            candidate = ind;
            break;
        }
    }

    if (candidate.has_value()) {
        const std::size_t c = *candidate;
        const ParenToken open_tok = std::get<ParenToken>(tokens[c].data);
        const std::size_t pair = open_tok.pair_idx;
        const bool has_close = pair != kNoMatch;

        const std::span<const Token> span{tokens};

        ParenSplit split;
        split.idx = c;
        split.open_tok = open_tok;
        split.prefix = span.subspan(0, c);

        if (has_close) {
            split.close_tok = std::get<ParenToken>(tokens[pair].data);
            split.left = span.subspan(c + 1, pair - c - 1);
            split.suffix = span.subspan(pair + 1, n - pair - 1);
        } else {
            split.close_tok.reset();
            split.left = span.subspan(c + 1, n - c - 1);
        }

        return StructuralSplit{split};
    }

    const std::size_t idx = expr_first;
    const LatexToken &latex_tok = std::get<LatexToken>(tokens[idx].data);

    ExprSplit split;
    split.idx = idx;
    split.kind = latex_tok.kind;

    const std::span<const Token> span{tokens};

    if (!latex_tok.left.empty()) {
        split.prefix = span.subspan(0, idx);
        split.left = latex_tok.left;
    } else {
        std::tie(split.prefix, split.left) = split_operand(span, 0, idx, /*lead=*/false);
    }

    if (!latex_tok.right.empty()) {
        split.right = latex_tok.right;
        split.suffix = span.subspan(idx + 1, n - idx - 1);
    } else {
        std::tie(split.right, split.suffix) = split_operand(span, idx + 1, n, /*lead=*/true);
    }

    return StructuralSplit{split};
}

namespace detail {

// Sorted latex/open-paren positions inside a span. Indices are local to the span.
// Used for descending into latex_tok.left / .right vectors that carry their own pair_idx
// and for recursing over sub-ranges of an already-classified branch.
struct SpanIndices {
    std::vector<std::size_t> latex;
    std::vector<std::size_t> open_paren;
};

SpanIndices scan_span(std::span<const Token> tokens) {
    SpanIndices ix;
    for (std::size_t i = 0; i < tokens.size(); ++i) {
        const auto &tok = tokens[i];
        if (tok.kind == TokenKind::Latex) {
            ix.latex.push_back(i);
        } else if (tok.kind == TokenKind::Paren) {
            const auto &p = std::get<ParenToken>(tok.data);
            if (p.type == ParenType::Open) {
                ix.open_paren.push_back(i);
            }
        }
    }
    return ix;
}

void build_row(
    std::span<const Token> all,
    const SpanIndices &ix,
    std::size_t begin,
    std::size_t end,
    bool after_node,
    std::vector<MathNode> &out);

inline void push_text(
    std::span<const Token> all,
    std::size_t from,
    std::size_t to,
    bool after_node,
    std::vector<MathNode> &out) {
    if (from >= to) {
        return;
    }
    out.emplace_back(TextNode{tokens_to_text(all.subspan(from, to - from), after_node)});
}

void build_row(
    std::span<const Token> all,
    const SpanIndices &ix,
    std::size_t begin,
    std::size_t end,
    bool after_node,
    std::vector<MathNode> &out) {

    std::size_t cursor = begin;
    bool ctx_after_node = after_node;

    while (cursor < end) {
        auto lat_it = std::lower_bound(ix.latex.begin(), ix.latex.end(), cursor);
        if (lat_it == ix.latex.end() || *lat_it >= end) {
            push_text(all, cursor, end, ctx_after_node, out);
            return;
        }
        const std::size_t expr_first = *lat_it;

        std::size_t paren_at = kNoMatch;
        auto op_it = std::lower_bound(ix.open_paren.begin(), ix.open_paren.end(), cursor);
        for (; op_it != ix.open_paren.end() && *op_it < expr_first; ++op_it) {
            const std::size_t pair = std::get<ParenToken>(all[*op_it].data).pair_idx;
            if (pair == kNoMatch || pair > expr_first) {
                paren_at = *op_it;
                break;
            }
        }

        if (paren_at != kNoMatch) {
            const std::size_t c = paren_at;
            const ParenToken &open = std::get<ParenToken>(all[c].data);
            const std::size_t pair = open.pair_idx;
            const bool has_close = pair != kNoMatch;

            push_text(all, cursor, c, ctx_after_node, out);

            ParenNode pn{open.kind, has_close, {}};
            const std::size_t inner_end = has_close ? pair : end;
            build_row(all, ix, c + 1, inner_end, /*after_node=*/false, pn.children);
            out.emplace_back(std::move(pn));

            ctx_after_node = true;
            if (!has_close) {
                return;
            }
            cursor = pair + 1;
            continue;
        }

        const std::size_t idx = expr_first;
        const LatexToken &lt = std::get<LatexToken>(all[idx].data);

        std::size_t prefix_end = 0;
        std::size_t right_end = 0;
        bool left_from_latex = !lt.left.empty();
        bool right_from_latex = !lt.right.empty();

        if (left_from_latex) {
            prefix_end = idx;
        } else {
            auto [pfx, lft] = split_operand(all, cursor, idx, /*lead=*/false);
            (void)lft;
            prefix_end = cursor + pfx.size();
        }

        if (right_from_latex) {
            right_end = idx + 1;
        } else {
            auto [rhs, suf] = split_operand(all, idx + 1, end, /*lead=*/true);
            (void)suf;
            right_end = idx + 1 + rhs.size();
        }

        push_text(all, cursor, prefix_end, ctx_after_node, out);

        LatexNode ln{lt.kind, {}, {}};

        if (left_from_latex) {
            const SpanIndices inner_ix = scan_span(lt.left);
            build_row(lt.left, inner_ix, 0, lt.left.size(), /*after_node=*/false, ln.left);
        } else {
            build_row(all, ix, prefix_end, idx, /*after_node=*/false, ln.left);
        }

        if (right_from_latex) {
            const SpanIndices inner_ix = scan_span(lt.right);
            build_row(lt.right, inner_ix, 0, lt.right.size(), /*after_node=*/false, ln.right);
        } else if (right_end > idx + 1) {
            build_row(all, ix, idx + 1, right_end, /*after_node=*/false, ln.right);
        }

        out.emplace_back(std::move(ln));
        ctx_after_node = true;
        cursor = right_end;
    }
}

} // namespace detail

std::vector<MathNode> build_math_nodes(const TokensBranch &branch, bool after_node) {
    std::vector<MathNode> out;
    if (branch.tokens.empty()) {
        return out;
    }
    detail::SpanIndices ix;
    ix.latex = branch.latex_indices;
    ix.open_paren = branch.open_paren_indices;
    detail::build_row(branch.tokens, ix, 0, branch.tokens.size(), after_node, out);
    return out;
}

TokensBranch classify_tokens(std::vector<Token> tokens) {
    TokensBranch result;
    result.tokens = std::move(tokens);
    detail::ParenStacks paren_stacks{};

    for (std::size_t i = 0; i < result.tokens.size(); ++i) {
        const auto &tok = result.tokens[i];
        switch (tok.kind) {
        case TokenKind::Latex:
            result.latex_indices.push_back(i);
            break;
        case TokenKind::Paren:
            detail::classify_paren(result, paren_stacks, i);
            break;
        default:
            break;
        }
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
        if (t.kind == TokenKind::Number || t.kind == TokenKind::Latex ||
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
        if (t.kind == TokenKind::Number || t.kind == TokenKind::Latex ||
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
        case TokenKind::Latex:
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

std::string format_expr_str(LatexKind kind, std::string_view left, std::string_view right) {
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

            if constexpr (std::is_same_v<T, LatexToken>) {
                return format_expr_str(
                    data.kind, tokens_to_text(data.left), tokens_to_text(data.right));
            } else if constexpr (std::is_same_v<T, NumberToken>) {
                return std::string(data.value);
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

std::string spaced(std::string_view text) {
    std::string out;
    out.reserve(text.size() + 2);
    out.push_back(' ');
    out.append(text);
    out.push_back(' ');
    return out;
}

std::string space_binary_op(ops::OpId op_id, const std::string &text, const bool &after_node) {
    if (is_binary_op(op_id) || (after_node && is_unary_as_binary(op_id))) {
        return spaced(text);
    }
    return text;
}

std::string tokens_to_text(std::span<const Token> tokens, const bool &after_node) {
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
    if (tok.kind == TokenKind::Latex) {
        const auto &latex = std::get<LatexToken>(tok.data);

        const auto wrap_side = [](const std::vector<Token> &side) {
            auto text = tokens_to_flat_text(side);
            // Wrap in braces if the side contains ops or latex
            for (const auto &t : side) {
                if (t.kind == TokenKind::Op || t.kind == TokenKind::Latex) {
                    constexpr char open = paren_symbol(ParenType::Open, ParenKind::Brace);
                    constexpr char close = paren_symbol(ParenType::Close, ParenKind::Brace);
                    return open + text + close;
                }
            }
            return text;
        };

        std::string out;
        out.append(wrap_side(latex.left));
        out.append(spaced(ops::op_spec(latex.op_id)->symbol));
        out.append(wrap_side(latex.right));
        return out;
    }
    return token_text(tok);
}

std::string tokens_to_flat_text(const std::vector<Token> &tokens) {
    std::string out;
    out.reserve(tokens.size() * 4);

    for (std::size_t i = 0; i < tokens.size(); ++i) {
        const auto &tok = tokens[i];

        if (tok.kind == TokenKind::Op) {
            const auto &op = std::get<OpToken>(tok.data);
            out.append(space_binary_op(op.op_id, token_text(tok), 0));
        } else {
            out.append(token_flat_text(tok));
        }
    }

    return out;
}

} // namespace tcalc::parser
