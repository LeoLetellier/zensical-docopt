"""Layer 1: obtain the raw docstring text, preferably without executing code."""

from __future__ import annotations

import ast
import importlib.util
import inspect
from dataclasses import dataclass
from pathlib import Path


class AcquisitionError(Exception):
    """The docstring could not be located or read."""


@dataclass(frozen=True, slots=True)
class Source:
    text: str
    origin: str


def resolve(ref: str, base_dir: Path) -> Path:
    """Resolve a file path, or a dotted module name, to a source file.

    Dotted names use `importlib.util.find_spec`, which may import parent
    packages (never the target module itself).
    """
    if "/" in ref or "\\" in ref or ref.endswith(".py"):
        path = Path(ref)
        if not path.is_absolute():
            path = base_dir / path
        if not path.is_file():
            raise AcquisitionError(f"file not found: {path}")
        return path
    try:
        spec = importlib.util.find_spec(ref)
    except (ImportError, ValueError) as exc:
        raise AcquisitionError(f"cannot resolve module {ref!r}: {exc}") from exc
    if spec is None or not spec.origin or spec.origin in ("built-in", "frozen"):
        raise AcquisitionError(f"module {ref!r} has no source file")
    return Path(spec.origin)


def load_source(
    ref: str,
    *,
    base_dir: str | Path = ".",
    symbol: str | None = None,
    mode: str = "static",
) -> Source:
    """Load the docopt docstring.

    `symbol=None` means the module docstring; otherwise the name of a
    module-level string constant (e.g. ``DOC``).
    """
    path = resolve(ref, Path(base_dir))
    if mode == "static":
        text = _static_doc(path, symbol)
    elif mode == "import":
        text = _import_doc(path, symbol)
    else:
        raise AcquisitionError(f"unknown source mode {mode!r} (use 'static' or 'import')")
    return Source(inspect.cleandoc(text), str(path))


def _static_doc(path: Path, symbol: str | None) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise AcquisitionError(f"cannot parse {path}: {exc}") from exc

    if symbol is None or symbol == "__doc__":
        doc = ast.get_docstring(tree, clean=False)
        if doc is None:
            raise AcquisitionError(f"{path} has no module docstring")
        return doc

    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == symbol for t in node.targets
        ):
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == symbol
        ):
            value = node.value
        else:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
        raise AcquisitionError(
            f"{symbol!r} is not a plain string literal; use source_mode 'import'"
        )
    raise AcquisitionError(f"symbol {symbol!r} not found in {path}")


def _import_doc(path: Path, symbol: str | None) -> str:
    """Opt-in: executes the module (under a non-__main__ name)."""
    spec = importlib.util.spec_from_file_location("_zensical_docopt_target", path)
    if spec is None or spec.loader is None:
        raise AcquisitionError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # user code: anything can happen
        raise AcquisitionError(f"importing {path} failed: {exc!r}") from exc
    value = getattr(module, symbol or "__doc__", None)
    if not isinstance(value, str):
        raise AcquisitionError(f"{symbol or '__doc__'!r} is not a string in {path}")
    return value
