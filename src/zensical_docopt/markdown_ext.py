"""Front-end: Python-Markdown extension (works in Zensical and MkDocs).

Implemented as a *preprocessor* (priority 27, before fenced_code/superfences at
25) so the Markdown it emits, including fences, is processed normally.

Directive:

    ::: docopt path/to/script.py
        heading_level: 3
        options_style: list
"""

from __future__ import annotations

import logging
import re
from typing import Any

from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

from .acquire import AcquisitionError, load_source
from .build import build_model_cached
from .diagnostics import Severity
from .render import RenderOptions, render_markdown

logger = logging.getLogger("zensical_docopt")

_DIRECTIVE = re.compile(r"^(?P<indent>[ \t]*)::: docopt[ \t]+(?P<ref>\S+)[ \t]*$")
_FENCE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})")
_KEY_VALUE = re.compile(r"^(?P<key>[A-Za-z_][\w-]*)[ \t]*:[ \t]*(?P<value>.*?)[ \t]*$")
_DIRECTIVE_KEYS = {
    "symbol", "source_mode", "dialect", "heading_level", "title", "show_heading",
    "show_prologue", "show_commands", "show_sections", "options_style", "anchors",
    "anchor_prefix", "base_dir",
}  # fmt: skip


class DocoptDirectiveError(Exception):
    """Raised in strict mode when a directive cannot be rendered cleanly."""


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _coerce(value: str) -> object:
    v = value.strip().strip("'\"")
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def _indent_len(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


class DocoptPreprocessor(Preprocessor):
    def __init__(self, md: Markdown, config: dict[str, Any]) -> None:
        super().__init__(md)
        self.config = config

    def run(self, lines: list[str]) -> list[str]:
        out: list[str] = []
        fence: str | None = None
        i = 0
        while i < len(lines):
            line = lines[i]
            if fence is not None:  # never touch fenced code
                out.append(line)
                stripped = line.strip()
                if stripped.startswith(fence) and not stripped.strip(fence[0]):
                    fence = None
                i += 1
                continue
            if m := _FENCE.match(line):
                fence = m["fence"]
                out.append(line)
                i += 1
                continue
            directive = _DIRECTIVE.match(line)
            if directive is None:
                out.append(line)
                i += 1
                continue
            overrides, i = self._read_options(lines, i + 1, len(directive["indent"]))
            out.extend(self._expand(directive["ref"], overrides, directive["indent"]))
        return out

    def _read_options(
        self, lines: list[str], start: int, base_indent: int
    ) -> tuple[dict[str, object], int]:
        overrides: dict[str, object] = {}
        j = start
        while j < len(lines) and lines[j].strip() and _indent_len(lines[j]) > base_indent:
            m = _KEY_VALUE.match(lines[j].strip())
            if m is None:
                logger.warning("zensical-docopt: ignoring malformed option line %r", lines[j])
            else:
                key = m["key"].replace("-", "_")
                if key in _DIRECTIVE_KEYS:
                    overrides[key] = _coerce(m["value"])
                else:
                    logger.warning("zensical-docopt: unknown option %r", m["key"])
            j += 1
        return overrides, j

    def _expand(self, ref: str, overrides: dict[str, object], indent: str) -> list[str]:
        cfg: dict[str, Any] = {**self.config, **overrides}
        strict = _as_bool(cfg.get("strict"))
        try:
            source = load_source(
                ref,
                base_dir=str(cfg["base_dir"]),
                symbol=(cfg.get("symbol") or None),
                mode=str(cfg["source_mode"]),
            )
            model = build_model_cached(source.text, str(cfg["dialect"]))
        except (AcquisitionError, ValueError) as exc:
            message = f"zensical-docopt: {ref}: {exc}"
            if strict:
                raise DocoptDirectiveError(message) from exc
            logger.error(message)
            return ["", f"{indent}> **{message}**", ""]

        problems = False
        for diag in model.diagnostics:
            text = diag.format(source.origin)
            if diag.severity is Severity.ERROR:
                logger.error(text)
                problems = True
            elif diag.severity is Severity.WARNING:
                logger.warning(text)
                problems = True
            else:
                logger.info(text)
        if strict and problems:
            raise DocoptDirectiveError(f"zensical-docopt: {ref}: diagnostics reported (strict)")

        style = str(cfg["options_style"])
        if style not in ("table", "list", "none"):
            style = "table"
        opts = RenderOptions(
            heading_level=int(cfg["heading_level"]),
            title=(cfg.get("title") or None),
            show_heading=_as_bool(cfg["show_heading"]),
            show_prologue=_as_bool(cfg.get("show_prologue", True)),
            show_commands=_as_bool(cfg["show_commands"]),
            show_sections=_as_bool(cfg.get("show_sections", True)),
            options_style=style,  # type: ignore[arg-type]
            anchors=_as_bool(cfg["anchors"]),
            anchor_prefix=str(cfg["anchor_prefix"]),
        )
        rendered = render_markdown(model, opts).splitlines()
        return ["", *(indent + ln if ln else "" for ln in rendered), ""]


class DocoptExtension(Extension):
    def __init__(self, **kwargs: Any) -> None:
        self.config = {
            "base_dir": [".", "Directory used to resolve relative script paths."],
            "dialect": ["auto", "auto | docopt | docopt2 (docopt2 falls back for now)."],
            "source_mode": ["static", "static (AST, no execution) | import."],
            "heading_level": [2, "Level of the top heading."],
            "options_style": ["table", "table | list | none."],
            "anchors": [True, "Emit per-option anchors."],
            "anchor_prefix": ["", "Prefix for anchor ids (several CLIs per page)."],
            "show_heading": [True, "Emit the top heading."],
            "show_commands": [True, "Emit the commands list."],
            "strict": [False, "Raise on diagnostics instead of logging."],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802
        md.preprocessors.register(
            DocoptPreprocessor(md, self.getConfigs()), "zensical_docopt", 27
        )
