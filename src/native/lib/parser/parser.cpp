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

struct ParenExtent {
    std::size_t end_pos;
    std::vector<std::size_t> top_commas;
    bool closed;
};

/// Scan paren extent with kind-strict stack matching. Stops at the first close
/// that doesn't match the top of the stack (unclosed outer). Commas at the
/// outermost level (stack.size()==1) become element separators.
ParenExtent scan_paren_extent(std::string_view s, std::size_t open_pos) {
    ParenExtent ext{open_pos, {}, false};
    if (open_pos >= s.size())
        return ext;

    std::vector<char> stack;
    stack.push_back(s[open_pos]);

    std::size_t i = open_pos + 1;
    while (i < s.size()) {
        const char c = s[i];
        const ParenRole role = paren_role_of(c);

        if (role == ParenRole::Open) {
            stack.push_back(c);
        } else if (role == ParenRole::Close) {
            // A close pops down to its matching open: unmatched intervening
            // opens are left for recursive tokenize on the inner substring to
            // recover as unclosed groups. If no matching open exists in the
            // stack, the close is stray and ends the extent unclosed.
            const char want_open = paren_symbol(/*is_open=*/true, paren_kind_of(c));
            const auto it = std::find(stack.rbegin(), stack.rend(), want_open);
            if (it == stack.rend()) {
                ext.end_pos = i;
                ext.closed = false;
                return ext;
            }
            stack.erase(it.base() - 1, stack.end());
            if (stack.empty()) {
                ext.end_pos = i;
                ext.closed = true;
                return ext;
            }
        } else if (c == ',' && stack.size() == 1) {
            ext.top_commas.push_back(i);
        }
        ++i;
    }
    ext.end_pos = s.size();
    return ext;
}

// Shared by build_paren_token / build_call_token: split the paren interior on
// top-level commas and recursively tokenize each slice into ParenElements.
struct BuiltElements {
    std::vector<ParenElement> elements;
    bool has_latex_descendant = false;
};

BuiltElements
build_paren_elements(std::string_view s, std::size_t open_pos, const ParenExtent &ext) {
    const std::size_t inner_begin = open_pos + 1;
    const std::size_t inner_end = ext.end_pos;

    BuiltElements out;
    const bool inner_empty = (inner_begin >= inner_end) && ext.top_commas.empty();
    if (!inner_empty) {
        std::size_t seg_begin = inner_begin;
        out.elements.reserve(ext.top_commas.size() + 1);
        auto push_slice = [&](std::string_view slice) {
            auto branch = tokenize(slice);
            if (!out.has_latex_descendant &&
                (!branch.latex_indices.empty() || branch.has_latex_descendant)) {
                out.has_latex_descendant = true;
            }
            if (branch.tokens.size() == 1) {
                out.elements.emplace_back(std::move(branch.tokens.front()));
            } else {
                out.elements.emplace_back(std::move(branch.tokens));
            }
        };
        for (const std::size_t comma_pos : ext.top_commas) {
            push_slice(s.substr(seg_begin, comma_pos - seg_begin));
            seg_begin = comma_pos + 1;
        }
        push_slice(s.substr(seg_begin, inner_end - seg_begin));
    }
    return out;
}

Token build_paren_token(
    std::string_view s, std::size_t open_pos, const ParenExtent &ext, ParenKind kind) {
    auto built = build_paren_elements(s, open_pos, ext);
    const std::size_t end_pos_excl = ext.closed ? ext.end_pos + 1 : ext.end_pos;
    return Token{
        TokenKind::Paren,
        ParenToken{
            kind,
            std::move(built.elements),
            /*has_open=*/true,
            /*has_close=*/ext.closed,
            built.has_latex_descendant},
        open_pos,
        end_pos_excl,
    };
}

