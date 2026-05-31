"""
Integration: score-global offsets through timebase + loader (real MusicXML path).

Guards against measure-local .offset bugs in build_tempo_segments and note_extraction.
"""

from __future__ import annotations

import pytest
from music21 import bar, note, stream, tempo

from granular_v2.loader import load_score_and_note_matrix
from granular_v2.timebase import build_tempo_segments, ql_to_seconds_fn


def _write_two_measure_two_tempo_xml(path):
    """Minimal MusicXML: 2 measures, 120 then 60 BPM, one note per beat."""
    p = stream.Part()
    m1 = stream.Measure(number=1)
    m1.insert(0, tempo.MetronomeMark(number=120))
    for i in range(4):
        m1.insert(float(i), note.Note("C4", quarterLength=1))
    m2 = stream.Measure(number=2)
    m2.insert(0, tempo.MetronomeMark(number=60))
    for i in range(4):
        m2.insert(float(i), note.Note("D4", quarterLength=1))
    m2.leftBarline = bar.Barline("regular")
    p.append(m1)
    p.append(m2)
    sc = stream.Score()
    sc.insert(0, p)
    sc.write("musicxml", fp=str(path))


def test_build_tempo_segments_global_ql_on_file(tmp_path):
    from music21 import converter

    path = tmp_path / "two_tempo.musicxml"
    _write_two_measure_two_tempo_xml(path)
    sc = converter.parse(str(path))
    segs = build_tempo_segments(sc)
    assert len(segs) >= 2
    assert segs[0].q0 == pytest.approx(0.0)
    assert segs[0].q1 == pytest.approx(4.0)
    assert segs[1].q0 == pytest.approx(4.0)
    fn = ql_to_seconds_fn(segs)
    assert fn(8.0) == pytest.approx(6.0)


def test_loader_onsets_span_multi_measure(tmp_path):
    path = tmp_path / "two_tempo.musicxml"
    _write_two_measure_two_tempo_xml(path)
    _, nm, audit = load_score_and_note_matrix(path)
    onsets = sorted(float(n["onset_sec"]) for n in nm)
    assert len(onsets) == 8
    assert onsets == pytest.approx([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0], abs=1e-6)
    span = max(onsets) - min(onsets)
    assert span == pytest.approx(5.0, abs=1e-6)
    assert audit.get("source") == "timebase_segments"


def test_sparse_homophony_fixture_span_and_rate():
    """Regression: reference must use global QL (span 4s at 60 BPM, not collapsed 2s)."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    fx = root / "corpus" / "fixtures" / "sparse_homophony.musicxml"
    if not fx.exists():
        pytest.skip("sparse_homophony fixture missing")
    _, nm, _ = load_score_and_note_matrix(fx)
    onsets = [float(n["onset_sec"]) for n in nm]
    span = max(onsets) - min(onsets)
    assert span == pytest.approx(4.0, abs=0.15)
    rate = len(nm) / span
    assert rate == pytest.approx(2.25, abs=0.15)
