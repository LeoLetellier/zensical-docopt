# zensical-docopt

Parse [docopt](http://docopt.org) docstrings of Python CLI scripts and render
them as documentation. Works with Zensical and MkDocs through a
Python-Markdown extension; also usable as a library and a CLI.

> [!WARNING]
> Claude Sonnet 5.5 oneshot generated

## Install

    pip install "zensical-docopt[markdown]"

## Use in Zensical

```toml
[project.markdown_extensions.zensical_docopt]
base_dir = "."
```

(MkDocs: `markdown_extensions: [zensical_docopt: {base_dir: .}]`.)

In a page:

    ::: docopt path/to/script.py
        heading_level: 3
        options_style: table

Per-directive keys: `symbol`, `source_mode`, `dialect`, `heading_level`, `title`,
`show_heading`, `show_prologue`, `show_commands`, `show_sections`,
`options_style` (`table|list|none`), `anchors`, `anchor_prefix`.

## CLI

    zensical-docopt render script.py
    zensical-docopt json   script.py
    zensical-docopt check  script.py --strict

## Design notes

- The docstring is read **statically** (AST) by default, so scripts are never
  imported or executed. `source_mode: import` is an explicit opt-in.
- Parsing is a dedicated lossless parser, not docopt's runtime. Errors become
  diagnostics; a broken pattern never fails the whole page unless `strict`.
- The JSON model (`CliModel.to_dict()`, `schema_version`) is the stable contract.

## Status / limitations

- Implements the legacy docopt rules. `dialect = "docopt2"` currently falls back
  to them (reported as diagnostic I001).
- Option abbreviation (`--ver` for `--version`) is not resolved.
- No persistent cache yet (in-process memo only).
- A native Zensical module adapter is planned for when its module API is public.
