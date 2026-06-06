"""Tie-merge reduces spurious onsets."""

import pytest
from music21 import chord, note, stream, tie, volume

from granular_v2.note_extraction import extract_notes_with_ties


def _score_with_part(*elements, part_name: str = "Violin") -> stream.Score:
    part = stream.Part()
    part.partName = part_name
    measure = stream.Measure()
    offset = 0.0
    for el in elements:
        measure.insert(offset, el)
        offset += float(el.duration.quarterLength)
    part.append(measure)
    score = stream.Score()
    score.insert(0, part)
    return score


def test_merge_ties_single_pitch():
    p = stream.Part()
    n1 = note.Note("C4", quarterLength=1.0)
    n1.tie = tie.Tie("start")
    n2 = note.Note("C4", quarterLength=1.0)
    n2.tie = tie.Tie("stop")
    p.insert(0, n1)
    p.insert(1, n2)
    sc = stream.Score()
    sc.insert(0, p)

    merged = extract_notes_with_ties(sc, merge_ties=True)
    raw = extract_notes_with_ties(sc, merge_ties=False)
    assert len(merged) < len(raw)
    assert len(merged) == 1
    assert merged[0]["duration"] == pytest.approx(2.0)


def test_merge_ties_on_fixture(sample_musicxml):
    from granular_v2.loader import load_score_and_note_matrix

    _, nm_merged, _ = load_score_and_note_matrix(sample_musicxml, merge_ties=True)
    _, nm_raw, _ = load_score_and_note_matrix(sample_musicxml, merge_ties=False)
    # fixture may have no ties; at least merged count <= raw
    assert len(nm_merged) <= len(nm_raw)


def test_score_without_parts_returns_empty():
    assert extract_notes_with_ties(stream.Score()) == []

    class _NoParts:
        pass

    assert extract_notes_with_ties(_NoParts()) == []


def test_simple_untied_note_fields():
    n = note.Note("E4", quarterLength=2.0)
    score = _score_with_part(n, part_name="Cello")

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 1
    ev = events[0]
    assert ev["pitch"] == 64
    assert ev["pitch_name"] == "E4"
    assert ev["start"] == pytest.approx(0.0)
    assert ev["end"] == pytest.approx(2.0)
    assert ev["duration"] == pytest.approx(2.0)
    assert ev["velocity"] == 64
    assert ev["part"] == "Cello"
    assert ev["onset_beats"] == pytest.approx(0.0)
    assert ev["duration_beats"] == pytest.approx(2.0)


def test_note_with_explicit_velocity():
    n = note.Note("G4", quarterLength=1.0)
    n.volume = volume.Volume(velocity=95)
    score = _score_with_part(n)

    events = extract_notes_with_ties(score)
    assert len(events) == 1
    assert events[0]["velocity"] == 95


def test_note_velocity_fallback_on_volume_error(monkeypatch):
    n = note.Note("A4", quarterLength=1.0)

    class _BrokenVolume:
        @property
        def velocity(self):
            raise RuntimeError("volume access failed")

    monkeypatch.setattr(n, "_volume", _BrokenVolume(), raising=False)
    score = _score_with_part(n)

    events = extract_notes_with_ties(score)
    assert len(events) == 1
    assert events[0]["velocity"] == 64


def test_tied_note_start_continue_stop_merges_to_one_event():
    n1 = note.Note("C4", quarterLength=1.0)
    n1.tie = tie.Tie("start")
    n2 = note.Note("C4", quarterLength=1.0)
    n2.tie = tie.Tie("continue")
    n3 = note.Note("C4", quarterLength=1.0)
    n3.tie = tie.Tie("stop")
    score = _score_with_part(n1, n2, n3)

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 1
    ev = events[0]
    assert ev["start"] == pytest.approx(0.0)
    assert ev["end"] == pytest.approx(3.0)
    assert ev["duration"] == pytest.approx(3.0)
    assert ev["pitch"] == 60


def test_tied_note_start_without_stop_flushes_at_part_end():
    n1 = note.Note("D4", quarterLength=1.5)
    n1.tie = tie.Tie("start")
    n2 = note.Note("D4", quarterLength=1.0)
    n2.tie = tie.Tie("continue")
    score = _score_with_part(n1, n2)

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 1
    ev = events[0]
    assert ev["start"] == pytest.approx(0.0)
    assert ev["end"] == pytest.approx(2.5)
    assert ev["duration"] == pytest.approx(2.5)


