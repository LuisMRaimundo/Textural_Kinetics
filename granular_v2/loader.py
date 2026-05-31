"""Single-parse loader: score + note matrix + auditable tempo metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Union

from .audit import append_warning
from .input_layer import load_file_to_note_matrix, note_matrix_from_notes_data
from .note_extraction import extract_notes_with_ties
from .timebase import build_tempo_segments, ql_to_seconds_fn
from .util_tempo import build_seconds_map

TempoAudit = Dict[str, Any]


def _timebase_audit(score, default_bpm: float) -> TempoAudit:
    segs = build_tempo_segments(score, default_bpm=default_bpm)
    return {
        "tempo_fallback_used": len(segs) <= 1 and float(segs[0].bpm) == float(default_bpm),
        "n_tempo_segments": len(segs),
        "reason": None,
        "source": "timebase_segments",
        "default_bpm": float(default_bpm),
        "tempo_model": "stepwise_plateau",
        "warnings": [],
    }


def _ql_map(
    score,
    use_tempo_map: bool,
    default_bpm: float,
) -> Tuple[Callable[[float], float], TempoAudit]:
    """
    Canonical: segment timebase first; build_seconds_map fallback (with tempo_info).
    """
    audit_fb: TempoAudit = {"warnings": []}
    if use_tempo_map:
        try:
            segs = build_tempo_segments(score, default_bpm=default_bpm)
            return ql_to_seconds_fn(segs), _timebase_audit(score, default_bpm)
        except Exception as e:
            append_warning(
                audit_fb,
                "timebase_segments_failed",
                f"build_tempo_segments failed ({e}); trying metronomeMarkBoundaries.",
            )
        try:
            fn = build_seconds_map(score)
            audit = dict(getattr(fn, "tempo_info", {}))
            audit.setdefault("source", "metronomeMarkBoundaries")
            audit.setdefault("warnings", []).extend(audit_fb.get("warnings", []))
            return fn, audit
        except Exception as e:
            append_warning(
                audit_fb,
                "metronome_boundaries_failed",
                f"build_seconds_map failed ({e}); using uniform segment map.",
            )
    segs = build_tempo_segments(score, default_bpm=default_bpm)
    audit = _timebase_audit(score, default_bpm)
    audit["reason"] = audit.get("reason") or "uniform segment map"
    audit.setdefault("warnings", []).extend(audit_fb.get("warnings", []))
    return ql_to_seconds_fn(segs), audit


def load_score_and_note_matrix(
    file_path: Union[str, Path],
    *,
    merge_ties: bool = True,
    pitch_domain: str = "written",
    default_bpm: float = 120.0,
    use_tempo_map: bool = True,
) -> Tuple[Any, List[Dict[str, Any]], TempoAudit]:
    """
    Parse file once; return (music21 score, note_matrix in seconds, tempo_audit).
    """
    path = Path(file_path)
    suf = path.suffix.lower()

    if suf in (".mid", ".midi"):
        nm = load_file_to_note_matrix(
            path,
            merge_ties=False,
            pitch_domain=pitch_domain,
            default_bpm=default_bpm,
        )
        from music21 import converter

        score = converter.parse(str(path))
        audit: TempoAudit = {
            "source": "midi_seconds",
            "tempo_fallback_used": False,
            "n_tempo_segments": 0,
            "reason": None,
            "tempo_model": "stepwise_plateau",
            "warnings": [],
        }
        return score, nm, audit

    from music21 import converter

    score = converter.parse(str(path))
    pre_warnings: TempoAudit = {"warnings": []}
    if pitch_domain == "sounding":
        try:
            score = score.toSoundingPitch(inPlace=False)
        except Exception as e:
            append_warning(
                pre_warnings,
                "sounding_pitch_failed",
                f"toSoundingPitch() failed; using written pitch: {e}",
            )

    notes_data = extract_notes_with_ties(score, merge_ties=merge_ties)
    ql_to_sec, tempo_audit = _ql_map(score, use_tempo_map, default_bpm)
    tempo_audit.setdefault("warnings", []).extend(pre_warnings.get("warnings", []))
    for n in notes_data:
        n["start"] = ql_to_sec(float(n["start"]))
        n["end"] = ql_to_sec(float(n["end"]))
        n["duration"] = float(n["end"]) - float(n["start"])
    nm = note_matrix_from_notes_data(notes_data, time_unit="seconds")
    return score, nm, tempo_audit
