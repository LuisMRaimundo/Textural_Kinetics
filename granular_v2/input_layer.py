# horizontal_density_v3/input_layer.py  (MusicXML/MIDI -> note matrix)
"""MusicXML / MIDI → unified note matrix. Tie-aware extraction + tempo map (v2 merge)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List

from .note_extraction import extract_notes_with_ties
from .offsets import global_ql
from .timebase import build_tempo_segments, convert_notes_times_inplace, ql_to_seconds_fn

log = logging.getLogger(__name__)


def _get_start_end(note_data: Dict[str, Any]) -> tuple:
    start = float(note_data.get("start", note_data.get("time", 0)) or 0)
    end = note_data.get("end")
    if end is not None:
        end = float(end)
    else:
        dur = float(note_data.get("duration", 0) or 0)
        end = start + dur
    return start, end


def note_matrix_from_notes_data(
    notes_data: List[Dict[str, Any]],
    time_unit: str = "seconds",
) -> List[Dict[str, Any]]:
    """
    Build a unified note matrix from notes_data.

    Each row: onset_sec, duration_sec, channel, pitch, velocity, [part].
    """
    nm = []
    for i, n in enumerate(notes_data):
        start, end = _get_start_end(n)
        duration = end - start
        pitch = int(n.get("pitch", 60))
        velocity = int(n.get("velocity", 80))
        part = n.get("part", n.get("channel", ""))
        if "channel" in n and isinstance(n["channel"], int):
            ch = n["channel"] % 16
        else:
            ch = hash(part) % 16 if part else 0

        row = {
            "onset_sec": start,
            "duration_sec": duration,
            "channel": ch,
            "pitch": pitch,
            "velocity": velocity,
            "part": part,
            "index": i,
        }
        if time_unit == "quarterLength":
            row["onset_beats"] = n.get("onset_beats", start)
            row["duration_beats"] = n.get("duration_beats", duration)
        nm.append(row)
    return nm


def _build_ql_to_seconds(
    score,
    use_tempo_map: bool,
    default_bpm: float,
) -> Callable[[float], float]:
    if use_tempo_map:
        try:
            segs = build_tempo_segments(score, default_bpm=default_bpm)
            return ql_to_seconds_fn(segs)
        except Exception as e:
            log.warning("timebase segments failed (%s); trying build_seconds_map.", e)
        try:
            from .util_tempo import build_seconds_map

            return build_seconds_map(score)
        except Exception as e:
            log.warning("build_seconds_map failed (%s); using uniform BPM.", e)
    try:
        segs = build_tempo_segments(score, default_bpm=default_bpm)
        return ql_to_seconds_fn(segs)
    except Exception:
        factor = 60.0 / max(default_bpm, 1e-6)

        def uniform_ql(q: float) -> float:
            return float(q) * factor

        return uniform_ql


def load_musicxml_to_note_matrix(
    file_path: str | Path,
    time_unit: str = "seconds",
    expand_repeats: bool = False,
    use_tempo_map: bool = True,
    return_metadata: bool = False,
    merge_ties: bool = True,
    pitch_domain: str = "written",
    default_bpm: float = 120.0,
):
    """
    Load MusicXML → note matrix.

    v2: tie-aware extraction (Granularidade), tempo map (util_tempo + fallback timebase),
    optional sounding pitch (transposing instruments).
    """
    path = Path(file_path)
    if not path.exists():
        log.error("File not found: %s", path)
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() not in (".xml", ".musicxml", ".mxl"):
        raise ValueError("Unsupported format. Use MusicXML (.xml, .musicxml, .mxl).")

    try:
        from music21 import converter
    except ImportError as e:
        raise ImportError("music21 is required. pip install music21") from e

    try:
        score = converter.parse(str(path))
    except Exception as e:
        log.exception("Failed to parse MusicXML: %s", path)
        raise ValueError(f"Invalid or unsupported MusicXML. {e!s}") from e

    if pitch_domain == "sounding":
        try:
            score = score.toSoundingPitch(inPlace=False)
        except Exception as e:
            log.warning("toSoundingPitch() failed; keeping written pitch: %s", e, exc_info=True)

    has_repeats = False
    expansion_applied = False
    if return_metadata:
        from .util_tempo import score_has_repeats

        has_repeats = score_has_repeats(score)

    if expand_repeats:
        from music21.stream import Measure

        n_before = len(score.parts[0].getElementsByClass(Measure)) if score.parts else 0
        from .util_tempo import expand_repeats_if_requested

        score = expand_repeats_if_requested(score, True)
        n_after = len(score.parts[0].getElementsByClass(Measure)) if score.parts else 0
        expansion_applied = n_after > n_before

    notes_data = extract_notes_with_ties(score, merge_ties=merge_ties)

    if time_unit == "seconds":
        ql_to_sec = _build_ql_to_seconds(score, use_tempo_map, default_bpm)
        convert_notes_times_inplace(notes_data, ql_to_sec)

    nm = note_matrix_from_notes_data(notes_data, time_unit=time_unit)
    if return_metadata:
        return nm, {
            "has_repeats": has_repeats,
            "expansion_applied": expansion_applied,
            "merge_ties": merge_ties,
            "pitch_domain": pitch_domain,
        }
    return nm


def _midi_onset_duration_sec(elem, score, part) -> tuple[float, float]:
    """Prefer music21 seconds; fallback to score-global QL × 0.5 (120 BPM assumption)."""
    try:
        return float(elem.getOffsetInSeconds()), float(elem.seconds)
    except Exception:
        q = global_ql(elem, score, part)
        dur_q = float(elem.duration.quarterLength) if elem.duration else 0.0
        log.warning(
            "MIDI element missing getOffsetInSeconds; using global QL offset (%.3f).",
            q,
        )
        return q * 0.5, dur_q * 0.5


def load_midi_to_note_matrix(
    file_path: str | Path,
    time_unit: str = "seconds",
) -> List[Dict[str, Any]]:
    """Load MIDI → note matrix (same schema). MIDI path unchanged from v1."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() not in (".mid", ".midi"):
        raise ValueError("Unsupported format. Use MIDI (.mid, .midi).")

    from music21 import converter

    try:
        score = converter.parse(str(path))
    except Exception as e:
        raise ValueError(f"Invalid MIDI. {e!s}") from e

    notes_data = []
    if hasattr(score, "parts") and score.parts:
        for part in score.parts:
            part_name = part.partName or part.id or ""
            for elem in part.recurse().notesAndRests:
                if elem.isNote:
                    n = elem
                    onset_sec, dur_sec = _midi_onset_duration_sec(n, score, part)
                    notes_data.append({
                        "start": onset_sec,
                        "end": onset_sec + dur_sec,
                        "duration": dur_sec,
                        "pitch": n.pitch.midi,
                        "velocity": getattr(n.volume, "velocity", 80) or 80,
                        "part": part_name,
                        "channel": getattr(n, "activeSite", None) and getattr(n.activeSite, "midiChannel", 0) or 0,
                    })
                elif elem.isChord:
                    onset_sec, dur_sec = _midi_onset_duration_sec(elem, score, part)
                    for p in elem.pitches:
                        notes_data.append({
                            "start": onset_sec,
                            "end": onset_sec + dur_sec,
                            "duration": dur_sec,
                            "pitch": p.midi,
                            "velocity": getattr(elem.volume, "velocity", 80) or 80,
                            "part": part_name,
                            "channel": 0,
                        })
    else:
        flat = score.flat if hasattr(score, "flat") else score
        for elem in flat.notesAndRests:
            if elem.isNote:
                n = elem
                onset_sec, dur_sec = _midi_onset_duration_sec(n, score, None)
                notes_data.append({
                    "start": onset_sec,
                    "end": onset_sec + dur_sec,
                    "duration": dur_sec,
                    "pitch": n.pitch.midi,
                    "velocity": getattr(n.volume, "velocity", 80) or 80,
                    "part": "",
                    "channel": 0,
                })
            elif elem.isChord:
                onset_sec, dur_sec = _midi_onset_duration_sec(elem, score, None)
                for p in elem.pitches:
                    notes_data.append({
                        "start": onset_sec,
                        "end": onset_sec + dur_sec,
                        "duration": dur_sec,
                        "pitch": p.midi,
                        "velocity": getattr(elem.volume, "velocity", 80) or 80,
                        "part": "",
                        "channel": 0,
                    })

    return note_matrix_from_notes_data(notes_data, time_unit=time_unit)


def load_file_to_note_matrix(
    file_path: str | Path,
    time_unit: str = "seconds",
    expand_repeats: bool = False,
    use_tempo_map: bool = True,
    return_metadata: bool = False,
    merge_ties: bool = True,
    pitch_domain: str = "written",
    default_bpm: float = 120.0,
):
    path = Path(file_path)
    suf = path.suffix.lower()
    if suf in (".xml", ".musicxml", ".mxl"):
        return load_musicxml_to_note_matrix(
            path,
            time_unit=time_unit,
            expand_repeats=expand_repeats,
            use_tempo_map=use_tempo_map,
            return_metadata=return_metadata,
            merge_ties=merge_ties,
            pitch_domain=pitch_domain,
            default_bpm=default_bpm,
        )
    if suf in (".mid", ".midi"):
        matrix = load_midi_to_note_matrix(path, time_unit=time_unit)
        return (matrix, {}) if return_metadata else matrix
    raise ValueError("Unsupported file format. Use MusicXML or MIDI.")
