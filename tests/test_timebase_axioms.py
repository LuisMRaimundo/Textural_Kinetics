"""Axioms for quarterLength → seconds (timebase)."""

import pytest

from granular_v2.timebase import TempoSeg, build_tempo_segments, ql_to_seconds_fn


def test_single_segment_linear():
    segs = [TempoSeg(0.0, 4.0, 0.0, 120.0)]
    fn = ql_to_seconds_fn(segs)
    assert fn(0.0) == pytest.approx(0.0)
    assert fn(4.0) == pytest.approx(2.0)  # 4 quarters at 120 BPM = 2 s
    assert fn(2.0) == pytest.approx(1.0)


def test_two_tempo_segments():
    segs = [
        TempoSeg(0.0, 2.0, 0.0, 120.0),
        TempoSeg(2.0, 4.0, 1.0, 60.0),
    ]
    fn = ql_to_seconds_fn(segs)
    assert fn(0.0) == pytest.approx(0.0)
    assert fn(2.0) == pytest.approx(1.0)
    assert fn(4.0) == pytest.approx(3.0)


def test_monotonic_in_segment():
    segs = [TempoSeg(0.0, 8.0, 0.0, 90.0)]
    fn = ql_to_seconds_fn(segs)
    qs = [0.0, 1.0, 2.5, 8.0]
    ts = [fn(q) for q in qs]
    assert ts == sorted(ts)


def test_build_tempo_segments_on_score(sample_musicxml):
    from music21 import converter

    score = converter.parse(str(sample_musicxml))
    segs = build_tempo_segments(score, default_bpm=120.0)
    assert len(segs) >= 1
    fn = ql_to_seconds_fn(segs)
    assert fn(0.0) == pytest.approx(0.0, abs=1e-6)
    t_end = fn(float(score.highestTime))
    assert t_end > 0


def test_loader_onsets_within_score_span(sample_musicxml):
    from granular_v2.loader import load_score_and_note_matrix
    from music21 import converter

    score = converter.parse(str(sample_musicxml))
    segs = build_tempo_segments(score, default_bpm=120.0)
    fn_seg = ql_to_seconds_fn(segs)
    t_end = fn_seg(float(score.highestTime))
    _, nm, audit = load_score_and_note_matrix(sample_musicxml, default_bpm=120.0)
    assert audit.get("source") == "timebase_segments"
    onsets = [float(n["onset_sec"]) for n in nm]
    assert min(onsets) >= -1e-6
    assert max(onsets) <= t_end + 0.05
