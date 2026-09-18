"""Onset extraction per layer — derived from the tie-merged note matrix."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .note_extraction import _is_grace, _part_label, extract_notes_with_ties
from .timebase import build_tempo_segments, ql_to_seconds_fn

# Nominal spacing for grace-note attacks (VD4 only). Configurable.
GRACE_NOMINAL_SPACING_SEC = 0.05


def build_ql_to_seconds_for_score(score, default_bpm: float = 120.0) -> Tuple[Callable[[float], float], float]:
    segs = build_tempo_segments(score, default_bpm=default_bpm)
    ql_to_seconds = ql_to_seconds_fn(segs)
    initial_bpm = float(segs[0].bpm) if segs else float(default_bpm)
    return ql_to_seconds, initial_bpm


def _part_key(note: Dict[str, Any]) -> str:
    part = note.get("part")
    if part is None or str(part).strip() == "":
        return "Unknown"
    return str(part).strip()


def _onset_sec(note: Dict[str, Any]) -> float:
    return float(note.get("onset_sec", note.get("start", note.get("onset_beats", 0.0))) or 0.0)


def note_offset_sec(note: Dict[str, Any]) -> float:
    if "offset_sec" in note and note["offset_sec"] is not None:
        return float(note["offset_sec"])
    onset = _onset_sec(note)
    dur = float(note.get("duration_sec", note.get("duration", note.get("duration_beats", 0.0))) or 0.0)
    if "end" in note and note["end"] is not None:
        try:
            return float(note["end"])
        except (TypeError, ValueError):
            pass
    return onset + dur


def assign_grace_nominal_onsets(
    note_matrix: List[Dict[str, Any]],
    *,
    spacing_sec: float = GRACE_NOMINAL_SPACING_SEC,
    coincidence_tol_sec: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Place grace-note attacks on a nominal grid before their principal note.

    k grace notes before a principal at t go at t-k*s, …, t-s. If the gap g to
    the previous unique onset of the same layer is smaller than (k+1)*s,
    s = g/(k+1). If s cannot stay above the coincidence tolerance, events are
    kept and the group is flagged ``grace_compressed``.
    """
    from .activity_granularity import COINCIDENCE_TOL_SEC

    tol = float(COINCIDENCE_TOL_SEC if coincidence_tol_sec is None else coincidence_tol_sec)
    n_grace = 0
    n_compressed_groups = 0
    any_compressed = False

    by_part: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for note in note_matrix:
        by_part[_part_key(note)].append(note)

    for notes in by_part.values():
        notes.sort(
            key=lambda n: (
                _onset_sec(n),
                0 if n.get("is_grace") else 1,
                int(n.get("pitch", 0) or 0),
            )
        )
        last_unique: Optional[float] = None
        i = 0
        while i < len(notes):
            if notes[i].get("is_grace") and not notes[i].get("grace_onset_assigned"):
                graces: List[Dict[str, Any]] = []
                while i < len(notes) and notes[i].get("is_grace"):
                    if not notes[i].get("grace_onset_assigned"):
                        graces.append(notes[i])
                    i += 1
                if not graces:
                    continue
                principal_t = (
                    _onset_sec(notes[i])
                    if i < len(notes) and not notes[i].get("is_grace")
                    else _onset_sec(graces[-1])
                )
                k = len(graces)
                s = float(spacing_sec)
                compressed = False
                if last_unique is not None:
                    gap = principal_t - last_unique
                    if gap < (k + 1) * s:
                        s = gap / (k + 1) if (k + 1) > 0 else s
                    if s <= tol:
                        compressed = True
                for j, grace in enumerate(graces):
                    grace["onset_sec"] = principal_t - (k - j) * s
                    if "start" in grace:
                        grace["start"] = grace["onset_sec"]
                    grace["grace_compressed"] = compressed
                    grace["grace_onset_assigned"] = True
                    n_grace += 1
                if compressed:
                    n_compressed_groups += 1
                    any_compressed = True
                last_unique = principal_t - s if k else last_unique
            else:
                t = _onset_sec(notes[i])
                last_unique = t
                i += 1

    return {
        "grace_onsets_included": n_grace,
        "grace_compressed_groups": n_compressed_groups,
        "grace_compressed": any_compressed,
    }