Token build_call_token(
    std::string_view s,
    std::size_t open_pos,
    const ParenExtent &ext,
    tcalc::ops::OpId op_id,
    std::size_t func_start) {
    auto built = build_paren_elements(s, open_pos, ext);
    const std::size_t end_pos_excl = ext.closed ? ext.end_pos + 1 : ext.end_pos;
    return Token{
        TokenKind::Call,
        CallToken{
            op_id, std::move(built.elements), /*has_close=*/ext.closed, built.has_latex_descendant},
        func_start,
        end_pos_excl};
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

inline bool is_paren_char(char c) {
    return paren_role_of(c) != ParenRole::None;
}

// UTF-8 byte classification for the free-text fallback.
constexpr unsigned char kAsciiLimit = 0x80U;   // below this byte value is 7-bit ASCII
constexpr unsigned char kContByteMask = 0xC0U; // selects a byte's top two bits
constexpr unsigned char kContByteTag = 0x80U;  // 10xxxxxx marks a UTF-8 continuation byte

bool tokenize_core(
    std::string_view expression,
    TokensBranch &result,
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

        // Named constant (π, e, i, φ, τ) — matched whole before the single-letter
        // CharToken splitter so multi-char constants ("pi") do not split.
        {
            std::size_t clen = 0;
            if (const auto *cspec = tcalc::consts::match_const(expression, i, clen);
                cspec != nullptr) {
                tokens.push_back(
                    Token{
                        .kind = TokenKind::Const,
                        .data = ConstToken{cspec->id},
                        .start_pos = tok_start,
                        .end_pos = base_offset + i + clen});
                i += clen;
                expect_operand = false;
                continue;
            }
        }

        // Free text, one unit per token. An ASCII letter is a single-letter
        // variable (CharToken); adjacent letters become an implicit product via normalize.
        const unsigned char fc = static_cast<unsigned char>(expression[i]);
        if (std::isalpha(fc) != 0 && fc < kAsciiLimit) {
            tokens.push_back(
                Token{
                    .kind = TokenKind::Char,
                    .data = CharToken{static_cast<char>(fc)},
                    .start_pos = tok_start,
                    .end_pos = base_offset + i + 1});
            ++i;
            expect_operand = false;
            continue;
        }
        // Multibyte: consume the lead byte + its UTF-8 continuation bytes (10xxxxxx),
        // so any codepoint stays one NumberToken
        std::size_t cp_len = 1;
        while (i + cp_len < n && (static_cast<unsigned char>(expression[i + cp_len]) &
                                  kContByteMask) == kContByteTag) {
            ++cp_len;
        }
        push_number(
            tokens, tok_start, base_offset + i + cp_len, std::string(expression.substr(i, cp_len)));
        i += cp_len;
        expect_operand = false;
    }
    return expect_operand;
}
} // namespace detail

namespace {

inline std::vector<Token> element_tokens(const ParenElement &e) {
    if (e.index() == 0)
        return {std::get<Token>(e)};
    return std::get<std::vector<Token>>(e);
}

inline bool element_has_latex_descendant(const ParenElement &e) {
    auto check = [](const Token &t) {
        if (t.kind == TokenKind::Latex)
            return true;
        if (t.kind == TokenKind::Paren) {
            return std::get<ParenToken>(t.data).has_latex_descendant;
        }
        return false;
    };
    if (e.index() == 0)
        return check(std::get<Token>(e));
    for (const auto &t : std::get<std::vector<Token>>(e)) {
        if (check(t))
            return true;
    }
    return false;
}

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

inline Token make_stray_close(ParenKind kind, std::size_t pos) {
    return Token{
        TokenKind::Paren,
        ParenToken{
            kind,
            /*elements=*/{},
            /*has_open=*/false,
            /*has_close=*/true,
            /*has_latex_descendant=*/false},
        pos,
        pos + 1,
    };
}

} // namespace

