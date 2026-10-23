"""Layer 2b: recursive-descent parser for docopt usage patterns.

    expr  := seq ('|' seq)*
    seq   := (atom '...'?)*
    atom  := '(' expr ')' | '[' expr ']' | 'options' | '--' | '-'
           | --long[=ARG] | -s[ARG]... | <arg> | UPPER | command

Which options take an argument is decided by the `declared` mapping built
from the Options section (docopt's own rule); undeclared `--opt=ARG` still
takes an argument.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from .nodes import (
    Argument,
    Command,
    DoubleDash,
    Either,
    Group,
    Node,
    Option,
    OptionsShortcut,
    Repeat,
    Seq,
    Stdin,
)

STRUCTURAL = frozenset({"[", "]", "(", ")", "|", "..."})


class PatternSyntaxError(ValueError):
    """The usage pattern is malformed."""


def tokenize(source: str) -> list[str]:
    source = re.sub(r"([\[\]\(\)\|]|\.\.\.)", r" \1 ", source)
    # `<...>` may contain spaces, so it is matched as one token.
    return [t for t in re.split(r"\s+|(\S*<.*?>)", source) if t]


def parse_pattern(source: str, declared: Mapping[str, str | None] | None = None) -> Node:
    return _Parser(tokenize(source), declared or {}).parse()


class _Parser:
    def __init__(self, tokens: list[str], declared: Mapping[str, str | None]) -> None:
        self.tokens = tokens
        self.declared = declared
        self.pos = 0

    # -- token helpers ---------------------------------------------------
    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self) -> str | None:
        tok = self.peek()
        if tok is not None:
            self.pos += 1
        return tok

    def can_take_value(self) -> bool:
        tok = self.peek()
        return tok is not None and tok not in STRUCTURAL and tok != "--"

    def take_value(self) -> str:
        tok = self.advance()
        assert tok is not None
        return tok

    # -- grammar ---------------------------------------------------------
    def parse(self) -> Node:
        node = self.expr()
        if (tok := self.peek()) is not None:
            raise PatternSyntaxError(f"unexpected {tok!r}")
        return node

    def expr(self) -> Node:
        branches = [self.seq()]
        while self.peek() == "|":
            self.advance()
            branches.append(self.seq())
        return branches[0] if len(branches) == 1 else Either(tuple(branches))

    def seq(self) -> Seq:
        items: list[Node] = []
        while (tok := self.peek()) is not None and tok not in ("]", ")", "|"):
            atoms = self.atom()
            if self.peek() == "...":
                self.advance()
                child: Node = atoms[0] if len(atoms) == 1 else Seq(tuple(atoms))
                items.append(Repeat(child))
            else:
                items.extend(atoms)
        return Seq(tuple(items))

    def atom(self) -> list[Node]:
        tok = self.advance()
        assert tok is not None
        if tok in ("(", "["):
            body = self.expr()
            expected = ")" if tok == "(" else "]"
            closing = self.advance()
            if closing != expected:
                raise PatternSyntaxError(
                    f"missing {expected!r}" if closing is None else f"expected {expected!r}, got {closing!r}"
                )
            return [Group("required" if tok == "(" else "optional", body)]
        if tok == "...":
            raise PatternSyntaxError("'...' must follow an element")
        if tok == "options":
            return [OptionsShortcut()]
        if tok == "--":
            return [DoubleDash()]
        if tok == "-":
            return [Stdin()]
        if tok.startswith("--"):
            return [self.long_option(tok)]
        if tok.startswith("-"):
            return self.short_options(tok)
        if (tok.startswith("<") and tok.endswith(">")) or tok.isupper():
            return [Argument(tok)]
        return [Command(tok)]

    def long_option(self, tok: str) -> Option:
        name, eq, value = tok.partition("=")
        if name in self.declared:
            declared_arg = self.declared[name]
            if declared_arg is None:
                if eq:
                    raise PatternSyntaxError(f"{name} does not take an argument")
                return Option(name)
            if eq:
                return Option(name, value or declared_arg)
            if self.can_take_value():
                return Option(name, self.take_value())
            return Option(name, declared_arg)  # lenient: `[--opt]` for a valued option
        return Option(name, value or None) if eq else Option(name)

    def short_options(self, tok: str) -> list[Node]:
        chars = tok[1:]
        out: list[Node] = []
        while chars:
            name = f"-{chars[0]}"
            chars = chars[1:]
            argname = self.declared.get(name)
            if argname is None:
                out.append(Option(name))
            elif chars:  # -ofile
                out.append(Option(name, chars))
                chars = ""
            elif self.can_take_value():
                out.append(Option(name, self.take_value()))
            else:
                out.append(Option(name, argname))
        return out
