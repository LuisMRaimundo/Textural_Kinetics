import pytest
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def sample_musicxml():
    p = FIXTURES / "sample.musicxml"
    if not p.exists():
        pytest.skip("sample.musicxml missing")
    return p
