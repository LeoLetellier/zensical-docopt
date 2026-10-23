import json

from zensical_docopt import Severity, parse


def test_naval_fate(naval):
    m = parse(naval)
    assert m.prog == "naval_fate.py"
    assert len(m.usages) == 6
    assert not [d for d in m.diagnostics if d.severity is Severity.ERROR]
    speed = next(o for o in m.options if o.long == "--speed")
    assert speed.argname == "<kn>" and speed.default == "10" and speed.in_usage
    assert ("ship", "new") in m.commands and ("mine",) in m.commands
    assert m.arguments[0] == "<name>"
    assert m.prologue == "Naval Fate."


def test_missing_usage():
    assert [d.code for d in parse("Just prose.").diagnostics] == ["E001"]


def test_unused_option_warns_without_shortcut():
    m = parse("Usage: prog\n\nOptions:\n  --foo  bar\n")
    assert "W101" in [d.code for d in m.diagnostics]


def test_shortcut_silences_unused_option_warning():
    m = parse("Usage: prog [options]\n\nOptions:\n  --foo  bar\n")
    assert "W101" not in [d.code for d in m.diagnostics]


def test_bad_pattern_is_diagnostic_not_exception():
    m = parse("Usage: prog [a\n")
    assert m.usages[0].tree is None
    assert "E003" in [d.code for d in m.diagnostics]


def test_json_is_serialisable_and_versioned(naval):
    data = json.loads(json.dumps(parse(naval).to_dict()))
    assert data["schema_version"] == 1
    assert data["usages"][0]["tree"]["type"] == "Seq"
