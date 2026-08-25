/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2025 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <pybind11/complex.h>
#include <pybind11/operators.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <string>
#include <utility>

#include "bindings.hpp"
#include "collection/collection.hpp"

namespace py = pybind11;

// Display cap shared by __repr__ and preview: past kReprThreshold a collection
// shows kHead leading and kTail trailing items, so a bulk-CSV collection (~M items)
// stays UI/REPL-friendly. Typed user lists up to the threshold display in full.
constexpr std::size_t kReprThreshold = 100;
constexpr std::size_t kHead = 4;
constexpr std::size_t kTail = 2;

/// Open/close glyph pair for a collection's kind.
constexpr std::pair<char, char> brackets(tcalc::CollectionKind kind) {
    return kind == tcalc::CollectionKind::List ? std::pair{'[', ']'} : std::pair{'(', ')'};
}

void bind_collection(py::module_ &m) {
    using K = tcalc::CollectionKind;

    auto coll = py::class_<tcalc::Collection, std::shared_ptr<tcalc::Collection>>(
        m, "Collection", "Evaluated collection value (List or Point of scalars).");

    py::enum_<K>(coll, "Kind").value("List", K::List).value("Point", K::Point);

    // No Python constructor: collections are produced by the evaluator, never built from
    // Python. Unpickling rebuilds through the C++ constructor in the __setstate__ below.
    coll.def_readonly("kind", &tcalc::Collection::kind)
        .def("__len__", [](const tcalc::Collection &c) { return c.items().size(); })
        .def(
            "__getitem__",
            [](const tcalc::Collection &c, std::ptrdiff_t i) -> py::object {
                const auto n = static_cast<std::ptrdiff_t>(c.items().size());
                if (i < 0)
                    i += n;
                if (i < 0 || i >= n)
                    throw py::index_error();
                return std::visit(
                    [](const auto &v) -> py::object { return py::cast(v); },
                    c.items()[static_cast<std::size_t>(i)]);
            })
        .def(
            "__iter__",
            [](const tcalc::Collection &c) {
                return py::make_iterator(c.items().begin(), c.items().end());
            },
            py::keep_alive<0, 1>())
        .def(
            "__eq__",
            [](const tcalc::Collection &a, const py::object &other) -> py::object {
                if (!py::isinstance<tcalc::Collection>(other)) {
                    return py::reinterpret_borrow<py::object>(Py_NotImplemented);
                }
                return py::cast(a == other.cast<tcalc::Collection>());
            })
        .def(
            "preview",
            [](const tcalc::Collection &c) {
                // Everything a caller needs to render one: the glyphs, and the
                // (head, tail) cap or None when every item is shown. No items copied.
                const auto [open, close] = brackets(c.kind);
                const bool capped = c.items().size() > kReprThreshold;
                py::object cap = py::none();
                if (capped)
                    cap = py::make_tuple(kHead, kTail);
                return py::make_tuple(std::string(1, open), std::string(1, close), cap);
            },
            "(open, close, cap) where cap is (head, tail) or None if all items show.")
        .def(
            "__repr__",
            [](const tcalc::Collection &c) {
                const auto [open, close] = brackets(c.kind);
                const auto fmt = [](const tcalc::CollectionItem &it) {
                    return py::cast<std::string>(py::repr(
                        std::visit([](const auto &v) -> py::object { return py::cast(v); }, it)));
                };

                std::string out;
                out.push_back(open);
                const std::size_t n = c.items().size();
                if (n <= kReprThreshold) {
                    for (std::size_t i = 0; i < n; ++i) {
                        if (i > 0)
                            out += ", ";
                        out += fmt(c.items()[i]);
                    }
                } else {
                    for (std::size_t i = 0; i < kHead; ++i) {
                        if (i > 0)
                            out += ", ";
                        out += fmt(c.items()[i]);
                    }
                    out += ", ..., ";
                    for (std::size_t i = n - kTail; i < n; ++i) {
                        if (i > n - kTail)
                            out += ", ";
                        out += fmt(c.items()[i]);
                    }
                }
                out.push_back(close);
                return out;
            })
        .def(
            py::pickle(
                [](const tcalc::Collection &c) { return py::make_tuple(c.kind, c.items()); },
                [](const py::tuple &t) {
                    if (t.size() != 2) {
                        throw std::runtime_error("Invalid Collection state");
                    }
                    auto kind = t[0].cast<K>();
                    auto items = t[1].cast<std::vector<tcalc::CollectionItem>>();
                    return std::make_shared<tcalc::Collection>(kind, std::move(items));
                }));
}
