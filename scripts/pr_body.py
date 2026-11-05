#!/usr/bin/env python3
# Prints the Breaking answer of a pull request description for the release workflow.
import re
import sys

# GitHub hides everything after a comment that never closes
COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.S)
FENCE = re.compile(r"^```.*?^```[ \t]*$", re.M | re.S)
BREAKING = re.compile(r"^\*\*Breaking:\*\*[ \t]*(yes|no)(?:[,:][^\n]*)?[ \t]*$", re.M | re.I)


def visible(body: str) -> str:
    # A comment is not an answer a reviewer can see, and a quoted answer is not an answer
    return FENCE.sub("", COMMENT.sub("", body.replace("\r\n", "\n")))


def is_breaking(body: str) -> bool:
    return [a.lower() for a in BREAKING.findall(visible(body))] == ["yes"]


if __name__ == "__main__":
    print("yes" if is_breaking(sys.stdin.read()) else "no")
