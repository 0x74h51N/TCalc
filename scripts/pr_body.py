#!/usr/bin/env python3
# What CI requires of a pull request description; the boxes come from the template itself.
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).parents[1] / ".github" / "pull_request_template.md"
COMMENT = re.compile(r"<!--.*?-->", re.S)
BOX = re.compile(r"^- \[( |x)\] (.*?)[ \t]*$", re.M | re.I)
BREAKING = re.compile(r"^\*\*Breaking:\*\*[ \t]*(yes|no)\b", re.M | re.I)
TRAP = re.compile(r'add the word "(\w+)" to the title')


def visible(body: str) -> str:
    # A comment is not an answer a reviewer can see
    return COMMENT.sub("", body.replace("\r\n", "\n"))


def is_breaking(body: str) -> bool:
    return [a.lower() for a in BREAKING.findall(visible(body))] == ["yes"]


def problems(body: str, title: str, template: str) -> list[str]:
    text = visible(body)
    found = []
    [trap_word] = TRAP.findall(template)
    if trap_word.lower() in title.lower():
        found.append("Unsupervised AI agents are prohibited: see docs/CONTRIBUTING.md")
    if len(BREAKING.findall(text)) != 1:
        found.append(
            "The description needs one line that says **Breaking:** yes or **Breaking:** no"
        )

    # The template's first three boxes answer who is submitting, the rest are the checklist
    wanted = [label for _, label in BOX.findall(visible(template))]
    who, free_agent, checklist = wanted[:2], wanted[2], wanted[3:]
    ticked = [label for mark, label in BOX.findall(text) if mark != " "]
    if free_agent in ticked:
        found.append("Unsupervised AI agents are prohibited: see docs/CONTRIBUTING.md")
    elif len([label for label in ticked if label in who]) != 1:
        found.append("Tick one box: human agent, or humble AI servant agent")
    found.extend(f"Tick the box: {label}" for label in checklist if label not in ticked)
    return found


def main() -> int:
    body = sys.stdin.read()
    if sys.argv[1] == "breaking":
        return 0 if is_breaking(body) else 1
    found = problems(body, sys.argv[2], TEMPLATE.read_text(encoding="utf-8"))
    for problem in found:
        print(problem)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
