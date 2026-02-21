#pragma once

#include <vector>

#include "parser/pub/parser.hpp"

namespace tcalc::parser::detail {

// Fold +/-, insert implicit multiplication, and normalize adjacency.
std::vector<Token> normalize(std::vector<Token> raw);
// Scan a number literal starting at index and report the end position.
std::string_view scan_number(std::string_view s, std::size_t start, std::size_t &out_next);

} // namespace tcalc::parser::detail
