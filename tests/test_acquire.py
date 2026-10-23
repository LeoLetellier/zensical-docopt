import pytest

from zensical_docopt import AcquisitionError, load_source


def test_module_docstring(tmp_path):
    p = tmp_path / "s.py"
    p.write_text('"""Usage: prog [options]"""\nraise SystemExit("must not run")\n')
    assert load_source(str(p)).text == "Usage: prog [options]"  # static: never executed


def test_symbol(tmp_path):
    p = tmp_path / "s.py"
    p.write_text('DOC = """Usage: prog"""\n')
    assert load_source(str(p), symbol="DOC").text == "Usage: prog"


def test_fstring_symbol_rejected(tmp_path):
    p = tmp_path / "s.py"
    p.write_text('X = 1\nDOC = f"Usage: prog {X}"\n')
    with pytest.raises(AcquisitionError):
        load_source(str(p), symbol="DOC")


def test_missing_file(tmp_path):
    with pytest.raises(AcquisitionError):
        load_source("nope.py", base_dir=tmp_path)
