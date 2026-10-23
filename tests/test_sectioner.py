from zensical_docopt.sectioner import Prose, Section, split_blocks


def test_naval_fate_blocks(naval):
    blocks = split_blocks(naval)
    assert isinstance(blocks[0], Prose) and blocks[0].text == "Naval Fate."
    sections = [b for b in blocks if isinstance(b, Section)]
    assert [s.kind for s in sections] == ["usage", "options"]
    assert sections[0].number == 3


def test_generic_section_needs_indented_body():
    text = "Intro.\n\nExamples:\n  prog a\n\nNot a section:\nplain text\n"
    blocks = split_blocks(text)
    kinds = [b.kind if isinstance(b, Section) else "prose" for b in blocks]
    assert kinds == ["prose", "other", "prose"]


def test_section_ends_at_blank_line():
    blocks = split_blocks("Usage: prog a\n  prog b\n\n  prog c\n")
    usage = blocks[0]
    assert isinstance(usage, Section)
    assert [l.text.strip() for l in usage.lines] == ["prog a", "prog b"]
