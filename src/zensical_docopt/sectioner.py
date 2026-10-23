"""Layer 2a: split a docstring into prose and sections (docopt heuristics).

A section starts at an unindented header line (``Usage:``, ``... options:``,
or any ``Title:`` followed by an indented line) and continues over the
following indented, non-blank lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Union

SectionKind = Literal["usage", "options", "other"]

_USAGE_RE = re.compile(r"^(?P<title>[^\n:]*usage)[ \t]*:(?P<rest>.*)$", re.IGNORECASE)
_OPTIONS_RE = re.compile(r"^(?P<title>[^\n:]*options)[ \t]*:(?P<rest>.*)$", re.IGNORECASE)
_GENERIC_RE = re.compile(r"^(?P<title>\S[^:]*?)[ \t]*:[ \t]*$")


@dataclass(frozen=True, slots=True)
class Line:
    number: int  # 1-based
    text: str


@dataclass(frozen=True, slots=True)
class Prose:
    lines: tuple[Line, ...]

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


@dataclass(frozen=True, slots=True)
class Section:
    kind: SectionKind
    title: str
    lines: tuple[Line, ...]
    number: int  # header line


Block = Union[Prose, Section]


def split_blocks(text: str) -> list[Block]:
    lines = text.splitlines()
    blocks: list[Block] = []
    prose: list[Line] = []

    def flush() -> None:
        trimmed = _trim(prose)
        if trimmed:
            blocks.append(Prose(tuple(trimmed)))
        prose.clear()

    i = 0
    while i < len(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        header = _classify(lines[i], nxt)
        if header is None:
            prose.append(Line(i + 1, lines[i]))
            i += 1
            continue
        flush()
        kind, title, rest = header
        body: list[Line] = []
        if rest.strip():
            body.append(Line(i + 1, rest.strip()))
        j = i + 1
        while j < len(lines) and _is_indented(lines[j]):
            body.append(Line(j + 1, lines[j]))
            j += 1
        blocks.append(Section(kind, title, tuple(body), i + 1))
        i = j
    flush()
    return blocks


def _classify(line: str, next_line: str | None) -> tuple[SectionKind, str, str] | None:
    if not line or line[0] in " \t":
        return None
    if m := _USAGE_RE.match(line):
        return "usage", m["title"].strip(), m["rest"]
    if m := _OPTIONS_RE.match(line):
        return "options", m["title"].strip(), m["rest"]
    if (m := _GENERIC_RE.match(line)) and next_line is not None and _is_indented(next_line):
        return "other", m["title"].strip(), ""
    return None


def _is_indented(line: str) -> bool:
    return bool(line.strip()) and line[0] in " \t"


def _trim(lines: list[Line]) -> list[Line]:
    start, end = 0, len(lines)
    while start < end and not lines[start].text.strip():
        start += 1
    while end > start and not lines[end - 1].text.strip():
        end -= 1
    return lines[start:end]