def test_chord_with_explicit_velocity():
    c = chord.Chord(["C4", "E4"], quarterLength=1.0)
    c.volume = volume.Volume(velocity=88)
    score = _score_with_part(c)

    events = extract_notes_with_ties(score)
    assert len(events) == 2
    assert all(ev["velocity"] == 88 for ev in events)


def test_chord_extracts_one_event_per_pitch():
    c = chord.Chord(["C4", "E4", "G4"], quarterLength=2.0)
    score = _score_with_part(c, part_name="Piano")

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 3
    pitches = sorted(ev["pitch"] for ev in events)
    assert pitches == [60, 64, 67]
    for ev in events:
        assert ev["start"] == pytest.approx(0.0)
        assert ev["end"] == pytest.approx(2.0)
        assert ev["duration"] == pytest.approx(2.0)
        assert ev["part"] == "Piano"


def test_chord_tie_start_stop_merges_each_pitch():
    c1 = chord.Chord(["C4", "E4"], quarterLength=1.0)
    c1.tie = tie.Tie("start")
    c2 = chord.Chord(["C4", "E4"], quarterLength=1.5)
    c2.tie = tie.Tie("stop")
    score = _score_with_part(c1, c2)

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 2
    by_pitch = {ev["pitch"]: ev for ev in events}
    assert set(by_pitch) == {60, 64}
    for ev in by_pitch.values():
        assert ev["start"] == pytest.approx(0.0)
        assert ev["end"] == pytest.approx(2.5)
        assert ev["duration"] == pytest.approx(2.5)


def test_chord_velocity_fallback_on_volume_error(monkeypatch):
    c = chord.Chord(["C4", "E4"], quarterLength=1.0)
    score = _score_with_part(c)

    class _BrokenVolume:
        @property
        def velocity(self):
            raise RuntimeError("chord volume failed")

    original_volume = chord.Chord.volume

    def _patched_volume(self):
        if self is c:
            return _BrokenVolume()
        return original_volume.fget(self)

    monkeypatch.setattr(chord.Chord, "volume", property(_patched_volume))

    events = extract_notes_with_ties(score)
    assert len(events) == 2
    assert all(ev["velocity"] == 64 for ev in events)


def test_chord_tie_continue_extends_active_pitch():
    c1 = chord.Chord(["C4", "E4"], quarterLength=1.0)
    c1.tie = tie.Tie("start")
    c2 = chord.Chord(["C4", "E4"], quarterLength=1.0)
    c2.tie = tie.Tie("continue")
    c3 = chord.Chord(["C4", "E4"], quarterLength=1.0)
    c3.tie = tie.Tie("stop")
    score = _score_with_part(c1, c2, c3)

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 2
    for ev in events:
        assert ev["duration"] == pytest.approx(3.0)


def test_unhandled_tie_type_emits_unmerged_event():
    n = note.Note("B4", quarterLength=1.0)
    n.tie = tie.Tie("let-ring")
    score = _score_with_part(n)

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 1
    assert events[0]["duration"] == pytest.approx(1.0)


def test_chord_tie_stop_without_active_emits_standalone_events():
    c = chord.Chord(["D4", "F4"], quarterLength=1.0)
    c.tie = tie.Tie("stop")
    score = _score_with_part(c)

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 2
    assert {ev["pitch"] for ev in events} == {62, 65}


def test_chord_unhandled_tie_type_emits_unmerged_events():
    c = chord.Chord(["G4", "B4"], quarterLength=1.5)
    c.tie = tie.Tie("let-ring")
    score = _score_with_part(c)

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 2
    assert all(ev["duration"] == pytest.approx(1.5) for ev in events)


def test_tie_stop_without_active_emits_standalone_event():
    n = note.Note("F4", quarterLength=1.0)
    n.tie = tie.Tie("stop")
    score = _score_with_part(n)

    events = extract_notes_with_ties(score, merge_ties=True)

    assert len(events) == 1
    assert events[0]["pitch"] == 65
    assert events[0]["duration"] == pytest.approx(1.0)
