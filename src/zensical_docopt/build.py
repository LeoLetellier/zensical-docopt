"""Layer 3: merge sections, options and patterns into a CliModel + diagnostics."""

from __future__ import annotations

import textwrap
from functools import lru_cache

from .diagnostics import Diagnostic, Severity
from .model import CliModel, ExtraSection, OptionDoc, UsageLine
from .nodes import Argument, DoubleDash, Node, Option, OptionsShortcut, Seq, iter_leaves
from .options import OptionSpec, parse_options_section
from .pattern import PatternSyntaxError, parse_pattern
from .sectioner import Prose, Section, split_blocks

DIALECTS = ("auto", "docopt", "docopt2")


def build_model(text: str, *, dialect: str = "auto") -> CliModel:
    if dialect not in DIALECTS:
        raise ValueError(f"unknown dialect {dialect!r}; expected one of {DIALECTS}")
    diags: list[Diagnostic] = []
    if dialect == "docopt2":
        diags.append(
            Diagnostic(
                "I001",
                "dialect 'docopt2' is not implemented yet; using the legacy docopt rules",
                Severity.INFO,
            )
        )

    prologue: list[str] = []
    epilogue: list[str] = []
    usage_sections: list[Section] = []
    options_sections: list[Section] = []
    extras: list[ExtraSection] = []
    seen_section = False
    for block in split_blocks(text):
        if isinstance(block, Prose):
            (epilogue if seen_section else prologue).append(block.text)
            continue
        seen_section = True
        if block.kind == "usage":
            usage_sections.append(block)
        elif block.kind == "options":
            options_sections.append(block)
        else:
            body = textwrap.dedent("\n".join(ln.text for ln in block.lines))
            extras.append(ExtraSection(block.title, body, block.number))

    # Options first: they decide which options take arguments in patterns.
    specs: list[tuple[str, OptionSpec]] = []
    for section in options_sections:
        parsed, option_diags = parse_options_section(section.lines)
        diags.extend(option_diags)
        specs.extend((section.title, s) for s in parsed)
    declared: dict[str, str | None] = {}
    for _, spec in specs:
        for name in spec.names:
            declared[name] = spec.argname

    prog = ""
    usages: list[UsageLine] = []
    if not usage_sections:
        diags.append(Diagnostic("E001", "no 'Usage:' section found", Severity.ERROR))
    else:
        if len(usage_sections) > 1:
            diags.append(
                Diagnostic(
                    "W001",
                    "more than one usage section; using the first",
                    Severity.WARNING,
                    usage_sections[1].number,
                )
            )
        prog, segments = _split_usage(usage_sections[0])
        if not segments:
            diags.append(
                Diagnostic("E002", "empty usage section", Severity.ERROR, usage_sections[0].number)
            )
        for number, raw in segments:
            try:
                tree: Node | None = parse_pattern(raw, declared)
            except PatternSyntaxError as exc:
                diags.append(
                    Diagnostic("E003", f"invalid usage pattern {raw!r}: {exc}", Severity.ERROR, number)
                )
                tree = None
            usages.append(UsageLine(raw, number, tree, _command_path(tree) if tree else ()))

    used: set[str] = set()
    has_shortcut = False
    arguments: list[str] = []
    for usage in usages:
        if usage.tree is None:
            continue
        for leaf in iter_leaves(usage.tree):
            if isinstance(leaf, Option):
                used.add(leaf.name)
            elif isinstance(leaf, OptionsShortcut):
                has_shortcut = True
            elif isinstance(leaf, Argument) and leaf.name not in arguments:
                arguments.append(leaf.name)

    options: list[OptionDoc] = []
    for group, spec in specs:
        in_usage = any(n in used for n in spec.names)
        options.append(
            OptionDoc(
                short=spec.short,
                long=spec.long,
                argname=spec.argname,
                default=spec.default,
                description=spec.description,
                in_usage=in_usage,
                group=group,
                line=spec.line,
            )
        )
        if usages and not in_usage and not has_shortcut:
            diags.append(
                Diagnostic(
                    "W101",
                    f"option {'/'.join(spec.names)} is documented but never used in "
                    + "Usage and there is no [options] shortcut",
                    Severity.WARNING,
                    spec.line,
                )
            )
    for name in sorted(used - set(declared)):
        diags.append(
            Diagnostic("I102", f"option {name} is used in Usage but not documented", Severity.INFO)
        )

    commands: list[tuple[str, ...]] = []
    for usage in usages:
        if usage.command_path and usage.command_path not in commands:
            commands.append(usage.command_path)

    return CliModel(
        prog=prog,
        prologue="\n\n".join(prologue),
        epilogue="\n\n".join(epilogue),
        usages=usages,
        options=options,
        arguments=arguments,
        commands=commands,
        sections=extras,
        diagnostics=diags,
    )


@lru_cache(maxsize=256)
def build_model_cached(text: str, dialect: str = "auto") -> CliModel:
    """Memoised variant. The returned model is shared: treat it as read-only."""
    return build_model(text, dialect=dialect)


def _split_usage(section: Section) -> tuple[str, list[tuple[int, str]]]:
    """docopt rule: the first word is the program name; each later occurrence
    of that word starts a new pattern."""
    tokens = [(tok, ln.number) for ln in section.lines for tok in ln.text.split()]
    if not tokens:
        return "", []
    prog = tokens[0][0]
    segments: list[tuple[int, list[str]]] = [(tokens[0][1], [])]
    for tok, number in tokens[1:]:
        if tok == prog:
            segments.append((number, []))
        else:
            segments[-1][1].append(tok)
    return prog, [(number, " ".join(toks)) for number, toks in segments]


def _command_path(tree: Node) -> tuple[str, ...]:
    """Leading commands of a pattern, skipping option-only items."""
    from .nodes import Command

    if not isinstance(tree, Seq):
        return ()
    path: list[str] = []
    for item in tree.items:
        if isinstance(item, Command):
            path.append(item.name)
        elif all(isinstance(x, (Option, OptionsShortcut, DoubleDash)) for x in iter_leaves(item)):
            continue
        else:
            break
    return tuple(path)
