"""Repeat expansion and metronomeMarkBoundaries fallback paths in util_tempo."""

from __future__ import annotations

import pytest
from music21 import metadata, note, stream, tempo

import granular_v2.util_tempo as util_tempo
from granular_v2.util_tempo import build_seconds_map, expand_repeats_if_requested


def _score_with_measures() -> stream.Score:
    part = stream.Part()
    part.append(note.Note("C4", quarterLength=4))
    score = stream.Score()
    score.insert(0, part)
    return score


class _FakeExpander:
    def __init__(self, stream_obj):
        self._stream = stream_obj

    def process(self):
        return self._processed


def test_expand_success_returns_processed_object(monkeypatch):
    score = _score_with_measures()
    processed = stream.Score()
    processed.insert(0, note.Note("E4", quarterLength=2))
    monkeypatch.setattr(score, "hasMeasures", lambda: True, raising=False)

    def _factory(stream_obj):
        expander = _FakeExpander(stream_obj)
        expander._processed = processed
        return expander

    monkeypatch.setattr("music21.repeat.Expander", _factory)

    out = expand_repeats_if_requested(score, enabled=True)

    assert out is processed


def test_expand_multipart_attribute_copy_failure_still_returns_expanded(monkeypatch):
    class _BrokenOutScore(stream.Score):
        def hasMeasures(self):
            return False

        def __setattr__(self, name, value):
            if name == "metadata" and len(self.parts) == 0:
                raise RuntimeError("metadata copy blocked")
            super().__setattr__(name, value)

    part_one = stream.Part()
    part_two = stream.Part()
    expanded_one = stream.Part()
    expanded_one.append(note.Note("C4", quarterLength=1))
    expanded_two = stream.Part()
    expanded_two.append(note.Note("D4", quarterLength=1))

    opus = _BrokenOutScore()
    opus.insert(0, part_one)
    opus.insert(0, part_two)
    opus.metadata = metadata.Metadata()

    expanded = iter([expanded_one, expanded_two])

    monkeypatch.setattr(
        util_tempo,
        "_expand_stream_repeats",
        lambda _part: next(expanded),
    )

    out = expand_repeats_if_requested(opus, enabled=True)

    assert out is not opus
    assert len(out.parts) == 2


def test_expand_recursion_error_on_process_returns_original(monkeypatch):
    score = _score_with_measures()
    monkeypatch.setattr(score, "hasMeasures", lambda: True, raising=False)

    class _LoopingExpander:
        def __init__(self, _stream_obj):
            pass

        def process(self):
            raise RecursionError("simulated repeat loop")

    monkeypatch.setattr("music21.repeat.Expander", _LoopingExpander)

    out = expand_repeats_if_requested(score, enabled=True)

    assert out is score


def test_expand_generic_failure_on_process_returns_original(monkeypatch):
    score = _score_with_measures()
    monkeypatch.setattr(score, "hasMeasures", lambda: True, raising=False)

    class _FailingExpander:
        def __init__(self, _stream_obj):
            pass

        def process(self):
            raise RuntimeError("simulated repeat failure")

    monkeypatch.setattr("music21.repeat.Expander", _FailingExpander)

    out = expand_repeats_if_requested(score, enabled=True)

    assert out is score


class _FakeTempoStream:
    highestTime = 4.0

    def __init__(self, *, boundaries=None, marks=None, boundaries_error=None):
        self._boundaries = boundaries
        self._marks = list(marks or [])
        self._boundaries_error = boundaries_error

    def metronomeMarkBoundaries(self):
        if self._boundaries_error is not None:
            raise self._boundaries_error
        return list(self._boundaries or [])

    def recurse(self):
        marks = list(self._marks)

        class _Recurse:
            def __init__(self, stored_marks):
                self._stored_marks = stored_marks

            def getElementsByClass(self, cls):
                if cls is tempo.MetronomeMark:
                    return self._stored_marks
                return []

        return _Recurse(marks)


def test_build_seconds_map_empty_boundaries_uses_global_fallback():
    fake = _FakeTempoStream(
        boundaries=[],
        marks=[tempo.MetronomeMark(number=90)],
    )

    fn = build_seconds_map(fake)
    info = fn.tempo_info

    assert info["tempo_fallback_used"] is True
    assert info["source"] == "global_bpm_fallback"
    assert info["n_tempo_segments"] == 1
    assert info["reason"] is not None
    assert "metronomeMarkBoundaries failed" in info["reason"]
    assert fn(1.0) == pytest.approx(60.0 / 90.0)


def test_build_seconds_map_boundaries_exception_uses_global_fallback():
    fake = _FakeTempoStream(
        boundaries_error=RuntimeError("boundaries unavailable"),
        marks=[tempo.MetronomeMark(number=90)],
    )

    fn = build_seconds_map(fake)
    info = fn.tempo_info

    assert info["tempo_fallback_used"] is True
    assert info["source"] == "global_bpm_fallback"
    assert "boundaries unavailable" in info["reason"]
    assert fn(2.0) == pytest.approx(2.0 * 60.0 / 90.0)


def test_build_seconds_map_global_metronome_mark_fallback_info():
    fake = _FakeTempoStream(
        boundaries=[],
        marks=[tempo.MetronomeMark(number=90)],
    )

    fn = build_seconds_map(fake)
    info = fn.tempo_info

    assert info["tempo_fallback_used"] is True
    assert info["source"] == "global_bpm_fallback"
    assert info["n_tempo_segments"] == 1
    assert "90 BPM" in info["reason"]


def test_build_seconds_map_final_120_bpm_fallback():
    fake = _FakeTempoStream(boundaries=[], marks=[])

    fn = build_seconds_map(fake)
    info = fn.tempo_info

    assert info["tempo_fallback_used"] is True
    assert info["source"] == "global_bpm_fallback"
    assert "120 BPM" in info["reason"]
    assert fn(2.0) == pytest.approx(1.0)