TokensBranch tokenize(std::string_view s) {
    TokensBranch result;
    result.tokens.reserve(s.size() / 2);

    std::size_t i = 0;
    const std::size_t n = s.size();
    bool expect_operand = true;

    while (i < n) {
        const char c = s[i];
        const ParenRole role = paren_role_of(c);

        // 1) Paren open → build_paren_token
        if (role == ParenRole::Open) {
            const ParenKind kind = paren_kind_of(c);
            const auto ext = detail::scan_paren_extent(s, i);

            if (kind == ParenKind::Paren && !result.tokens.empty() &&
                result.tokens.back().kind == TokenKind::Op) {
                const auto &prev_op = std::get<OpToken>(result.tokens.back().data);
                if (const ops::OpSpec *sp = ops::op_spec(prev_op.op_id);
                    sp && ops::is_call_function(*sp)) {
                    const std::size_t func_start = result.tokens.back().start_pos;
                    const ops::OpId fop = prev_op.op_id;
                    result.tokens.pop_back();
                    auto call = detail::build_call_token(s, i, ext, fop, func_start);
                    if (std::get<CallToken>(call.data).has_latex_descendant)
                        result.has_latex_descendant = true;
                    result.tokens.push_back(std::move(call));
                    result.has_call = true;
                    i = ext.closed ? ext.end_pos + 1 : ext.end_pos;
                    expect_operand = false;
                    continue;
                }
            }

            const auto tok_idx = static_cast<TokenIndex>(result.tokens.size());
            result.paren_indices.push_back(tok_idx);
            auto tok = detail::build_paren_token(s, i, ext, kind);
            if (!result.has_latex_descendant &&
                std::get<ParenToken>(tok.data).has_latex_descendant) {
                result.has_latex_descendant = true;
            }
            result.tokens.push_back(std::move(tok));
            i = ext.closed ? ext.end_pos + 1 : ext.end_pos;
            expect_operand = false;
            continue;
        }

        // 2) Latex: '\'
        if (c == '\\') {
            LatexKind out_kind = LatexKind::Frac;
            OpId op_id = OpId::Div;
            std::string_view out_left{};
            std::string_view out_right{};
            std::size_t out_end = 0;

            if (match_latex_expr({s, i, &out_kind, &op_id, &out_left, &out_right, &out_end})) {
                const auto expr_idx = static_cast<TokenIndex>(result.tokens.size());
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
                expect_operand = false;
                continue;
            }

            ++i;
            continue;
        }

        // 3) Stray close
        if (role == ParenRole::Close) {
            const ParenKind kind = paren_kind_of(c);
            result.paren_indices.push_back(static_cast<TokenIndex>(result.tokens.size()));
            result.tokens.push_back(make_stray_close(kind, i));
            ++i;
            // A close-paren-style token acts as an operand for the next op:
            // the following '+' / '-' should be binary, not unary.
            expect_operand = false;
            continue;
        }

        // 4) Fallback: tokenize_core (ops, numbers, free text)
        const std::size_t start = i;
        while (i < s.size() && s[i] != '\\' && s[i] != '(' && s[i] != '[' && s[i] != '{' &&
               s[i] != ')' && s[i] != ']' && s[i] != '}') {
            ++i;
        }

        expect_operand =
            detail::tokenize_core(s.substr(start, i - start), result, start, expect_operand);
    }

    return result;
}

// ========================== Math Node Split and Creation =========================
//
// split_operand
// structural_split
// build_row
// build_math_nodes
// classify_tokens
//
// =============================================================================

OperandSplit
split_operand(std::span<const Token> tokens, TokenIndex begin, TokenIndex end, bool lead) {
    if (begin >= end) {
        return {};
    }

    if (lead) {
        const Token &first = tokens[begin];
        if (first.kind == TokenKind::Paren || first.kind == TokenKind::Number ||
            first.kind == TokenKind::Call || first.kind == TokenKind::Char ||
            first.kind == TokenKind::Const) {
            return {
                tokens.subspan(begin, 1),
                tokens.subspan(begin + 1, end - begin - 1),
            };
        }
        return {{}, tokens.subspan(begin, end - begin)};
    }

    const Token &last = tokens[end - 1];
    if (last.kind == TokenKind::Paren || last.kind == TokenKind::Number ||
        last.kind == TokenKind::Call || last.kind == TokenKind::Char ||
        last.kind == TokenKind::Const) {
        return {
            tokens.subspan(begin, end - begin - 1),
            tokens.subspan(end - 1, 1),
        };
    }
    return {tokens.subspan(begin, end - begin), {}};
}

