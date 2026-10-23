"""Parse docopt docstrings and render them as documentation."""

from __future__ import annotations

from typing import Any

from .acquire import AcquisitionError, Source, load_source
from .build import DIALECTS, build_model, build_model_cached
from .diagnostics import Diagnostic, Severity
from .model import SCHEMA_VERSION, CliModel
from .render import RenderOptions, render_markdown

__version__ = "0.1.0"

parse = build_model

__all__ = [
    "DIALECTS",
    "SCHEMA_VERSION",
    "AcquisitionError",
    "CliModel",
    "Diagnostic",
    "RenderOptions",
    "Severity",
    "Source",
    "build_model",
    "build_model_cached",
    "load_source",
    "parse",
    "render_markdown",
]


def makeExtension(**kwargs: Any) -> Any:  # noqa: N802 - Python-Markdown contract
    """Lazy entry point so the core stays importable without `markdown`."""
    from .markdown_ext import DocoptExtension

    return DocoptExtension(**kwargs)
