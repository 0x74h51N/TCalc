# The description rules run as CI runs them: the script, a body on stdin, its exit code
import subprocess
import sys
from pathlib import Path

import pytest
from pytest import param

ROOT = Path(__file__).parents[4]
SCRIPT = ROOT / "scripts" / "pr_body.py"
TEMPLATE = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
HUMAN = "- [ ] Human agent"
AGENT = next(line for line in TEMPLATE.splitlines() if line.startswith("- [ ] Humble AI"))
FREE = next(line for line in TEMPLATE.splitlines() if line.startswith("- [ ] I am not a slave"))


def run(command: str, body: str, *title: str) -> int:
    done = subprocess.run(
        [sys.executable, SCRIPT, command, *title],
        input=body,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode


def filled(who: str = HUMAN, breaking: str = "**Breaking:** no") -> str:
    checklist = TEMPLATE[TEMPLATE.index("**Checklist:**") :].replace("- [ ]", "- [x]")
    head = TEMPLATE[: TEMPLATE.index("**Checklist:**")].replace("**Breaking:**", breaking)
    return (head + checklist).replace(who, who.replace("[ ]", "[x]"))


# body, exit code of check
@pytest.mark.parametrize(
    "body, code",
    [
        param(filled(), 0, id="human, no"),
        param(
            filled(breaking="**Breaking:** yes, a theme from 0.14 loses its colors"),
            0,
            id="yes with what is lost",
        ),
        param(filled(breaking="**Breaking:** No"), 0, id="either case"),
        param(filled().replace("\n", "\r\n"), 0, id="web editor line ends"),
        param(filled(AGENT), 0, id="humble servant"),
        param(filled(FREE), 1, id="free agent"),
        param(filled().replace(FREE, FREE.replace("[ ]", "[x]")), 1, id="human and free agent"),
        param("", 1, id="empty"),
        param(TEMPLATE, 1, id="template left as it is"),
        param(filled(breaking="**Breaking:**"), 1, id="breaking unanswered"),
        param(filled(breaking="**Breaking:** maybe"), 1, id="breaking is not yes or no"),
        param(filled(breaking="<!--\n**Breaking:** no\n-->"), 1, id="answer hidden in a comment"),
        param(filled(breaking="**Breaking:** no\n**Breaking:** yes"), 1, id="two answers"),
        param(filled().replace(HUMAN.replace("[ ]", "[x]"), HUMAN), 1, id="who is not ticked"),
        param(filled().replace(AGENT, AGENT.replace("[ ]", "[x]")), 1, id="both who boxes"),
        param(
            filled().replace("- [x] My change stays", "- [ ] My change stays"),
            1,
            id="a checklist box left empty",
        ),
    ],
)
def test_check(body: str, code: int) -> None:
    assert run("check", body, "docs: a title") == code


# title, exit code of check
@pytest.mark.parametrize(
    "title, code",
    [
        param("docs: a title", 0, id="no word"),
        param("docs: marmalade for all", 1, id="the word"),
        param("docs: MARMALADE", 1, id="the word in capitals"),
    ],
)
def test_trap_word_in_title(title: str, code: int) -> None:
    assert run("check", filled(), title) == code


# body, exit code of breaking
@pytest.mark.parametrize(
    "body, code",
    [
        param("**Breaking:** yes", 0, id="yes"),
        param("a\r\n**Breaking:** YES, history\r\nb", 0, id="yes with what is lost"),
        param("**Breaking:** no", 1, id="no"),
        param("<!--\n**Breaking:** yes\n-->", 1, id="only in a comment"),
        param("merged before the line existed", 1, id="no line"),
    ],
)
def test_breaking(body: str, code: int) -> None:
    assert run("breaking", body) == code
