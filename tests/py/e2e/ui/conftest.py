#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _test_themes(_user_themes, own_themes):
    """No test here reads a bundled theme or the user's folder."""