def onsets_per_layer_from_note_matrix(
    note_matrix: Sequence[Dict[str, Any]],
    *,
    ignore_grace: bool = False,
    part_filter: Optional[Iterable[str]] = None,
) -> Dict[str, List[float]]:
    """Unique attack times per layer from the tie-merged (grace-placed) note matrix."""
    selected: Optional[Set[str]] = {x.strip() for x in part_filter} if part_filter else None
    by_part: Dict[str, Set[float]] = defaultdict(set)
    for note in note_matrix:
        if ignore_grace and note.get("is_grace"):
            continue
        label = _part_key(note)
        if selected and label not in selected:
            continue
        by_part[label].add(_onset_sec(note))
    return {label: sorted(times) for label, times in by_part.items() if times}


def onsets_per_layer_ms_from_note_matrix(
    note_matrix: Sequence[Dict[str, Any]],
    *,
    ignore_grace: bool = False,
    part_filter: Optional[Iterable[str]] = None,
) -> Dict[str, List[float]]:
    layers = onsets_per_layer_from_note_matrix(
        note_matrix, ignore_grace=ignore_grace, part_filter=part_filter
    )
    return {label: [t * 1000.0 for t in times] for label, times in layers.items()}


def _notes_data_to_matrix_seconds(notes_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from .input_layer import note_matrix_from_notes_data

    return note_matrix_from_notes_data(notes_data, time_unit="seconds")


def extract_onsets_per_layer_ms_from_score(
    score,
    *,
    default_bpm: float = 120.0,
    part_filter: Optional[List[str]] = None,
    ignore_grace: bool = False,
) -> Tuple[Dict[str, List[float]], float, float, float]:
    """
    Per-layer unique onsets (ms) from the same tie-merged note matrix used for
    regularity metrics. Grace notes are attacks by default and receive nominal
    onset times.
    """
    ql_to_seconds, initial_bpm = build_ql_to_seconds_for_score(score, default_bpm=default_bpm)
    try:
        score_q_end = float(getattr(score, "highestTime", 0.0) or 0.0)
    except Exception:
        score_q_end = 0.0
    score_end_ms = ql_to_seconds(score_q_end) * 1000.0

    notes_data = extract_notes_with_ties(score, merge_ties=True)
    for n in notes_data:
        n["start"] = ql_to_seconds(float(n["start"]))
        n["end"] = ql_to_seconds(float(n["end"]))
        n["duration"] = float(n["end"]) - float(n["start"])
    note_matrix = _notes_data_to_matrix_seconds(notes_data)
    assign_grace_nominal_onsets(note_matrix)

    onsets_per_layer = onsets_per_layer_ms_from_note_matrix(
        note_matrix, ignore_grace=ignore_grace, part_filter=part_filter
    )
    t_end_ms = 0.0
    for n in note_matrix:
        t_end_ms = max(t_end_ms, note_offset_sec(n) * 1000.0)

    return onsets_per_layer, t_end_ms, score_end_ms, initial_bpm


def resolve_granularity_window_ms(
    window_ms: Optional[float],
    t_end_ms: float,
    score_end_ms: float,
    *,
    clamp_ratio: float = 1.25,
) -> float:
    if window_ms is not None and window_ms > 0:
        return float(window_ms)
    last_event_ms = float(t_end_ms or 0.0)
    score_ms = float(score_end_ms or 0.0)
    if last_event_ms > 0 and score_ms > 0:
        if score_ms > last_event_ms * clamp_ratio:
            return last_event_ms
        return max(score_ms, last_event_ms)
    if last_event_ms > 0:
        return last_event_ms
    if score_ms > 0:
        return score_ms
    return 10000.0


def score_support_sec(score, default_bpm: float = 120.0) -> Optional[Tuple[float, float]]:
    """Half-open score support [0, t_end) from highestTime, or None if unknown."""
    try:
        ql_to_seconds, _ = build_ql_to_seconds_for_score(score, default_bpm=default_bpm)
        q_end = float(getattr(score, "highestTime", 0.0) or 0.0)
        t_end = ql_to_seconds(q_end)
    except Exception:
        return None
    if t_end <= 0.0:
        return None
    return (0.0, t_end)
