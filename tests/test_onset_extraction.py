"""Onset extraction: part labels, filtering, grace notes, and window resolution."""

from __future__ import annotations

import pytest
from music21 import duration, instrument, note, stream

from granular_v2.onset_extraction import (
    _is_grace,
    _part_label,
    extract_onsets_per_layer_ms_from_score,
    resolve_granularity_window_ms,
)


def _part_with_notes(*elements, part_name: str = "", part_id: str = "P1") -> stream.Part:
    part = stream.Part()
    part.id = part_id
    part.partName = part_name
    measure = stream.Measure()
    offset = 0.0
    for el in elements:
        measure.insert(offset, el)
        offset += float(getattr(el, "quarterLength", 0.0) or 0.0)
    part.append(measure)
    return part


def _score_with_parts(*parts: stream.Part) -> stream.Score:
    score = stream.Score()
    for part in parts:
        score.insert(0, part)
    return score


def test_part_label_uses_instrument_name():
    part = stream.Part()
    part.partName = ""
    part.insert(0, instrument.Instrument(instrumentName="Custom Horn"))
    part.append(stream.Measure([note.Note("C4", quarterLength=1)]))

    assert _part_label(part) == "Custom Horn"


def test_part_label_falls_back_to_part_id():
    part = stream.Part()
    part.id = "AltoPart"
    part.partName = ""
    part.append(stream.Measure([note.Note("D4", quarterLength=1)]))

    assert _part_label(part) == "AltoPart"


def test_part_filter_includes_only_selected_part():
    horn = _part_with_notes(note.Note("C4", quarterLength=1), part_id="H1")
    horn.partName = ""
    horn.insert(0, instrument.Instrument(instrumentName="Horn"))

    violin = _part_with_notes(note.Note("E4", quarterLength=1), part_name="Violin", part_id="V1")
    score = _score_with_parts(horn, violin)

    layers, _, _, _ = extract_onsets_per_layer_ms_from_score(
        score, part_filter=["Horn"]
    )

    assert set(layers) == {"Horn"}
    assert len(layers["Horn"]) == 1


def test_rests_do_not_generate_onsets():
    part = _part_with_notes(
        note.Rest(quarterLength=1),
        note.Note("G4", quarterLength=1),
        part_name="Flute",
    )
    score = _score_with_parts(part)

    layers, t_end_ms, _, _ = extract_onsets_per_layer_ms_from_score(score)

    assert layers["Flute"] == [pytest.approx(500.0)]
    assert t_end_ms == pytest.approx(1000.0)


def test_grace_note_excluded_when_ignore_grace_true():
    grace = note.Note("A4")
    grace.duration = duration.GraceDuration()
    ordinary = note.Note("B4", quarterLength=1)
    part = _part_with_notes(grace, ordinary, part_name="Oboe")
    score = _score_with_parts(part)

    assert _is_grace(grace) is True

    layers, _, _, _ = extract_onsets_per_layer_ms_from_score(score, ignore_grace=True)

    assert len(layers["Oboe"]) == 1
    assert layers["Oboe"][0] == pytest.approx(0.0)


def test_grace_note_included_when_ignore_grace_false():
    grace = note.Note("A4")
    grace.duration = duration.GraceDuration()
    ordinary = note.Note("B4", quarterLength=1)
    part = _part_with_notes(grace, ordinary, part_name="Oboe")
    score = _score_with_parts(part)

    layers, _, _, _ = extract_onsets_per_layer_ms_from_score(score, ignore_grace=False)

    assert len(layers["Oboe"]) == 2
    assert layers["Oboe"][0] == pytest.approx(0.0)


def test_is_grace_true_for_zero_quarter_length():
    n = note.Note("C4")
    n.duration.quarterLength = 0
    assert _is_grace(n) is True


def test_is_grace_exception_fallback_returns_false():
    class _BrokenElement:
        @property
        def quarterLength(self):
            raise RuntimeError("grace probe failed")

    assert _is_grace(_BrokenElement()) is False


def test_flatten_fallback_when_flatten_raises(monkeypatch):
    part = _part_with_notes(note.Note("C4", quarterLength=1), part_name="Cello")
    score = _score_with_parts(part)
    notes_and_rests = list(part.recurse().notesAndRests)

    class _FlatFallback:
        notesAndRests = notes_and_rests

    def _raise_flatten(*_args, **_kwargs):
        raise RuntimeError("flatten failed")

    original_flat = type(part).flat
    monkeypatch.setattr(part, "flatten", _raise_flatten)
    monkeypatch.setattr(
        type(part),
        "flat",
        property(lambda self: _FlatFallback() if self is part else original_flat.fget(self)),
    )

    layers, t_end_ms, _, _ = extract_onsets_per_layer_ms_from_score(score)

    assert layers["Cello"] == [pytest.approx(0.0)]
    assert t_end_ms == pytest.approx(500.0)


def test_highest_time_fallback_when_access_raises(monkeypatch):
    part = _part_with_notes(note.Note("C4", quarterLength=1), part_name="Bass")
    score = _score_with_parts(part)
    original_highest = type(score).highestTime
    calls = {"n": 0}

    def _broken_highest(self):
        if self is score:
            calls["n"] += 1
            if calls["n"] > 1:
                raise RuntimeError("highestTime failed")
        return original_highest.fget(self)

    monkeypatch.setattr(type(score), "highestTime", property(_broken_highest))

    layers, t_end_ms, score_end_ms, _ = extract_onsets_per_layer_ms_from_score(score)

    assert calls["n"] >= 2
    assert layers["Bass"] == [pytest.approx(0.0)]
    assert t_end_ms == pytest.approx(500.0)
    assert score_end_ms == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("window_ms", "t_end_ms", "score_end_ms", "clamp_ratio", "expected"),
    [
        (5000.0, 1000.0, 8000.0, 1.25, 5000.0),
        (None, 1000.0, 2000.0, 1.25, 1000.0),
        (None, 1000.0, 1100.0, 1.25, 1100.0),
        (None, 500.0, 0.0, 1.25, 500.0),
        (None, 0.0, 300.0, 1.25, 300.0),
        (None, 0.0, 0.0, 1.25, 10000.0),
    ],
    ids=[
        "explicit_window",
        "clamp_to_last_event",
        "max_score_and_last_event",
        "fallback_last_event",
        "fallback_score_ms",
        "fallback_default_10s",
    ],
)
def test_resolve_granularity_window_ms(window_ms, t_end_ms, score_end_ms, clamp_ratio, expected):
    result = resolve_granularity_window_ms(
        window_ms,
        t_end_ms,
        score_end_ms,
        clamp_ratio=clamp_ratio,
    )
    assert result == pytest.approx(expected)
