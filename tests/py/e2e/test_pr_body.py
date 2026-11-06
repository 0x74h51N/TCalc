# The Breaking answer as the release workflow reads it: the script, a body on stdin, its output
import subprocess
import sys
from pathlib import Path

import pytest
from pytest import param

ROOT = Path(__file__).parents[3]
SCRIPT = ROOT / "scripts" / "pr_body.py"
TEMPLATE = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")


# body, what the script prints
@pytest.mark.parametrize(
    "body, answer",
    [
        param("**Breaking:** yes", "yes", id="yes"),
        param("a\r\n**Breaking:** YES, history\r\nb", "yes", id="yes with what is lost"),
        param("**Breaking:** no", "no", id="no"),
        param("**Breaking:** yes or no", "no", id="both words on the line"),
        param("<!--\n**Breaking:** yes\n-->", "no", id="only in a comment"),
        param("```\n**Breaking:** yes\n```", "no", id="only in a quote"),
        param("merged before the line existed", "no", id="no line"),
        param(TEMPLATE, "no", id="template left as it is"),
        param(
            TEMPLATE.replace("**Breaking:** no", "**Breaking:** yes, a theme loses its colors"),
            "yes",
            id="template answered yes",
        ),
    ],
)
def test_breaking(body: str, answer: str) -> None:
    done = subprocess.run(
        [sys.executable, SCRIPT], input=body, capture_output=True, text=True, check=False
    )
    assert (done.returncode, done.stdout.strip()) == (0, answer)
