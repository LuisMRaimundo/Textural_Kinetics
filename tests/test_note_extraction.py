"""Tie-merge reduces spurious onsets."""

import pytest
from music21 import note, stream, tie

from granular_v2.note_extraction import extract_notes_with_ties


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
