"""
Focused regression tests for granular_v2.input_layer.

Exercises MusicXML/MIDI → note-matrix loading without duplicating loader.py
tempo-fallback or pipeline integration coverage.
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

import pytest
from music21 import note, stream, tie

from granular_v2.input_layer import (
    load_file_to_note_matrix,
    load_midi_to_note_matrix,
    load_musicxml_to_note_matrix,
    note_matrix_from_notes_data,
)

ROOT = Path(__file__).resolve().parents[1]
REPEAT_FIXTURE = ROOT / "corpus" / "fixtures" / "musicological_regression" / "repeated_section.musicxml"

NUMERIC_NOTE_FIELDS = ("onset_sec", "duration_sec", "pitch", "velocity", "channel")


def _write_three_note_score(path: Path) -> None:
    part = stream.Part()
    part.append(note.Note("C4", quarterLength=1.0))
    part.append(note.Note("D4", quarterLength=1.0))
    part.append(note.Note("E4", quarterLength=1.0))
    score = stream.Score()
    score.insert(0, part)
    score.write("musicxml", fp=str(path))


def _write_tied_sustain_score(path: Path) -> None:
    part = stream.Part()
    n1 = note.Note("C4", quarterLength=1.0)
    n1.tie = tie.Tie("start")
    n2 = note.Note("C4", quarterLength=1.0)
    n2.tie = tie.Tie("stop")
    part.insert(0, n1)
    part.insert(1, n2)
    score = stream.Score()
    score.insert(0, part)
    score.write("musicxml", fp=str(path))


def _write_repeated_attack_score(path: Path) -> None:
    part = stream.Part()
    part.append(note.Note("C4", quarterLength=1.0))
    part.append(note.Note("C4", quarterLength=1.0))
    score = stream.Score()
    score.insert(0, part)
    score.write("musicxml", fp=str(path))


def _write_rest_gap_score(path: Path) -> None:
    measure = stream.Measure()
    measure.append(note.Note("C4", quarterLength=1.0))
    measure.append(note.Rest(quarterLength=1.0))
    measure.append(note.Note("E4", quarterLength=1.0))
    part = stream.Part()
    part.append(measure)
    score = stream.Score()
    score.insert(0, part)
    score.write("musicxml", fp=str(path))


def _write_two_part_async_score(path: Path) -> None:
    violin = stream.Part()
    violin.partName = "Violin"
    violin.append(note.Note("C4", quarterLength=1.0))
    cello = stream.Part()
    cello.partName = "Cello"
    cello.insert(0.5, note.Note("E4", quarterLength=1.0))
    score = stream.Score()
    score.insert(0, violin)
    score.insert(0, cello)
    score.write("musicxml", fp=str(path))


def _assert_note_matrix_invariants(note_matrix: list[dict]) -> None:
    assert note_matrix
    onsets: list[float] = []
    for row in note_matrix:
        for field in NUMERIC_NOTE_FIELDS:
            assert field in row
            value = float(row[field])
            assert math.isfinite(value), f"non-finite {field}: {value}"
        assert row["duration_sec"] > 0
        assert row["onset_sec"] >= 0
        onsets.append(float(row["onset_sec"]))
    assert onsets == sorted(onsets)


def test_minimal_musicxml_event_count_and_pitches(tmp_path: Path) -> None:
    path = tmp_path / "minimal.musicxml"
    _write_three_note_score(path)
    note_matrix = load_musicxml_to_note_matrix(path)
    assert len(note_matrix) == 3
    assert [row["pitch"] for row in note_matrix] == [60, 62, 64]


def test_minimal_musicxml_invariants_finite_monotonic(tmp_path: Path) -> None:
    path = tmp_path / "minimal.musicxml"
    _write_three_note_score(path)
    note_matrix = load_musicxml_to_note_matrix(path)
    _assert_note_matrix_invariants(note_matrix)


def test_note_matrix_from_notes_data_schema_and_finite_fields() -> None:
    note_matrix = note_matrix_from_notes_data(
        [
            {
                "start": 0.0,
                "duration": 0.5,
                "pitch": 60,
                "velocity": 90,
                "part": "Test",
                "channel": 1,
            },
            {
                "start": 0.5,
                "end": 1.25,
                "pitch": 64,
                "velocity": 80,
                "part": "Test",
            },
        ]
    )
    assert len(note_matrix) == 2
    _assert_note_matrix_invariants(note_matrix)
    assert note_matrix[0]["part"] == "Test"
    assert note_matrix[1]["duration_sec"] == pytest.approx(0.75)


def test_tied_notes_merge_reduces_events_at_input_layer(tmp_path: Path) -> None:
    path = tmp_path / "tied.musicxml"
    _write_tied_sustain_score(path)
    merged = load_musicxml_to_note_matrix(path, merge_ties=True)
    raw = load_musicxml_to_note_matrix(path, merge_ties=False)
    assert len(merged) == 1
    assert len(raw) == 2
    assert merged[0]["duration_sec"] == pytest.approx(1.0)


def test_repeated_attacks_remain_separate_with_merge_ties(tmp_path: Path) -> None:
    path = tmp_path / "repeated.musicxml"
    _write_repeated_attack_score(path)
    note_matrix = load_musicxml_to_note_matrix(path, merge_ties=True)
    assert len(note_matrix) == 2
    assert note_matrix[0]["onset_sec"] == pytest.approx(0.0)
    assert note_matrix[1]["onset_sec"] == pytest.approx(0.5)


def test_sustained_tied_vs_repeated_attacks_distinguishable(tmp_path: Path) -> None:
    tied_path = tmp_path / "tied.musicxml"
    repeated_path = tmp_path / "repeated.musicxml"
    _write_tied_sustain_score(tied_path)
    _write_repeated_attack_score(repeated_path)
    tied = load_musicxml_to_note_matrix(tied_path, merge_ties=True)
    repeated = load_musicxml_to_note_matrix(repeated_path, merge_ties=True)
    assert len(tied) == 1
    assert len(repeated) == 2
    assert tied[0]["duration_sec"] == pytest.approx(1.0)
    assert repeated[0]["duration_sec"] == pytest.approx(0.5)


def test_two_part_score_preserves_parts_and_async_onsets(tmp_path: Path) -> None:
    path = tmp_path / "two_part.musicxml"
    _write_two_part_async_score(path)
    note_matrix = load_musicxml_to_note_matrix(path)
    _assert_note_matrix_invariants(note_matrix)
    parts = {row["part"] for row in note_matrix}
    assert parts == {"Violin", "Cello"}
    onsets = {round(float(row["onset_sec"]), 4) for row in note_matrix}
    assert len(onsets) == 2
    counts: dict[float, int] = defaultdict(int)
    for row in note_matrix:
        counts[round(float(row["onset_sec"]), 4)] += 1
    assert max(counts.values()) == 1


def test_rest_gap_does_not_create_note_events(tmp_path: Path) -> None:
    path = tmp_path / "rest_gap.musicxml"
    _write_rest_gap_score(path)
    note_matrix = load_musicxml_to_note_matrix(path)
    assert len(note_matrix) == 2
    assert [row["pitch"] for row in note_matrix] == [60, 64]
    assert note_matrix[0]["onset_sec"] == pytest.approx(0.0)
    assert note_matrix[1]["onset_sec"] == pytest.approx(1.0)


def test_musicxml_midi_broad_parity_via_load_file(tmp_path: Path) -> None:
    musicxml_path = tmp_path / "score.musicxml"
    midi_path = tmp_path / "score.mid"
    _write_three_note_score(musicxml_path)
    from music21 import converter

    score = converter.parse(str(musicxml_path))
    score.write("midi", fp=str(midi_path))

    xml_matrix = load_file_to_note_matrix(musicxml_path)
    midi_matrix = load_file_to_note_matrix(midi_path)
    _assert_note_matrix_invariants(xml_matrix)
    _assert_note_matrix_invariants(midi_matrix)
    assert len(xml_matrix) == len(midi_matrix)
    assert {row["pitch"] for row in xml_matrix} == {row["pitch"] for row in midi_matrix}
    xml_onsets = [round(float(row["onset_sec"]), 2) for row in xml_matrix]
    midi_onsets = [round(float(row["onset_sec"]), 2) for row in midi_matrix]
    assert xml_onsets == midi_onsets


def test_repeat_expansion_increases_events_and_monotonic_onsets() -> None:
    if not REPEAT_FIXTURE.exists():
        pytest.skip("musicological repeat fixture missing")
    baseline = load_musicxml_to_note_matrix(REPEAT_FIXTURE)
    expanded = load_musicxml_to_note_matrix(REPEAT_FIXTURE, expand_repeats=True)
    assert len(expanded) > len(baseline)
    _assert_note_matrix_invariants(expanded)


def test_repeat_expansion_metadata_flags() -> None:
    if not REPEAT_FIXTURE.exists():
        pytest.skip("musicological repeat fixture missing")
    _, metadata = load_musicxml_to_note_matrix(
        REPEAT_FIXTURE,
        expand_repeats=True,
        return_metadata=True,
    )
    assert metadata["has_repeats"] is True
    assert metadata["expansion_applied"] is True
    assert metadata["merge_ties"] is True


def test_missing_musicxml_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="File not found"):
        load_musicxml_to_note_matrix(tmp_path / "missing.musicxml")


def test_unsupported_extension_raises_value_error(tmp_path: Path) -> None:
    path = tmp_path / "score.txt"
    path.write_text("not music", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file format"):
        load_file_to_note_matrix(path)


def test_malformed_musicxml_raises_value_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.musicxml"
    path.write_text("not valid xml", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid or unsupported MusicXML"):
        load_musicxml_to_note_matrix(path)


def test_load_musicxml_rejects_midi_extension(tmp_path: Path) -> None:
    path = tmp_path / "score.mid"
    path.write_bytes(b"fake")
    with pytest.raises(ValueError, match="Unsupported format"):
        load_musicxml_to_note_matrix(path)


def test_missing_midi_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="File not found"):
        load_midi_to_note_matrix(tmp_path / "missing.mid")
