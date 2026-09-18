"""Bridge score → Mustextu horizontal density."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .config import MustextuConfig
from .mustextu import compute_horizontal_density_from_onsets
from .onset_extraction import (
    extract_onsets_per_layer_ms_from_score,
    note_offset_sec,
    onsets_per_layer_ms_from_note_matrix,
    resolve_granularity_window_ms,
)


def analyze_mustextu_from_score(
    score,
    cfg: MustextuConfig,
    *,
    part_filter: Optional[List[str]] = None,
    note_matrix: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if note_matrix:
        onsets_per_layer = onsets_per_layer_ms_from_note_matrix(
            note_matrix,
            ignore_grace=cfg.ignore_grace,
            part_filter=part_filter,
        )
        t_end_ms = 0.0
        for n in note_matrix:
            t_end_ms = max(t_end_ms, note_offset_sec(n) * 1000.0)
        from .onset_extraction import build_ql_to_seconds_for_score

        ql_to_seconds, initial_bpm = build_ql_to_seconds_for_score(score, default_bpm=cfg.default_bpm)
        try:
            score_q_end = float(getattr(score, "highestTime", 0.0) or 0.0)
        except Exception:
            score_q_end = 0.0
        score_end_ms = ql_to_seconds(score_q_end) * 1000.0
    else:
        onsets_per_layer, t_end_ms, score_end_ms, initial_bpm = extract_onsets_per_layer_ms_from_score(
            score,
            default_bpm=cfg.default_bpm,
            part_filter=part_filter,
            ignore_grace=cfg.ignore_grace,
        )
    window_ms = resolve_granularity_window_ms(cfg.window_ms, t_end_ms, score_end_ms)
    result = compute_horizontal_density_from_onsets(
        onsets_per_layer,
        window_ms=window_ms,
        iei_timbre_ms=cfg.iei_timbre_ms,
        coincidence_ms=cfg.coincidence_ms,
        adaptive_tolerance=cfg.adaptive_tolerance,
        tol_frac_of_min_period=cfg.tol_frac_of_min_period,
        align_window_to_beat=cfg.align_window_to_beat,
        bpm_for_alignment=initial_bpm if cfg.align_window_to_beat else None,
        gran_max_eps=cfg.gran_max_eps,
    )
    comp = result.get("composite", {})
    rate_eps = float(comp.get("rate_eps", 0.0))
    return {
        "mustextu": result,
        "initial_bpm": initial_bpm,
        "window_ms": window_ms,
        "rate_events_per_second": rate_eps,
        "rate_events_per_millisecond": rate_eps / 1000.0,
        "rate_events_per_second_raw": float(comp.get("rate_eps_raw", rate_eps)),
        "synchrony_fraction": float(comp.get("synchrony_fraction", 0.0)),
        "granularity_score": float(comp.get("granularity_score", 0.0)),
        "coincidence_ms_effective": comp.get("coincidence_ms_effective"),
        "coincidence_tol_sec_effective": (
            float(comp["coincidence_ms_effective"]) / 1000.0
            if comp.get("coincidence_ms_effective") is not None
            else None
        ),
    }
