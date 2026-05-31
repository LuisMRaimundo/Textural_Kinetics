"""Onset extraction per layer (ms) — canonical timebase for Mustextu."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Set, Tuple

from music21 import stream as m21stream

from .offsets import global_ql
from .timebase import build_tempo_segments, ql_to_seconds_fn


def _part_label(part) -> str:
    name = part.partName or ""
    if not name:
        ins = part.getInstrument(returnDefault=False)
        if ins and getattr(ins, "instrumentName", None):
            name = ins.instrumentName
    return name or (part.id or "Part")


def _is_grace(el) -> bool:
    try:
        if getattr(el, "quarterLength", None) == 0:
            return True
        d = getattr(el, "duration", None)
        return bool(getattr(d, "isGrace", False))
    except Exception:
        return False


def build_ql_to_seconds_for_score(score, default_bpm: float = 120.0) -> Tuple[Callable[[float], float], float]:
    segs = build_tempo_segments(score, default_bpm=default_bpm)
    ql_to_seconds = ql_to_seconds_fn(segs)
    initial_bpm = float(segs[0].bpm) if segs else float(default_bpm)
    return ql_to_seconds, initial_bpm


def extract_onsets_per_layer_ms_from_score(
    score,
    *,
    default_bpm: float = 120.0,
    part_filter: Optional[List[str]] = None,
    ignore_grace: bool = True,
) -> Tuple[Dict[str, List[float]], float, float, float]:
    ql_to_seconds, initial_bpm = build_ql_to_seconds_for_score(score, default_bpm=default_bpm)
    try:
        score_q_end = float(getattr(score, "highestTime", 0.0) or 0.0)
    except Exception:
        score_q_end = 0.0
    score_end_ms = ql_to_seconds(score_q_end) * 1000.0

    selected: Optional[Set[str]] = {x.strip() for x in part_filter} if part_filter else None
    onsets_per_layer: Dict[str, List[float]] = {}
    t_end_ms = 0.0

    parts = list(getattr(score, "parts", [])) or list(score.getElementsByClass(m21stream.Part))
    for p in parts:
        label = _part_label(p)
        if selected and label not in selected:
            continue
        try:
            flat_part = p.flatten()
        except Exception:
            flat_part = getattr(p, "flat", p)
        times: List[float] = []
        for el in flat_part.notesAndRests:
            if getattr(el, "isRest", False):
                continue
            if ignore_grace and _is_grace(el):
                continue
            q0 = global_ql(el, score, p)
            t0_ms = ql_to_seconds(q0) * 1000.0
            times.append(t0_ms)
            q1 = q0 + float(getattr(el, "quarterLength", 0.0) or 0.0)
            t1_ms = ql_to_seconds(q1) * 1000.0
            if t1_ms > t_end_ms:
                t_end_ms = t1_ms
        if times:
            onsets_per_layer[label] = sorted(times)

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
