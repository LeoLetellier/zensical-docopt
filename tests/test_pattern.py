import pytest

from zensical_docopt.nodes import Option, OptionsShortcut, format_node, iter_leaves
from zensical_docopt.pattern import PatternSyntaxError, parse_pattern


def fmt(src, declared=None):
    return format_node(parse_pattern(src, declared))


def test_roundtrip_simple():
    assert fmt("ship new <name>...") == "ship new <name>..."
    assert fmt("(-h | --help)") == "(-h | --help)"
    assert fmt("mine (set|remove) <x> <y>") == "mine (set | remove) <x> <y>"


def test_declared_valued_long_option_consumes_next_token():
    assert fmt("[--speed <kn>]", {"--speed": "<kn>"}) == "[--speed=<kn>]"


def test_undeclared_long_option_does_not_consume():
    leaves = list(iter_leaves(parse_pattern("--speed <kn>")))
    assert leaves[0] == Option("--speed") and len(leaves) == 2


def test_stacked_short_options():
    leaves = list(iter_leaves(parse_pattern("-vv")))
    assert leaves == [Option("-v"), Option("-v")]


def test_options_shortcut():
    leaves = list(iter_leaves(parse_pattern("[options] FILE")))
    assert isinstance(leaves[0], OptionsShortcut)


def test_angle_argument_with_space():
    assert fmt("<input file>") == "<input file>"


@pytest.mark.parametrize("bad", ["[a", "a)", "(a | ", "...", "a ] b"])
def test_syntax_errors(bad):
    with pytest.raises(PatternSyntaxError):
        parse_pattern(bad)