std::optional<StructuralSplit> structural_split(const TokensBranch &branch) {
    if (branch.latex_indices.empty() && !branch.has_latex_descendant) {
        return std::nullopt;
    }

    const auto &tokens = branch.tokens;
    const auto n = static_cast<TokenIndex>(tokens.size());
    const std::span<const Token> span{tokens};

    const bool has_latex = !branch.latex_indices.empty();
    const TokenIndex latex_first = has_latex ? branch.latex_indices.front() : n;

    // First top-level ParenToken before latex_first that wraps a latex descendant.
    for (const TokenIndex idx : branch.paren_indices) {
        if (idx >= latex_first)
            break;
        const auto &ptok = std::get<ParenToken>(tokens[idx].data);
        if (!ptok.has_latex_descendant)
            continue;

        ParenSplit ps;
        ps.kind = ptok.kind;
        ps.has_open = ptok.has_open;
        ps.has_close = ptok.has_close;
        ps.prefix = span.subspan(0, idx);
        ps.elements = std::span<const ParenElement>{ptok.elements};
        ps.suffix = span.subspan(idx + 1, n - idx - 1);
        return StructuralSplit{ps};
    }

    if (!has_latex) {
        // has_latex_descendant=true but no qualifying paren found — defensive.
        return std::nullopt;
    }

    const TokenIndex idx = latex_first;
    const LatexToken &latex_tok = std::get<LatexToken>(tokens[idx].data);

    LatexSplit split;
    split.kind = latex_tok.kind;

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

// Append text to a children list, merging into a trailing TextNode if
// present. Keeps build_row output free of consecutive Text-Text runs so
// the Python _render_row's setText overwrites cleanly.
inline void emit_text(std::vector<MathNode> &out, std::string text) {
    if (text.empty())
        return;
    if (!out.empty() && std::holds_alternative<TextNode>(out.back().data)) {
        std::get<TextNode>(out.back().data).text += text;
    } else {
        out.emplace_back(TextNode{std::move(text)});
    }
}

void build_row(std::vector<MathNode> &out, TokensBranch branch, bool after_node) {
    while (true) {
        auto split = structural_split(branch);
        if (!split) {
            if (!branch.tokens.empty()) {
                emit_text(out, tokens_to_text(branch.tokens, after_node));
            }
            return;
        }

        std::optional<TokensBranch> next;
        std::visit(
            [&](const auto &s) {
                if (!s.prefix.empty()) {
                    emit_text(out, tokens_to_text(s.prefix, after_node));
                }

                using T = std::decay_t<decltype(s)>;
                if constexpr (std::is_same_v<T, ParenSplit>) {
                    ParenNode pn{s.kind, s.has_close, {}};
                    std::string pending_text;
                    bool last_was_latex = false;

                    auto flush_text = [&]() {
                        emit_text(pn.children, std::move(pending_text));
                        pending_text.clear();
                    };

                    for (std::size_t k = 0; k < s.elements.size(); ++k) {
                        if (element_has_latex_descendant(s.elements[k])) {
                            if (!pending_text.empty()) {
                                pending_text += ", ";
                            } else if (last_was_latex) {
                                pending_text = ", ";
                            }
                            flush_text();
                            build_row(
                                /*out=*/pn.children,
                                /*branch=*/classify_tokens(element_tokens(s.elements[k])),
                                /*after_node=*/false);
                            last_was_latex = true;
                        } else {
                            if (!pending_text.empty() || k > 0)
                                pending_text += ", ";
                            pending_text += tokens_to_text(element_tokens(s.elements[k]));
                            last_was_latex = false;
                        }
                    }
                    flush_text();
                    out.emplace_back(std::move(pn));
                } else {
                    LatexNode ln{s.kind, {}, {}};
                    if (!s.left.empty()) {
                        build_row(
                            /*out=*/ln.left,
                            /*branch=*/classify_tokens({s.left.begin(), s.left.end()}),
                            /*after_node=*/false);
                    }
                    if (!s.right.empty()) {
                        build_row(
                            /*out=*/ln.right,
                            /*branch=*/classify_tokens({s.right.begin(), s.right.end()}),
                            /*after_node=*/false);
                    }
                    out.emplace_back(std::move(ln));
                }

                if (!s.suffix.empty()) {
                    next = classify_tokens({s.suffix.begin(), s.suffix.end()});
                }
            },
            *split);

        after_node = true;
        if (!next) {
            return;
        }
        branch = std::move(*next);
    }
}

} // namespace detail

