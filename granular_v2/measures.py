"""Measure timeline and per-bar event rates (seconds + beats)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .note_types import NoteMatrix
from .timebase import build_tempo_segments, ql_to_seconds_fn


@dataclass(frozen=True)
class MeasureInfo:
    number: int
    start_sec: float
    end_sec: float
    duration_sec: float
    beats: float
    start_ql: float


def build_measure_timeline(score, default_bpm: float = 120.0) -> List[MeasureInfo]:
    """Build measure boundaries from first part (seconds via tempo map)."""
    from music21 import stream

    segs = build_tempo_segments(score, default_bpm=default_bpm)
    ql_to_sec = ql_to_seconds_fn(segs)

    parts = list(getattr(score, "parts", []) or [])
    if not parts:
        return []

    part = parts[0]
    measures = list(part.getElementsByClass(stream.Measure))
    if not measures:
        return []

    out: List[MeasureInfo] = []
    for m in measures:
        num = int(getattr(m, "number", len(out) + 1) or len(out) + 1)
        q0 = float(getattr(m, "offset", 0.0) or 0.0)
        qlen = float(getattr(m, "duration", None) and m.duration.quarterLength or 0.0)
        if qlen <= 0:
            ts = getattr(m, "timeSignature", None) or m.getContextByClass(stream.TimeSignature)
            if ts is not None:
                qlen = float(getattr(ts, "barDuration", None) and ts.barDuration.quarterLength or 4.0)
            else:
                qlen = 4.0
        s0 = ql_to_sec(q0)
        s1 = ql_to_sec(q0 + qlen)
        beats = qlen  # quarterLength = quarter-note beats in 4/4
        out.append(
            MeasureInfo(
                number=num,
                start_sec=s0,
                end_sec=s1,
                duration_sec=max(s1 - s0, 1e-9),
                beats=beats,
                start_ql=q0,
            )
        )
    return out


def attach_measure_to_notes(note_matrix: NoteMatrix, measures: List[MeasureInfo]) -> None:
    """In-place: set measure_number, measure_start_sec on each note by onset."""
    if not measures or not note_matrix:
        return
    starts = np.array([m.start_sec for m in measures], dtype=float)
    nums = [m.number for m in measures]
    for n in note_matrix:
        t = float(n.get("onset_sec", 0))
        idx = int(np.searchsorted(starts, t, side="right") - 1)
        idx = max(0, min(idx, len(measures) - 1))
        if idx + 1 < len(measures) and t >= measures[idx + 1].start_sec:
            idx += 1
        m = measures[idx]
        n["measure_number"] = m.number
        n["measure_start_sec"] = m.start_sec
        n["measure_duration_sec"] = m.duration_sec
        n["measure_beats"] = m.beats


def per_bar_event_rates(note_matrix: NoteMatrix, measures: Optional[List[MeasureInfo]] = None) -> List[Dict[str, Any]]:
    """
    Per-bar metrics:
      - onset_count (events starting in bar)
      - events_per_second_in_bar = onset_count / bar_duration_sec
      - events_per_millisecond_in_bar = events_per_second_in_bar / 1000
      - events_per_beat_in_bar = onset_count / beats
    """
    if measures is None:
        by_m: Dict[int, Dict[str, Any]] = {}
        for n in note_matrix:
            mn = n.get("measure_number")
            if mn is None:
                continue
            mn = int(mn)
            if mn not in by_m:
                by_m[mn] = {
                    "measure": mn,
                    "onset_count": 0,
                    "measure_start_sec": float(n.get("measure_start_sec", 0)),
                    "measure_duration_sec": float(n.get("measure_duration_sec", 1)),
                    "measure_beats": float(n.get("measure_beats", 4)),
                }
            by_m[mn]["onset_count"] += 1
        rows = []
        for row in sorted(by_m.values(), key=lambda x: x["measure"]):
            dur = max(row["measure_duration_sec"], 1e-9)
            beats = max(row["measure_beats"], 1e-9)
            c = row["onset_count"]
            eps = c / dur
            row["events_per_second_in_bar"] = eps
            row["events_per_millisecond_in_bar"] = eps / 1000.0
            row["events_per_beat_in_bar"] = c / beats
            rows.append(row)
        return rows

    counts = {m.number: 0 for m in measures}
    for n in note_matrix:
        mn = n.get("measure_number")
        if mn is not None:
            counts[int(mn)] = counts.get(int(mn), 0) + 1
        else:
            t = float(n.get("onset_sec", 0))
            for m in measures:
                if m.start_sec <= t < m.end_sec:
                    counts[m.number] = counts.get(m.number, 0) + 1
                    break

    rows = []
    for m in measures:
        c = counts.get(m.number, 0)
        eps = c / m.duration_sec
        rows.append({
            "measure": m.number,
            "measure_start_sec": m.start_sec,
            "measure_duration_sec": m.duration_sec,
            "measure_beats": m.beats,
            "onset_count": c,
            "events_per_second_in_bar": eps,
            "events_per_millisecond_in_bar": eps / 1000.0,
            "events_per_beat_in_bar": c / max(m.beats, 1e-9),
        })
    return rows
