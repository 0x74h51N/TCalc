#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "*=false")


@pytest.fixture(autouse=True)
def _reset_canon_log(request):
    """Clear the per-test raw->canonical round-trip log before each test."""
    log = getattr(request.module, "CANON_LOG", None)
    if log is not None:
        log.clear()
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach the raw->canonical round-trips to the report only when the test
    fails, so a green run stays quiet and a red one shows where eval diverged."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    log = getattr(getattr(item, "module", None), "CANON_LOG", None)
    if log:
        body = "\n".join(f"{raw!r} -> {canonical!r}" for raw, canonical in log)
        report.sections.append(("raw -> canonical (eval round-trip)", body))