std::vector<MathNode> build_math_nodes(const TokensBranch &branch, bool after_node) {
    std::vector<MathNode> out;
    if (branch.tokens.empty()) {
        return out;
    }
    if (branch.has_call) {
        detail::build_row(
            out, classify_tokens(branch.tokens), after_node); // lower calls, then render
    } else {
        detail::build_row(out, branch, after_node); // hot path, unchanged
    }
    return out;
}

TokensBranch classify_tokens(std::vector<Token> tokens) {
    TokensBranch result;
    result.tokens.reserve(tokens.size() + 1);

    // Single pass building the token row + its latex/paren indices. A CallToken is lowered
    // (render-only) to Op(symbol) + Paren(args) so the existing Op-text / Paren / LaTeX
    // render path applies unchanged, no Call MathNode. has_latex_descendant is read off the
    // token (precomputed at tokenize), never rescanned.
    for (auto &tok : tokens) {
        switch (tok.kind) {
        case TokenKind::Call: {
            auto &c = std::get<CallToken>(tok.data);
            const bool hld = c.has_latex_descendant;
            result.tokens.push_back(
                Token{TokenKind::Op, OpToken{c.op_id}, tok.start_pos, tok.start_pos});
            const auto idx = static_cast<TokenIndex>(result.tokens.size());
            result.tokens.push_back(
                Token{
                    TokenKind::Paren,
                    ParenToken{
                        ParenKind::Paren, std::move(c.args), /*has_open=*/true, c.has_close, hld},
                    tok.start_pos,
                    tok.end_pos});
            result.paren_indices.push_back(idx);
            if (hld)
                result.has_latex_descendant = true;
            break;
        }
        case TokenKind::Latex: {
            const auto idx = static_cast<TokenIndex>(result.tokens.size());
            result.tokens.push_back(std::move(tok));
            result.latex_indices.push_back(idx);
            break;
        }
        case TokenKind::Paren: {
            const bool hld = std::get<ParenToken>(tok.data).has_latex_descendant;
            const auto idx = static_cast<TokenIndex>(result.tokens.size());
            result.tokens.push_back(std::move(tok));
            result.paren_indices.push_back(idx);
            if (hld)
                result.has_latex_descendant = true;
            break;
        }
        default:
            result.tokens.push_back(std::move(tok));
            break;
        }
    }

    return result;
}

// =============================================================================
//
// Evaluation layer, only shunting yard
// RPN and evaluation function calling in python side
//
// =============================================================================

