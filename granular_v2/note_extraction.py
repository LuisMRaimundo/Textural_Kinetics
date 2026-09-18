"""
Tie-aware note extraction (from unified_musicxml_analyzer ScoreProcessor).
Events use quarterLength for start/end until converted to seconds by the caller.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from music21 import chord as m21chord
from music21 import note as m21note

from .offsets import global_ql


def _part_label(part) -> str:
    name = (getattr(part, "partName", None) or "").strip()
    if name:
        return name
    try:
        ins = part.getInstrument(returnDefault=False)
    except Exception:
        ins = None
    if ins and getattr(ins, "instrumentName", None):
        iname = str(ins.instrumentName).strip()
        if iname:
            return iname
    pid = getattr(part, "id", None)
    if isinstance(pid, str):
        pid = pid.strip()
        if pid and not pid.isdigit():
            return pid
    return "Unknown"


def _is_grace(el) -> bool:
    try:
        if getattr(el, "quarterLength", None) == 0:
            return True
        d = getattr(el, "duration", None)
        return bool(getattr(d, "isGrace", False))
    except Exception:
        return False


def _tie_type(el, pitch_index: Optional[int] = None) -> Optional[str]:
    """Per-pitch tie if present; otherwise the element-level tie."""
    if pitch_index is not None:
        notes = getattr(el, "notes", None)
        if notes is not None and 0 <= pitch_index < len(notes):
            t = getattr(notes[pitch_index], "tie", None)
            if t is not None:
                return getattr(t, "type", None)
    t = getattr(el, "tie", None)
    if t is not None:
        return getattr(t, "type", None)
    return None


def _velocity(el) -> int:
    vel = 64
    try:
        if el.volume and el.volume.velocity is not None:
            vel = int(el.volume.velocity)
    except Exception:
        vel = 64
    return vel


def extract_notes_with_ties(score, merge_ties: bool = True) -> List[Dict[str, Any]]:
    """
    Extract notes per part; optionally merge tied notes to avoid onset inflation.

    A notated element is a continuation only when every pitch in it is tied from
    the previous element. A chord with at least one new pitch yields a new attack
    (the new pitch starts a new row; tied pitches extend their earlier rows).

    Output keys: start, end, duration, pitch, pitch_name, velocity, part, is_grace
    (QL space for start/end).
    """
    out: List[Dict[str, Any]] = []

    if not getattr(score, "parts", None):
        return out

    for part_index, part in enumerate(score.parts, start=1):
        part_name = _part_label(part)
        if part_name == "Unknown":
            part_name = f"Part-{part_index}"
        active: Dict[int, Dict[str, Any]] = {}

        def flush_active():
            nonlocal out, active
            for _midi, ev in active.items():
                ev["duration"] = float(ev["end"]) - float(ev["start"])
                out.append(ev)
            active.clear()

        def emit_or_merge(base: Dict[str, Any], midi: int, tie_type: Optional[str]) -> None:
            if not merge_ties or tie_type is None:
                out.append(base)
                return
            if tie_type in ("start", "continue"):
                if midi not in active:
                    active[midi] = dict(base)
                else:
                    active[midi]["end"] = max(float(active[midi]["end"]), float(base["end"]))
                    active[midi]["duration"] = float(active[midi]["end"]) - float(active[midi]["start"])
            elif tie_type == "stop":
                if midi in active:
                    active[midi]["end"] = max(float(active[midi]["end"]), float(base["end"]))
                    active[midi]["duration"] = float(active[midi]["end"]) - float(active[midi]["start"])
                    out.append(active.pop(midi))
                else:
                    out.append(base)
            else:
                out.append(base)

        for el in part.recurse().notes:
            is_grace = _is_grace(el)
            if isinstance(el, m21note.Note):
                start = global_ql(el, score, part)
                dur = float(el.duration.quarterLength) if el.duration else 0.0
                end = start + dur
                midi = int(el.pitch.midi)
                base = {
                    "start": start,
                    "end": end,
                    "duration": dur,
                    "pitch": midi,
                    "pitch_name": el.pitch.nameWithOctave,
                    "velocity": _velocity(el),
                    "part": part_name,
                    "onset_beats": start,
                    "duration_beats": dur,
                    "is_grace": is_grace,
                }
                emit_or_merge(base, midi, _tie_type(el))

            elif isinstance(el, m21chord.Chord):
                start = global_ql(el, score, part)
                dur = float(el.duration.quarterLength) if el.duration else 0.0
                end = start + dur
                vel = _velocity(el)
                for idx, p in enumerate(el.pitches):
                    midi = int(p.midi)
                    base = {
                        "start": start,
                        "end": end,
                        "duration": dur,
                        "pitch": midi,
                        "pitch_name": p.nameWithOctave,
                        "velocity": vel,
                        "part": part_name,
                        "onset_beats": start,
                        "duration_beats": dur,
                        "is_grace": is_grace,
                    }
                    emit_or_merge(base, midi, _tie_type(el, idx))

        flush_active()

    out.sort(key=lambda d: (d.get("start", 0.0), d.get("part", ""), d.get("pitch", 0)))
    return out
