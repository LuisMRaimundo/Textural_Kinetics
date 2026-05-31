"""Tempo map: quarterLength → seconds (from unified_musicxml_analyzer)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from music21 import tempo

from .offsets import global_offset


@dataclass(frozen=True)
class TempoSeg:
    q0: float
    q1: float
    s0: float
    bpm: float


def build_tempo_segments(score, default_bpm: float = 120.0) -> List[TempoSeg]:
    marks = list(score.recurse().getElementsByClass(tempo.MetronomeMark))
    marks = [m for m in marks if getattr(m, "number", None) is not None]
    marks.sort(key=lambda m: global_offset(m, score, default=0.0))

    highest = float(getattr(score, "highestTime", 0.0) or 0.0)
    if highest <= 0:
        return [TempoSeg(0.0, 0.0, 0.0, float(default_bpm))]

    if not marks:
        return [TempoSeg(0.0, highest, 0.0, float(default_bpm))]

    segs: List[TempoSeg] = []
    t_sec = 0.0
    for i, mm in enumerate(marks):
        q0 = global_offset(mm, score, default=0.0)
        bpm = float(mm.number or default_bpm)
        if bpm <= 0:
            bpm = float(default_bpm)
        q1 = (
            global_offset(marks[i + 1], score, default=highest)
            if i < len(marks) - 1
            else highest
        )
        if q1 < q0:
            continue
        segs.append(TempoSeg(q0, q1, t_sec, bpm))
        t_sec += (60.0 / bpm) * (q1 - q0)

    if segs and segs[0].q0 > 0:
        bpm0 = segs[0].bpm
        if bpm0 <= 0:
            bpm0 = float(default_bpm)
        seg0 = TempoSeg(0.0, segs[0].q0, 0.0, bpm0)
        shift = (60.0 / bpm0) * (segs[0].q0 - 0.0)
        segs = [seg0] + [TempoSeg(s.q0, s.q1, s.s0 + shift, s.bpm) for s in segs]

    return segs


def ql_to_seconds_fn(segs: List[TempoSeg]) -> Callable[[float], float]:
    def ql_to_sec(q: float) -> float:
        q = float(q or 0.0)
        if not segs:
            return q * 60.0 / 120.0
        for s in segs:
            if s.q0 <= q <= s.q1:
                bpm = s.bpm if s.bpm > 0 else 120.0
                return s.s0 + (60.0 / bpm) * (q - s.q0)
        last = segs[-1]
        bpm = last.bpm if last.bpm > 0 else 120.0
        return last.s0 + (60.0 / bpm) * (q - last.q0)

    return ql_to_sec


def convert_notes_times_inplace(notes_data, ql_to_sec):
    for n in notes_data:
        if "start" in n:
            n["start"] = ql_to_sec(n["start"])
        if "end" in n:
            n["end"] = ql_to_sec(n["end"])
        if "time" in n:
            n["time"] = ql_to_sec(n["time"])
