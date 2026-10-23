"""Front-end: command line (argparse; deliberately not docopt itself)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .acquire import AcquisitionError, load_source
from .build import DIALECTS, build_model
from .diagnostics import Severity
from .render import RenderOptions, render_markdown


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zensical-docopt", description="Parse and render docopt docstrings."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_ in (
        ("render", "print Markdown"),
        ("json", "print the semantic model as JSON"),
        ("check", "print diagnostics; non-zero exit on problems"),
    ):
        p = sub.add_parser(name, help=help_)
        _ = p.add_argument("source", help="script path or dotted module name")
        _ = p.add_argument("--symbol", help="module-level string constant (default: __doc__)")
        _ = p.add_argument("--mode", choices=("static", "import"), default="static")
        _ = p.add_argument("--dialect", choices=DIALECTS, default="auto")
        _ = p.add_argument("--base-dir", default=".")
        if name == "render":
            _ = p.add_argument("--heading-level", type=int, default=2)
            _ = p.add_argument("--options-style", choices=("table", "list", "none"), default="table")
            _ = p.add_argument("--no-anchors", action="store_true")
        if name == "check":
            _ = p.add_argument("--strict", action="store_true", help="warnings fail too")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        source = load_source(
            args.source, base_dir=args.base_dir, symbol=args.symbol, mode=args.mode
        )
        model = build_model(source.text, dialect=args.dialect)
    except (AcquisitionError, ValueError) as exc:
        print(f"zensical-docopt: {exc}", file=sys.stderr)
        return 2

    if args.command == "render":
        opts = RenderOptions(
            heading_level=args.heading_level,
            options_style=args.options_style,
            anchors=not args.no_anchors,
        )
        sys.stdout.write(render_markdown(model, opts))
        return 0
    if args.command == "json":
        print(json.dumps(model.to_dict(), indent=2))
        return 0

    failing = False
    for diag in model.diagnostics:
        print(diag.format(source.origin))
        if diag.severity is Severity.ERROR or (args.strict and diag.severity is Severity.WARNING):
            failing = True
    return 1 if failing else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
