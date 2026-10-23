from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def naval() -> str:
    return (Path(__file__).parent / "corpus" / "naval_fate.txt").read_text(encoding="utf-8")
