"""Layer 4: Markdown renderer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .model import CliModel, OptionDoc

FENCE = "`" * 3


@dataclass(frozen=True, slots=True)
class RenderOptions:
    heading_level: int = 2
    title: str | None = None
    show_heading: bool = True
    show_prologue: bool = True
    show_commands: bool = True
    show_sections: bool = True
    options_style: Literal["table", "list", "none"] = "table"
    anchors: bool = True
    anchor_prefix: str = ""


def render_markdown(model: CliModel, opts: RenderOptions | None = None) -> str:
    opts = opts or RenderOptions()
    top = max(1, min(opts.heading_level, 6))
    sub = min(top + 1, 6) if opts.show_heading else top
    chunks: list[str] = []

    if opts.show_heading:
        chunks.append(_heading(top, opts.title or model.prog or "Command line"))
    if opts.show_prologue and model.prologue:
        chunks.append(model.prologue)

    if model.usages:
        chunks.append(_heading(sub, "Usage"))
        chunks.append(_fenced([f"{model.prog} {u.raw}".strip() for u in model.usages]))

    if opts.show_commands and model.commands:
        chunks.append(_heading(sub, "Commands"))
        chunks.append("\n".join(f"- `{model.prog} {' '.join(p)}`" for p in model.commands))

    if opts.options_style != "none" and model.options:
        groups: dict[str, list[OptionDoc]] = {}
        for option in model.options:
            groups.setdefault(option.group, []).append(option)
        for title, items in groups.items():
            chunks.append(_heading(sub, "Options" if len(groups) == 1 else title))
            chunks.append(
                _table(items, opts) if opts.options_style == "table" else _list(items, opts)
            )

    if opts.show_sections:
        for section in model.sections:
            chunks.append(_heading(sub, section.title))
            chunks.append(_fenced(section.text.splitlines()))

    if model.epilogue:
        chunks.append(model.epilogue)
    return "\n\n".join(chunks) + "\n"


def anchor_id(prefix: str, name: str) -> str:
    kind = "opt" if name.startswith("--") else "opt-s"
    return re.sub(r"[^A-Za-z0-9_-]", "-", f"{prefix}{kind}-{name.lstrip('-')}")


def _heading(level: int, text: str) -> str:
    return f"{'#' * min(level, 6)} {text}"


def _fenced(lines: list[str]) -> str:
    return "\n".join([f"{FENCE}text", *lines, FENCE])


def _escape(text: str) -> str:
    return text.replace("|", "\\|").replace("<", "&lt;").replace("\n", " ")


def _names_cell(option: OptionDoc, opts: RenderOptions) -> str:
    names = [n for n in (option.short, option.long) if n]
    anchors = ""
    if opts.anchors:
        anchors = "".join(f'<span id="{anchor_id(opts.anchor_prefix, n)}"></span>' for n in names)
    return anchors + ", ".join(f"`{n}`" for n in names)


def _table(items: list[OptionDoc], opts: RenderOptions) -> str:
    has_arg = any(o.argname for o in items)
    has_default = any(o.default is not None for o in items)
    header = ["Option"]
    if has_arg:
        header.append("Argument")
    if has_default:
        header.append("Default")
    header.append("Description")

    rows = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    for o in items:
        cells = [_names_cell(o, opts)]
        if has_arg:
            cells.append(f"`{o.argname}`" if o.argname else "")
        if has_default:
            cells.append(f"`{o.default}`" if o.default is not None else "")
        cells.append(_escape(o.description))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def _list(items: list[OptionDoc], opts: RenderOptions) -> str:
    lines = []
    for o in items:
        head = _names_cell(o, opts)
        if o.argname:
            head += f" `{o.argname}`"
        lines.append(f"- {head} — {_escape(o.description)}" if o.description else f"- {head}")
    return "\n".join(lines)
