#include "parser/pub/parser.hpp"

#include <cctype>
#include <string>
#include <utility>


namespace tcalc::ops {

namespace {

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

} // namespace

std::vector<Token> tokenize(std::string_view expression) {
    std::vector<Token> tokens;
    if (expression.empty()) {
        return tokens;
    }

    std::size_t i = 0;
    const std::size_t n = expression.size();
    bool expect_operand = true;

    while (i < n) {
        const unsigned char c = static_cast<unsigned char>(expression[i]);

        if (std::isspace(c) != 0) {
            ++i;
            continue;
        }

        if (expression[i] == '(') {
            tokens.push_back(Token{TokenKind::LParen});
            ++i;
            expect_operand = true;
            continue;
        }

        if (expression[i] == ')') {
            tokens.push_back(Token{TokenKind::RParen});
            ++i;
            expect_operand = false;
            continue;
        }

        std::size_t len = 0;
        const OpSpec *spec = match_op(expression, i, len);
        if (spec != nullptr && len != 0) {
            if (spec->id == OpId::Sub && expect_operand) {
                spec = op_spec(OpId::Negate);
            }
            tokens.push_back(Token{TokenKind::Op, spec->id});
            i += len;
            expect_operand = (spec->arity != Arity::Postfix);
            continue;
        }

        if (std::isdigit(c) != 0 || expression[i] == '.') {
            std::size_t next = i;
            const std::string_view sv = scan_number(expression, i, next);

            if (!sv.empty()) {
                i = next;
                std::string number(sv);

                if (i < n && (expression[i] == 'i' || expression[i] == 'I')) {
                    number.push_back('i');
                    ++i;
                }
                tokens.push_back(Token{TokenKind::Number, OpId::Count, std::move(number)});
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
        tokens.push_back(Token{TokenKind::Number, OpId::Count, std::string(chunk)});
        expect_operand = false;
    }

    return tokens;
}

std::vector<Token> normalize(const std::vector<Token> &raw) {
    std::vector<Token> normalized;
    normalized.reserve(raw.size());

    const auto is_plus_minus = [](const Token &t) -> bool {
        return t.kind == TokenKind::Op && (t.op_id == OpId::Add || t.op_id == OpId::Sub);
    };

    const auto ends_operand = [](const Token &t) -> bool {
        return t.kind == TokenKind::Number || t.kind == TokenKind::RParen ||
               (t.kind == TokenKind::Op && op_spec(t.op_id)->arity == Arity::Postfix);
    };

    const auto starts_operand = [](const Token &t) -> bool {
        return t.kind == TokenKind::Number || t.kind == TokenKind::LParen ||
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
                normalized.push_back(Token{TokenKind::Op, OpId::Mul});
            }
        }

        normalized.push_back(tok);
    }

    return normalized;
}

//
// Shunting Yard Algorithm
// RIP Edsger Dijkstra
//
// Ref: https://www.sunshine2k.de/articles/coding/shuntingyardalgorithm/shunting_yard_algorithm.html
//
std::vector<Token> shunting_yard(const std::vector<Token> &tokens) {
    std::vector<Token> normalized = normalize(tokens);

    std::vector<Token> output;
    std::vector<Token> operator_stack;

    for (const Token &tok : normalized) {
        switch (tok.kind) {
        case TokenKind::Number:
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

} // namespace tcalc::ops
