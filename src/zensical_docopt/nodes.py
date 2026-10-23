"""Layer 2b: AST of a docopt usage pattern."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Literal, Union


@dataclass(frozen=True, slots=True)
class Command:
    name: str


@dataclass(frozen=True, slots=True)
class Argument:
    name: str


@dataclass(frozen=True, slots=True)
class Option:
    name: str  # "--long" or "-s"
    argname: str | None = None


@dataclass(frozen=True, slots=True)
class OptionsShortcut:  # the literal `options` token, usually `[options]`
    pass


@dataclass(frozen=True, slots=True)
class DoubleDash:  # `--`
    pass


@dataclass(frozen=True, slots=True)
class Stdin:  # `-`
    pass


@dataclass(frozen=True, slots=True)
class Seq:
    items: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class Either:
    branches: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class Group:
    kind: Literal["optional", "required"]
    body: Node


@dataclass(frozen=True, slots=True)
class Repeat:
    child: Node


Node = Union[
    Command, Argument, Option, OptionsShortcut, DoubleDash, Stdin, Seq, Either, Group, Repeat
]


def iter_leaves(node: Node) -> Iterator[Node]:
    match node:
        case Seq(items):
            for item in items:
                yield from iter_leaves(item)
        case Either(branches):
            for branch in branches:
                yield from iter_leaves(branch)
        case Group(_, body):
            yield from iter_leaves(body)
        case Repeat(child):
            yield from iter_leaves(child)
        case _:
            yield node


def format_node(node: Node) -> str:
    """Canonical text form of a pattern (normalises `--opt ARG` to `--opt=ARG`)."""
    match node:
        case Seq(items):
            return " ".join(format_node(i) for i in items)
        case Either(branches):
            return " | ".join(format_node(b) for b in branches)
        case Group(kind, body):
            opening, closing = ("[", "]") if kind == "optional" else ("(", ")")
            return f"{opening}{format_node(body)}{closing}"
        case Repeat(child):
            text = format_node(child)
            if isinstance(child, Seq) and len(child.items) > 1:
                text = f"({text})"
            return f"{text}..."
        case Command(n) | Argument(n):
            return n
        case Option(name, arg):
            if arg is None:
                return name
            return f"{name}={arg}" if name.startswith("--") else f"{name} {arg}"
        case OptionsShortcut():
            return "options"
        case DoubleDash():
            return "--"
        case Stdin():
            return "-"
    raise TypeError(f"unknown node {node!r}")  # pragma: no cover


def node_to_dict(node: Node) -> dict[str, Any]:
    out: dict[str, Any] = {"type": type(node).__name__}
    for f in fields(node):
        out[f.name] = _plain(getattr(node, f.name))
    return out


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, Node):
        return node_to_dict(value)
    return value
