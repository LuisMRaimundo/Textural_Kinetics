"""Compare tempo→seconds implementations (timebase vs util_tempo)."""

from __future__ import annotations

from typing import List, Tuple

from .timebase import build_tempo_segments, ql_to_seconds_fn
from .util_tempo import build_seconds_map


def compare_ql_maps(
    score,
    default_bpm: float = 120.0,
    *,
    sample_ql: List[float] | None = None,
    atol: float = 0.05,
) -> Tuple[bool, List[Tuple[float, float, float, float]]]:
    """
    Returns (all_close, rows) where each row is (ql, sec_timebase, sec_util, delta).
    """
    fn_seg = ql_to_seconds_fn(build_tempo_segments(score, default_bpm=default_bpm))
    fn_util = build_seconds_map(score)

    highest = float(getattr(score, "highestTime", 0.0) or 0.0)
    if sample_ql is None:
        sample_ql = [0.0, 0.5, 1.0, 2.0, 4.0, max(highest * 0.25, 0.0), max(highest * 0.5, 0.0), highest]
    sample_ql = sorted({max(0.0, min(float(q), highest)) for q in sample_ql})

    rows = []
    ok = True
    for ql in sample_ql:
        a = float(fn_seg(ql))
        b = float(fn_util(ql))
        d = abs(a - b)
        if d > atol:
            ok = False
        rows.append((ql, a, b, d))
    return ok, rows
