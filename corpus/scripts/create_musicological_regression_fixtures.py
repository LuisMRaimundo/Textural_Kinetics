#!/usr/bin/env python3
"""Generate deterministic MusicXML fixtures for musicological regression (phase 1)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from music21 import bar, chord, duration, instrument, metadata, note, stream, tempo, tie

OUT_DIR = ROOT / "corpus" / "fixtures" / "musicological_regression"


def _write(score: stream.Score, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    score.metadata = metadata.Metadata()
    score.metadata.title = name.replace("_", " ").title()
    path = OUT_DIR / f"{name}.musicxml"
    score.write("musicxml", fp=str(path))
    return path


def build_regular_homorhythm() -> stream.Score:
    """Four parts attack together on each quarter (3 simultaneous pitches per attack)."""
    pitches = ["C4", "E4", "G4"]
    score = stream.Score()
    for i, pname in enumerate(["Soprano", "Alto", "Tenor"]):
        part = stream.Part(partName=pname)
        part.id = f"P{i + 1}"
        for meas_num in range(1, 5):
            measure = stream.Measure(number=meas_num)
            if meas_num == 1:
                measure.insert(0, tempo.MetronomeMark(number=120))
            for beat in range(4):
                measure.insert(float(beat), note.Note(pitches[i], quarterLength=1.0))
            part.append(measure)
        score.insert(0, part)
    return score


def build_tied_sustained_texture() -> stream.Score:
    """Tied half notes crossing barlines in two parts."""
    score = stream.Score()
    for pname, pitch in [("Violin", "A4"), ("Cello", "D3")]:
        part = stream.Part(partName=pname)
        part.id = pname
        m1 = stream.Measure(number=1)
        n1 = note.Note(pitch, quarterLength=2.0)
        n1.tie = tie.Tie("start")
        m1.append(n1)
        m2 = stream.Measure(number=2)
        n2 = note.Note(pitch, quarterLength=2.0)
        n2.tie = tie.Tie("stop")
        m2.append(n2)
        m3 = stream.Measure(number=3)
        m3.append(note.Note(pitch, quarterLength=4.0))
        part.append(m1)
        part.append(m2)
        part.append(m3)
        score.insert(0, part)
    return score


def build_dense_chordal_blocks() -> stream.Score:
    """Chordal attacks (4 pitches) separated by rests."""
    score = stream.Score()
    part = stream.Part(partName="Piano")
    part.id = "Piano"
    chord_pitches = [["C4", "E4", "G4", "B4"], ["D4", "F4", "A4", "C5"], ["E4", "G4", "B4", "D5"]]
    measure = stream.Measure(number=1)
    offset = 0.0
    for pitches in chord_pitches:
        measure.insert(offset, chord.Chord(pitches, quarterLength=1.0))
        offset += 1.0
        measure.insert(offset, note.Rest(quarterLength=1.0))
        offset += 1.0
    part.append(measure)
    score.insert(0, part)
    return score


def build_layered_async() -> stream.Score:
    """Three parts with staggered quarter-note entries (no homorhythm)."""
    score = stream.Score()
    patterns = [
        ("LayerA", [0.0, 2.0, 4.0, 6.0]),
        ("LayerB", [0.5, 2.5, 4.5, 6.5]),
        ("LayerC", [1.0, 3.0, 5.0, 7.0]),
    ]
    for pname, onsets in patterns:
        part = stream.Part(partName=pname)
        part.id = pname
        measure = stream.Measure(number=1)
        measure.insert(0, tempo.MetronomeMark(number=120))
        for t in onsets:
            measure.insert(t, note.Note("C4", quarterLength=0.5))
        part.append(measure)
        score.insert(0, part)
    return score


def build_tempo_change_mid_score() -> stream.Score:
    """Two measures at 60 BPM, then two at 120 BPM."""
    score = stream.Score()
    part = stream.Part(partName="Flute")
    part.id = "Flute"
    for meas_num, bpm in [(1, 60), (2, 60), (3, 120), (4, 120)]:
        measure = stream.Measure(number=meas_num)
        measure.insert(0, tempo.MetronomeMark(number=bpm))
        for beat in range(4):
            measure.insert(float(beat), note.Note("G4", quarterLength=1.0))
        part.append(measure)
    score.insert(0, part)
    return score


def build_repeated_section() -> stream.Score:
    """Two-measure repeat: ||: m1-m2 :||"""
    score = stream.Score()
    part = stream.Part(partName="RepeatPart")
    part.id = "RepeatPart"
    m1 = stream.Measure(number=1)
    m1.leftBarline = bar.Repeat(direction="start")
    m1.append(note.Note("C4", quarterLength=4.0))
    m2 = stream.Measure(number=2)
    m2.append(note.Note("D4", quarterLength=4.0))
    m2.rightBarline = bar.Repeat(direction="end")
    part.append(m1)
    part.append(m2)
    score.insert(0, part)
    return score


def build_grace_note_passage() -> stream.Score:
    """Grace notes before principal quarter notes."""
    score = stream.Score()
    part = stream.Part(partName="Oboe")
    part.id = "Oboe"
    measure = stream.Measure(number=1)
    for i in range(4):
        grace = note.Note("D5")
        grace.duration = duration.GraceDuration()
        principal = note.Note("C4", quarterLength=1.0)
        measure.insert(float(i), grace)
        measure.insert(float(i), principal)
    part.append(measure)
    score.insert(0, part)
    return score


def build_transposing_instrument_score() -> stream.Score:
    """B-flat clarinet written as C4."""
    score = stream.Score()
    part = stream.Part(partName="Clarinet")
    part.id = "Clarinet"
    part.insert(0, instrument.Clarinet())
    measure = stream.Measure(number=1)
    measure.append(note.Note("C4", quarterLength=1.0))
    measure.insert(1.0, note.Note("E4", quarterLength=1.0))
    measure.insert(2.0, note.Note("G4", quarterLength=1.0))
    part.append(measure)
    score.insert(0, part)
    return score


def build_multi_voice_polyphony() -> stream.Score:
    """Two voices in one part with offset entries."""
    score = stream.Score()
    part = stream.Part(partName="Piano")
    part.id = "Piano"
    measure = stream.Measure(number=1)
    voice1 = stream.Voice(id="1")
    voice2 = stream.Voice(id="2")
    voice1.insert(0.0, note.Note("C4", quarterLength=1.0))
    voice1.insert(1.0, note.Note("E4", quarterLength=1.0))
    voice2.insert(0.5, note.Note("G4", quarterLength=1.0))
    voice2.insert(1.5, note.Note("B4", quarterLength=1.0))
    measure.insert(0, voice1)
    measure.insert(0, voice2)
    m2 = stream.Measure(number=2)
    m2.append(note.Note("C4", quarterLength=4.0))
    part.append(measure)
    part.append(m2)
    score.insert(0, part)
    return score


def build_empty_or_degenerate_score() -> stream.Score:
    """Score with one empty part (no notes)."""
    score = stream.Score()
    part = stream.Part(partName="Empty")
    part.id = "Empty"
    part.append(stream.Measure(number=1))
    score.insert(0, part)
    return score


BUILDERS = {
    "regular_homorhythm": build_regular_homorhythm,
    "tied_sustained_texture": build_tied_sustained_texture,
    "dense_chordal_blocks": build_dense_chordal_blocks,
    "layered_async": build_layered_async,
    "tempo_change_mid_score": build_tempo_change_mid_score,
    "repeated_section": build_repeated_section,
    "grace_note_passage": build_grace_note_passage,
    "transposing_instrument_score": build_transposing_instrument_score,
    "multi_voice_polyphony": build_multi_voice_polyphony,
    "empty_or_degenerate_score": build_empty_or_degenerate_score,
}


def main() -> int:
    written = []
    for name, builder in BUILDERS.items():
        path = _write(builder(), name)
        written.append(path.name)
        print(f"Wrote {path}")
    print(f"Created {len(written)} fixtures in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
