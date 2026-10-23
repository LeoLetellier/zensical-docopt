"""Layer 3: the semantic model. `CliModel.to_dict()` is the stable JSON contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .diagnostics import Diagnostic
from .nodes import Node, node_to_dict

SCHEMA_VERSION = 1


@dataclass(slots=True)
class OptionDoc:
    short: str | None
    long: str | None
    argname: str | None
    default: str | None
    description: str
    in_usage: bool
    group: str = "Options"
    line: int | None = None


@dataclass(slots=True)
class UsageLine:
    raw: str
    line: int
    tree: Node | None
    command_path: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "line": self.line,
            "command_path": list(self.command_path),
            "tree": node_to_dict(self.tree) if self.tree is not None else None,
        }


@dataclass(slots=True)
class ExtraSection:
    title: str
    text: str
    line: int


@dataclass(slots=True)
class CliModel:
    prog: str = ""
    prologue: str = ""
    epilogue: str = ""
    usages: list[UsageLine] = field(default_factory=list)
    options: list[OptionDoc] = field(default_factory=list)
    arguments: list[str] = field(default_factory=list)
    commands: list[tuple[str, ...]] = field(default_factory=list)
    sections: list[ExtraSection] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "prog": self.prog,
            "prologue": self.prologue,
            "epilogue": self.epilogue,
            "usages": [u.to_dict() for u in self.usages],
            "options": [asdict(o) for o in self.options],
            "arguments": list(self.arguments),
            "commands": [list(c) for c in self.commands],
            "sections": [asdict(s) for s in self.sections],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }
