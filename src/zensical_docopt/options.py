"""Layer 2c: parse `Options:` entries (docopt rules).

An entry starts at a line whose first non-blank character is `-`; following
lines that do not start with `-` continue its description. Names and
description are separated by two or more spaces.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from .diagnostics import Diagnostic, Severity
from .sectioner import Line

_DEFAULT_RE = re.compile(r"\[default:\s*(.*?)\]", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class OptionSpec:
    short: str | None
    long: str | None
    argname: str | None
    default: str | None
    description: str
    line: int

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(n for n in (self.short, self.long) if n)


def parse_options_section(lines: Sequence[Line]) -> tuple[list[OptionSpec], list[Diagnostic]]:
    entries: list[list[Line]] = []
    for line in lines:
        stripped = line.text.strip()
        if stripped.startswith("-"):
            entries.append([line])
        elif stripped and entries:
            entries[-1].append(line)

    specs: list[OptionSpec] = []
    diags: list[Diagnostic] = []
    for entry in entries:
        spec = _parse_entry(entry, diags)
        if spec is not None:
            specs.append(spec)
    return specs, diags


def _parse_entry(entry: list[Line], diags: list[Diagnostic]) -> OptionSpec | None:
    first = entry[0].text.strip()
    head, _, tail = first.partition("  ")
    short = long = argname = None
    extra: set[str] = set()
    for tok in head.replace(",", " ").replace("=", " ").split():
        if tok in ("-", "--"):
            continue
        if tok.startswith("--"):
            long = tok
        elif tok.startswith("-"):
            short = tok
        else:
            extra.add(tok)
            argname = argname or tok
    if short is None and long is None:
        return None
    if len(extra) > 1:
        diags.append(
            Diagnostic(
                "W103",
                f"entry {head!r} has several words after the option names; "
                "separate the description with two spaces",
                Severity.WARNING,
                entry[0].number,
            )
        )
    desc_lines = [tail.strip(), *(ln.text.strip() for ln in entry[1:])]
    desc_lines = [d for d in desc_lines if d]
    default = None
    if argname:
        for d in desc_lines:
            if m := _DEFAULT_RE.search(d):
                default = m.group(1)
                break
    return OptionSpec(short, long, argname, default, " ".join(desc_lines), entry[0].number)
