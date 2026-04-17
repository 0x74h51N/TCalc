#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import pytest

from tests.benchmark.conftest import HISTORY_SCENARIO_COUNTS
from tests.benchmark.expressions import (
    EXPR_NO_ALIAS,
    EXPR_WITH_ALIAS,
    PAREN_EXPRESSIONS,
    PIPELINE_EXPRESSIONS,
    RENDER_EXPRESSIONS,
    make_history_init_func,
    make_incremental_edit_func,
    make_multi_edit_func,
    make_normalize_func,
    make_pipeline_func,
    make_render_func,
    make_shunting_func,
    make_tokenize_func,
    setup_widget,
)

from .conftest import run_flamegraph


@pytest.mark.parametrize("name", list(PIPELINE_EXPRESSIONS))
def test_calc_pipeline_flame(name: str):
    run_flamegraph(make_pipeline_func(PIPELINE_EXPRESSIONS[name]), group="Calc Pipeline", name=name)


@pytest.mark.flamegraph
@pytest.mark.parametrize("name", list(PIPELINE_EXPRESSIONS))
def test_tokenize_flame(name: str):
    run_flamegraph(make_tokenize_func(PIPELINE_EXPRESSIONS[name]), group="Tokenize", name=name)


@pytest.mark.flamegraph
@pytest.mark.parametrize("name", list(PIPELINE_EXPRESSIONS))
def test_shunting_yard_flame(name: str):
    run_flamegraph(make_shunting_func(PIPELINE_EXPRESSIONS[name]), group="Shunting Yard", name=name)


@pytest.mark.flamegraph
@pytest.mark.parametrize("name", list(PAREN_EXPRESSIONS))
def test_tokenize_paren_flame(name: str):
    run_flamegraph(
        make_tokenize_func(PAREN_EXPRESSIONS[name]), group="Tokenize Paren-LaTeX", name=name
    )


@pytest.mark.flamegraph
@pytest.mark.parametrize("name", list(RENDER_EXPRESSIONS))
def test_expression_render_flame(qapp, name: str):
    run_flamegraph(
        make_render_func(qapp, RENDER_EXPRESSIONS[name]),
        group="Expression Render",
        name=name,
    )


@pytest.mark.flamegraph
@pytest.mark.parametrize("name", list(RENDER_EXPRESSIONS))
def test_single_edit_flame(qapp, name: str):
    widget = setup_widget(qapp, RENDER_EXPRESSIONS[name])
    try:
        run_flamegraph(
            make_incremental_edit_func(qapp, widget),
            group="UI Integration - Single Edit",
            name=name,
        )
    finally:
        widget.close()
        widget.deleteLater()
        qapp.processEvents()


@pytest.mark.flamegraph
@pytest.mark.parametrize("name", list(RENDER_EXPRESSIONS))
def test_multi_edit_flame(qapp, name: str):
    widget = setup_widget(qapp, RENDER_EXPRESSIONS[name])
    try:
        run_flamegraph(
            make_multi_edit_func(qapp, widget, num_steps=5),
            group="UI Integration - Multi Edit",
            name=name,
        )
    finally:
        widget.close()
        widget.deleteLater()
        qapp.processEvents()


@pytest.mark.flamegraph
@pytest.mark.parametrize("name", list(EXPR_NO_ALIAS))
def test_normalize_no_alias_flame(qapp, name: str):
    run_flamegraph(
        make_normalize_func(qapp, EXPR_NO_ALIAS[name]),
        group="Normalize",
        name=f"no_alias_{name}",
    )


@pytest.mark.flamegraph
@pytest.mark.parametrize("name", list(EXPR_WITH_ALIAS))
def test_normalize_with_alias_flame(qapp, name: str):
    run_flamegraph(
        make_normalize_func(qapp, EXPR_WITH_ALIAS[name]),
        group="Normalize",
        name=f"with_alias_{name}",
    )


@pytest.mark.flamegraph
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_history_init_flame(qapp, history_seed):
    run_flamegraph(
        make_history_init_func(qapp),
        group="History Init - Full Load",
        name=history_seed,
    )


@pytest.mark.flamegraph
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_history_init_math_mode_flame(qapp, history_seed):
    run_flamegraph(
        make_history_init_func(qapp, math_mode=True),
        group="History Init - Full Load (math)",
        name=history_seed,
    )


@pytest.mark.flamegraph
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_history_first_paint_flame(qapp, history_seed):
    run_flamegraph(
        make_history_init_func(qapp, first_paint_only=True),
        group="History First Paint",
        name=history_seed,
    )


@pytest.mark.flamegraph
@pytest.mark.parametrize("history_seed", list(HISTORY_SCENARIO_COUNTS), indirect=True)
def test_history_first_paint_math_mode_flame(qapp, history_seed):
    run_flamegraph(
        make_history_init_func(qapp, math_mode=True, first_paint_only=True),
        group="History First Paint (math)",
        name=history_seed,
    )
