"""
Tie-aware note extraction (from unified_musicxml_analyzer ScoreProcessor).
Events use quarterLength for start/end until converted to seconds by the caller.
"""

from __future__ import annotations

from typing import Any, Dict, List

from music21 import chord as m21chord
from music21 import note as m21note

from .offsets import global_ql


def extract_notes_with_ties(score, merge_ties: bool = True) -> List[Dict[str, Any]]:
    """
    Extract notes per part; optionally merge tied notes to avoid onset inflation.

    Output keys: start, end, duration, pitch, pitch_name, velocity, part (QL space for start/end).
    """
    out: List[Dict[str, Any]] = []

    if not getattr(score, "parts", None):
        return out

    for part in score.parts:
        part_name = part.partName or "Unknown"
        active: Dict[int, Dict[str, Any]] = {}

        def flush_active():
            nonlocal out, active
            for _midi, ev in active.items():
                ev["duration"] = float(ev["end"]) - float(ev["start"])
                out.append(ev)
            active.clear()

        for el in part.recurse().notes:
            if isinstance(el, m21note.Note):
                start = global_ql(el, score, part)
                dur = float(el.duration.quarterLength) if el.duration else 0.0
                end = start + dur
                midi = int(el.pitch.midi)
                vel = 64
                try:
                    if el.volume and el.volume.velocity is not None:
                        vel = int(el.volume.velocity)
                except Exception:
                    vel = 64

                tie_type = None
                if getattr(el, "tie", None) is not None:
                    tie_type = getattr(el.tie, "type", None)

                base = {
                    "start": start,
                    "end": end,
                    "duration": dur,
                    "pitch": midi,
                    "pitch_name": el.pitch.nameWithOctave,
                    "velocity": vel,
                    "part": part_name,
                    "onset_beats": start,
                    "duration_beats": dur,
                }

                if not merge_ties or tie_type is None:
                    out.append(base)
                    continue

                if tie_type in ("start", "continue"):
                    if midi not in active:
                        active[midi] = dict(base)
                    else:
                        active[midi]["end"] = max(float(active[midi]["end"]), float(end))
                        active[midi]["duration"] = float(active[midi]["end"]) - float(active[midi]["start"])
                elif tie_type == "stop":
                    if midi in active:
                        active[midi]["end"] = max(float(active[midi]["end"]), float(end))
                        active[midi]["duration"] = float(active[midi]["end"]) - float(active[midi]["start"])
                        out.append(active.pop(midi))
                    else:
                        out.append(base)
                else:
                    out.append(base)

            elif isinstance(el, m21chord.Chord):
                start = global_ql(el, score, part)
                dur = float(el.duration.quarterLength) if el.duration else 0.0
                end = start + dur
                vel = 64
                try:
                    if el.volume and el.volume.velocity is not None:
                        vel = int(el.volume.velocity)
                except Exception:
                    vel = 64

                chord_tie = None
                if getattr(el, "tie", None) is not None:
                    chord_tie = getattr(el.tie, "type", None)

                for p in el.pitches:
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
                    }

                    if not merge_ties or chord_tie is None:
                        out.append(base)
                        continue

                    if chord_tie in ("start", "continue"):
                        if midi not in active:
                            active[midi] = dict(base)
                        else:
                            active[midi]["end"] = max(float(active[midi]["end"]), float(end))
                            active[midi]["duration"] = float(active[midi]["end"]) - float(active[midi]["start"])
                    elif chord_tie == "stop":
                        if midi in active:
                            active[midi]["end"] = max(float(active[midi]["end"]), float(end))
                            active[midi]["duration"] = float(active[midi]["end"]) - float(active[midi]["start"])
                            out.append(active.pop(midi))
                        else:
                            out.append(base)
                    else:
                        out.append(base)

        flush_active()

    out.sort(key=lambda d: (d.get("start", 0.0), d.get("part", ""), d.get("pitch", 0)))
    return out
