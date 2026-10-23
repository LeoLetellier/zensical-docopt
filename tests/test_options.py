from zensical_docopt.options import parse_options_section
from zensical_docopt.sectioner import Line


def L(*texts):
    return [Line(i + 1, t) for i, t in enumerate(texts)]


def test_flag_and_valued_entries():
    specs, diags = parse_options_section(
        L(
            "-h --help     Show this screen.",
            "--speed=<kn>  Speed in knots [default: 10].",
            "-o FILE, --output=FILE  Write here.",
        )
    )
    assert not diags
    help_, speed, out = specs
    assert (help_.short, help_.long, help_.argname) == ("-h", "--help", None)
    assert (speed.long, speed.argname, speed.default) == ("--speed", "<kn>", "10")
    assert (out.short, out.long, out.argname) == ("-o", "--output", "FILE")


def test_continuation_lines_join_description():
    specs, _ = parse_options_section(L("--rate=N  Rate limit.", "    More text [default: 3]"))
    assert specs[0].default == "3" and "More text" in specs[0].description


def test_single_space_description_warns():
    _, diags = parse_options_section(L("-v Verbose output"))
    assert [d.code for d in diags] == ["W103"]