namespace detail {
/**
 * Preprocesses tokens before the Shunting Yard
 *
 * Inserts implicit multiplication operators
 * Collapses consecutive '+' and '-' operators into a single sign
 */

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
            t.kind == TokenKind::Char || t.kind == TokenKind::Const) {
            return true;
        }
        if (t.kind == TokenKind::Paren) {
            return std::get<ParenToken>(t.data).has_close;
        }
        if (t.kind == TokenKind::Call) {
            return std::get<CallToken>(t.data).has_close;
        }
        if (t.kind == TokenKind::Op) {
            const auto &op_token = std::get<OpToken>(t.data);
            return op_spec(op_token.op_id)->arity == Arity::Postfix;
        }
        return false;
    };

    const auto starts_operand = [](const Token &t) -> bool {
        if (t.kind == TokenKind::Number || t.kind == TokenKind::Latex ||
            t.kind == TokenKind::Char || t.kind == TokenKind::Const) {
            return true;
        }
        if (t.kind == TokenKind::Paren) {
            return std::get<ParenToken>(t.data).has_open;
        }
        // TODO: Call is unreachable (nothing emits it yet); treated like
        // Paren — a call token always starts an operand (its head is the func name).
        if (t.kind == TokenKind::Call) {
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
        case TokenKind::Paren:
        case TokenKind::Call:
        case TokenKind::Char:
        case TokenKind::Const:
            output.push_back(std::move(tok));
            break;
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
    constexpr char open = paren_symbol(true, ParenKind::Brace);
    constexpr char close = paren_symbol(false, ParenKind::Brace);
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
                std::string out;
                if (data.has_open)
                    out.push_back(paren_symbol(true, data.kind));
                for (std::size_t i = 0; i < data.elements.size(); ++i) {
                    if (i > 0)
                        out += ", ";
                    out += tokens_to_text(element_tokens(data.elements[i]));
                }
                if (data.has_close)
                    out.push_back(paren_symbol(false, data.kind));
                return out;
            } else if constexpr (std::is_same_v<T, CallToken>) {
                std::string out;
                const auto *spec = ops::op_spec(data.op_id);
                if (spec)
                    out += spec->symbol;
                out.push_back(paren_symbol(true, ParenKind::Paren));
                for (std::size_t i = 0; i < data.args.size(); ++i) {
                    if (i > 0)
                        out += ", ";
                    out += tokens_to_text(element_tokens(data.args[i]));
                }
                if (data.has_close)
                    out.push_back(paren_symbol(false, ParenKind::Paren));
                return out;
            } else if constexpr (std::is_same_v<T, CharToken>) {
                return std::string(1, data.value);
            } else if constexpr (std::is_same_v<T, ConstToken>) {
                const auto *spec = tcalc::consts::const_spec(data.id);
                return spec ? std::string(spec->symbol) : std::string{};
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
        } else if (tok.kind == TokenKind::Number) {
            // NumberToken values that contain ',' come from tokenize_core's
            // fallback path (raw chunks). Comma is a collection separator --
            // emit ", " for each occurrence so multi-comma typing renders
            // with consistent spacing (space_binary_op pattern, unconditional).
            const auto text = token_text(tok);
            for (const char c : text) {
                out.push_back(c);
                if (c == ',')
                    out.push_back(' ');
            }
        } else {
            out.append(token_text(tok));
        }
    }

    return out;
}

// Flat text for a comma group: "(e0, e1, ...)" (or [ ]/{ }), each element flattened.
// Shared by the Paren and Call arms of token_flat_text.
std::string flat_group(
    ParenKind kind, const std::vector<ParenElement> &elements, bool has_open, bool has_close) {
    std::string out;
    if (has_open)
        out.push_back(paren_symbol(true, kind));
    for (std::size_t i = 0; i < elements.size(); ++i) {
        if (i > 0)
            out += ", ";
        out += tokens_to_flat_text(element_tokens(elements[i]));
    }
    if (has_close)
        out.push_back(paren_symbol(false, kind));
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
                    constexpr char open = paren_symbol(true, ParenKind::Brace);
                    constexpr char close = paren_symbol(false, ParenKind::Brace);
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
    if (tok.kind == TokenKind::Paren) {
        const auto &p = std::get<ParenToken>(tok.data);
        return flat_group(p.kind, p.elements, p.has_open, p.has_close);
    }
    if (tok.kind == TokenKind::Call) {
        const auto &c = std::get<CallToken>(tok.data);
        std::string out;
        if (const ops::OpSpec *spec = ops::op_spec(c.op_id))
            out.append(spec->symbol);
        out += flat_group(ParenKind::Paren, c.args, /*has_open=*/true, c.has_close);
        return out;
    }
    if (tok.kind == TokenKind::Char) {
        return std::string(1, std::get<CharToken>(tok.data).value);
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
