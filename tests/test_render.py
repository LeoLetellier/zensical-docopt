from zensical_docopt import RenderOptions, parse, render_markdown


def test_default_render(naval):
    out = render_markdown(parse(naval))
    assert out.startswith("## naval_fate.py")
    assert "### Usage" in out
    assert "naval_fate.py ship new <name>..." in out
    assert 'id="opt-speed"' in out and "`--speed`" in out
    assert "| Option | Argument | Default | Description |" in out


def test_flag_only_table_drops_columns():
    out = render_markdown(parse("Usage: prog [options]\n\nOptions:\n  -v  Verbose.\n"))
    assert "| Option | Description |" in out


def test_list_style_and_no_heading(naval):
    out = render_markdown(
        parse(naval), RenderOptions(options_style="list", show_heading=False, heading_level=3)
    )
    assert out.startswith("Naval Fate.") or "### Usage" in out
    assert "- <span" in out


def test_pipes_and_angle_brackets_are_escaped():
    out = render_markdown(parse("Usage: prog [options]\n\nOptions:\n  -x  a|b <tag>\n"))
    assert "a\\|b &lt;tag>" in out
