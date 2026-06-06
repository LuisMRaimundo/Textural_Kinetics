"""Axioms for quarterLength → seconds (timebase)."""

import pytest
from music21 import note, stream, tempo

import granular_v2.timebase as timebase_mod
from granular_v2.timebase import (
    TempoSeg,
    build_tempo_segments,
    convert_notes_times_inplace,
    ql_to_seconds_fn,
)


def _score_delayed_first_tempo_mark() -> stream.Score:
    """Four quarters before the first MetronomeMark at q=4."""
    part = stream.Part()
    m1 = stream.Measure(number=1)
    for i in range(4):
        m1.insert(float(i), note.Note("C4", quarterLength=1))
    m2 = stream.Measure(number=2)
    m2.insert(0, tempo.MetronomeMark(number=60))
    for i in range(4):
        m2.insert(float(i), note.Note("D4", quarterLength=1))
    part.append(m1)
    part.append(m2)
    score = stream.Score()
    score.insert(0, part)
    return score


def _assert_segments_continuous(segs: list[TempoSeg]) -> None:
    for i in range(len(segs) - 1):
        assert segs[i].q1 == pytest.approx(segs[i + 1].q0)
        t_boundary = segs[i].s0 + (60.0 / segs[i].bpm) * (segs[i].q1 - segs[i].q0)
        assert t_boundary == pytest.approx(segs[i + 1].s0)


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


def test_build_tempo_segments_prepends_initial_segment_before_first_mark():
    score = _score_delayed_first_tempo_mark()
    segs = build_tempo_segments(score, default_bpm=120.0)

    assert len(segs) == 2
    assert segs[0].q0 == pytest.approx(0.0)
    assert segs[0].q1 == pytest.approx(4.0)
    assert segs[0].s0 == pytest.approx(0.0)
    assert segs[0].bpm == pytest.approx(60.0)
    assert segs[1].q0 == pytest.approx(4.0)
    assert segs[1].q1 == pytest.approx(float(score.highestTime))
    assert segs[1].s0 == pytest.approx(4.0)
    _assert_segments_continuous(segs)

    fn = ql_to_seconds_fn(segs)
    assert fn(0.0) == pytest.approx(0.0)
    assert fn(4.0) == pytest.approx(4.0)
    assert fn(8.0) == pytest.approx(8.0)


def test_build_tempo_segments_highest_time_non_positive():
    score = stream.Score()
    segs = build_tempo_segments(score, default_bpm=90.0)
    assert segs == [TempoSeg(0.0, 0.0, 0.0, 90.0)]


def test_build_tempo_segments_non_positive_bpm_uses_default():
    part = stream.Part()
    measure = stream.Measure()
    measure.insert(0, tempo.MetronomeMark(number=0))
    measure.insert(0, note.Note("C4", quarterLength=4))
    part.append(measure)
    score = stream.Score()
    score.insert(0, part)

    segs = build_tempo_segments(score, default_bpm=100.0)
    assert len(segs) == 1
    assert segs[0].bpm == pytest.approx(100.0)

    negative_part = stream.Part()
    negative_measure = stream.Measure()
    negative_measure.insert(0, tempo.MetronomeMark(number=-20))
    negative_measure.insert(0, note.Note("D4", quarterLength=4))
    negative_part.append(negative_measure)
    negative_score = stream.Score()
    negative_score.insert(0, negative_part)
    negative_segs = build_tempo_segments(negative_score, default_bpm=100.0)
    assert negative_segs[0].bpm == pytest.approx(100.0)


def test_build_tempo_segments_skips_malformed_q1_before_q0(monkeypatch):
    part = stream.Part()
    measure = stream.Measure()
    first_mark = tempo.MetronomeMark(number=120)
    second_mark = tempo.MetronomeMark(number=60)
    measure.insert(0, note.Note("C4", quarterLength=8))
    measure.insert(0, first_mark)
    measure.insert(4, second_mark)
    part.append(measure)
    score = stream.Score()
    score.insert(0, part)

    real_offset = timebase_mod.global_offset
    highest = float(score.highestTime)

    def _offset(elem, score_ctx, default=0.0):
        if elem is second_mark and default == highest:
            return -1.0
        return real_offset(elem, score_ctx, default=default)

    monkeypatch.setattr(timebase_mod, "global_offset", _offset)

    segs = build_tempo_segments(score, default_bpm=120.0)
    assert len(segs) == 2
    assert segs[0].q0 == pytest.approx(0.0)
    assert segs[0].q1 == pytest.approx(4.0)
    assert segs[1].q0 == pytest.approx(4.0)
    _assert_segments_continuous(segs)


def test_ql_to_seconds_empty_segments_default_bpm():
    fn = ql_to_seconds_fn([])
    assert fn(0.0) == pytest.approx(0.0)
    assert fn(4.0) == pytest.approx(2.0)
    assert fn(None) == pytest.approx(0.0)


def test_ql_to_seconds_extrapolates_beyond_last_segment():
    segs = [TempoSeg(0.0, 4.0, 0.0, 120.0)]
    fn = ql_to_seconds_fn(segs)
    assert fn(6.0) == pytest.approx(3.0)


def test_ql_to_seconds_non_positive_segment_bpm_falls_back():
    segs = [TempoSeg(0.0, 4.0, 0.0, 0.0)]
    fn = ql_to_seconds_fn(segs)
    assert fn(2.0) == pytest.approx(1.0)

    segs_extrap = [TempoSeg(0.0, 2.0, 0.0, 120.0), TempoSeg(2.0, 4.0, 1.0, -5.0)]
    fn_extrap = ql_to_seconds_fn(segs_extrap)
    assert fn_extrap(6.0) == pytest.approx(3.0)


def test_convert_notes_times_inplace_updates_present_fields_only():
    def _double(q: float) -> float:
        return float(q) * 2.0

    notes = [
        {"start": 1.0, "end": 3.0, "time": 2.0, "pitch": 60, "extra": "keep"},
        {"pitch": 72},
    ]
    convert_notes_times_inplace(notes, _double)

    assert notes[0]["start"] == pytest.approx(2.0)
    assert notes[0]["end"] == pytest.approx(6.0)
    assert notes[0]["time"] == pytest.approx(4.0)
    assert notes[0]["pitch"] == 60
    assert notes[0]["extra"] == "keep"
    assert notes[1] == {"pitch": 72}
