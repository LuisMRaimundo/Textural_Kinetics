import pytest

from granular_v2.config import MustextuConfig
from granular_v2.granularity_mustextu import analyze_mustextu_from_score
from granular_v2.loader import load_score_and_note_matrix


def test_mustextu_wired(sample_musicxml):
    score, _, _ = load_score_and_note_matrix(sample_musicxml)
    out = analyze_mustextu_from_score(score, MustextuConfig())
    assert out["rate_events_per_second"] >= 0
    assert "mustextu" in out
    assert out["mustextu"]["composite"]["window_ms"] > 0
