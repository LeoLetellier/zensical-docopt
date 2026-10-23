import pytest

markdown = pytest.importorskip("markdown")

from zensical_docopt.markdown_ext import DocoptExtension  # noqa: E402

EXTS = ["tables", "fenced_code"]


def test_directive_expands(tmp_path, naval):
    (tmp_path / "naval_fate.py").write_text('"""' + naval + '"""\n', encoding="utf-8")
    src = "# CLI\n\n::: docopt naval_fate.py\n    heading_level: 3\n"
    html = markdown.markdown(src, extensions=[*EXTS, DocoptExtension(base_dir=str(tmp_path))])
    assert "<h3" in html and "<h4" in html
    assert 'id="opt-speed"' in html
    assert "naval_fate.py ship new" in html


def test_directive_inside_fence_is_untouched():
    src = "```\n::: docopt x.py\n```\n"
    html = markdown.markdown(src, extensions=[*EXTS, DocoptExtension()])
    assert "::: docopt x.py" in html


def test_missing_file_is_reported_not_raised(tmp_path):
    html = markdown.markdown(
        "::: docopt nope.py\n", extensions=[DocoptExtension(base_dir=str(tmp_path))]
    )
    assert "file not found" in html


def test_missing_file_raises_in_strict(tmp_path):
    from zensical_docopt.markdown_ext import DocoptDirectiveError

    with pytest.raises(DocoptDirectiveError):
        markdown.markdown(
            "::: docopt nope.py\n",
            extensions=[DocoptExtension(base_dir=str(tmp_path), strict=True)],
        )
