"""
Branch coverage for util_tempo.py — paths that degrade silently.

Exercises score_has_repeats, expand_repeats_if_requested, build_seconds_map
fallback, and dense multi-segment tempo accumulation (regression for boundary bug).
"""

from __future__ import annotations

import pytest
from music21 import bar, note, stream, tempo

from granular_v2.util_tempo import (
    build_seconds_map,
    expand_repeats_if_requested,
    score_has_repeats,
)


def _score_no_tempo() -> stream.Score:
    p = stream.Part()
    for _ in range(4):
        p.append(note.Note("C4", quarterLength=1))
    sc = stream.Score()
    sc.insert(0, p)
    return sc


def _score_with_full_repeat() -> stream.Score:
    p = stream.Part()
    m1 = stream.Measure(number=1)
    m1.leftBarline = bar.Repeat(direction="start")
    m1.append(note.Note("C4", quarterLength=4))
    m2 = stream.Measure(number=2)
    m2.append(note.Note("D4", quarterLength=4))
    m2.rightBarline = bar.Repeat(direction="end")
    p.append(m1)
    p.append(m2)
    sc = stream.Score()
    sc.insert(0, p)
    return sc


def _score_with_start_repeat_only() -> stream.Score:
    p = stream.Part()
    m1 = stream.Measure(number=1)
    m1.leftBarline = bar.Repeat(direction="start")
    m1.append(note.Note("C4", quarterLength=4))
    m2 = stream.Measure(number=2)
    m2.append(note.Note("D4", quarterLength=4))
    p.append(m1)
    p.append(m2)
    sc = stream.Score()
    sc.insert(0, p)
    return sc


def _count_notes(s) -> int:
    return len(list(s.recurse().getElementsByClass(note.Note)))


def test_score_has_repeats_true():
    assert score_has_repeats(_score_with_full_repeat()) is True


def test_score_has_repeats_false():
    assert score_has_repeats(_score_no_tempo()) is False


def test_expand_disabled_returns_same_object():
    sc = _score_with_full_repeat()
    out = expand_repeats_if_requested(sc, enabled=False)
    assert out is sc


def test_expand_full_repeat_duplicates_events():
    sc = _score_with_full_repeat()
    n_before = _count_notes(sc)
    out = expand_repeats_if_requested(sc, enabled=True)
    n_after = _count_notes(out)
    assert n_after >= n_before
    assert n_after == pytest.approx(2 * n_before, abs=0)


def test_expand_start_repeat_only_is_safe_noop():
    sc = _score_with_start_repeat_only()
    n_before = _count_notes(sc)
    out = expand_repeats_if_requested(sc, enabled=True)
    assert _count_notes(out) == n_before


def test_expand_recursion_error_returns_original(monkeypatch):
    sc = _score_with_full_repeat()

    class _Boom:
        def __init__(self, *_a, **_k):
            raise RecursionError("simulated repeat loop")

    monkeypatch.setattr("music21.repeat.Expander", _Boom)
    part = sc.parts[0]
    out = expand_repeats_if_requested(part, enabled=True)
    assert out is part


def test_seconds_map_no_explicit_tempo_defaults_like_120():
    """No MetronomeMark: music21 may still return boundaries; times match ~120 BPM."""
    sc = _score_no_tempo()
    fn = build_seconds_map(sc)
    assert fn(0.0) == pytest.approx(0.0)
    assert fn(1.0) == pytest.approx(0.5)
    assert fn(4.0) == pytest.approx(2.0)
    assert "tempo_info" in dir(fn) or hasattr(fn, "tempo_info")


def test_seconds_map_single_tempo_60():
    p = stream.Part()
    p.insert(0, tempo.MetronomeMark(number=60))
    for i in range(4):
        p.append(note.Note("C4", quarterLength=1))
    sc = stream.Score()
    sc.insert(0, p)
    fn = build_seconds_map(sc)
    assert fn(1.0) == pytest.approx(1.0)
    assert fn(4.0) == pytest.approx(4.0)


def test_seconds_map_monotonic_and_nonnegative():
    sc = _score_no_tempo()
    fn = build_seconds_map(sc)
    qs = [0.0, 0.5, 1.0, 2.0, 3.0, 4.0]
    ts = [fn(q) for q in qs]
    assert all(t >= -1e-9 for t in ts)
    assert ts == sorted(ts)


def test_dense_tempo_changes_accumulate_correctly():
    p = stream.Part()
    bpms = [120, 90, 60, 144, 72, 108, 96, 60]
    for i, b in enumerate(bpms):
        p.insert(float(i), tempo.MetronomeMark(number=b))
        p.insert(float(i), note.Note("C4", quarterLength=1))
    sc = stream.Score()
    sc.insert(0, p)
    fn = build_seconds_map(sc)
    expected_end = sum(60.0 / b for b in bpms)
    assert fn(float(len(bpms))) == pytest.approx(expected_end, abs=1e-6)
    ts = [fn(float(i)) for i in range(len(bpms) + 1)]
    assert ts == sorted(ts)


def test_two_tempo_score_fn4_is_three_seconds():
    """Regression: fn(4.0) was 6.0 before _boundary_offset fix."""
    p = stream.Part()
    p.insert(0, tempo.MetronomeMark(number=120))
    p.insert(0, note.Note("C4", quarterLength=2))
    p.insert(2, tempo.MetronomeMark(number=60))
    p.insert(2, note.Note("D4", quarterLength=2))
    sc = stream.Score()
    sc.insert(0, p)
    fn = build_seconds_map(sc)
    assert fn(2.0) == pytest.approx(1.0)
    assert fn(4.0) == pytest.approx(3.0)
