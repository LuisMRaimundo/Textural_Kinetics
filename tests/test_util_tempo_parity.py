"""util_tempo.build_seconds_map vs timebase segments."""

import pytest
from music21 import note, stream, tempo

from granular_v2.timebase_parity import compare_ql_maps
from granular_v2.timebase import TempoSeg, ql_to_seconds_fn
from granular_v2.util_tempo import build_seconds_map


def _two_tempo_score():
    p = stream.Part()
    p.insert(0, tempo.MetronomeMark(number=120))
    p.insert(0, note.Note("C4", quarterLength=2))
    p.insert(2, tempo.MetronomeMark(number=60))
    p.insert(2, note.Note("D4", quarterLength=2))
    sc = stream.Score()
    sc.insert(0, p)
    return sc


def test_manual_segments_match_formula():
    segs = [
        TempoSeg(0.0, 2.0, 0.0, 120.0),
        TempoSeg(2.0, 4.0, 1.0, 60.0),
    ]
    fn = ql_to_seconds_fn(segs)
    assert fn(0.0) == pytest.approx(0.0)
    assert fn(2.0) == pytest.approx(1.0)
    assert fn(4.0) == pytest.approx(3.0)


def test_util_vs_timebase_on_synthetic_score():
    """After _boundary_offset fix, util_tempo should match timebase closely."""
    sc = _two_tempo_score()
    ok, rows = compare_ql_maps(sc, atol=0.06)
    assert ok, rows
    fn = build_seconds_map(sc)
    assert fn(4.0) == pytest.approx(3.0)


def test_build_seconds_map_monotonic():
    sc = _two_tempo_score()
    fn = build_seconds_map(sc)
    qs = [0.0, 1.0, 2.0, 3.0, 4.0]
    ts = [fn(q) for q in qs]
    assert ts == sorted(ts)


def test_parity_on_corpus_fixtures():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "corpus" / "fixtures"
    from music21 import converter

    for path in sorted(root.glob("*.musicxml")):
        sc = converter.parse(str(path))
        ok, rows = compare_ql_maps(sc, atol=0.1)
        assert ok, (path.name, rows)
