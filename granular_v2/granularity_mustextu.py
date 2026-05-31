"""Bridge score → Mustextu horizontal density."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import MustextuConfig
from .mustextu import compute_horizontal_density_from_onsets
from .onset_extraction import (
    extract_onsets_per_layer_ms_from_score,
    resolve_granularity_window_ms,
)


def analyze_mustextu_from_score(
    score,
    cfg: MustextuConfig,
    *,
    part_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
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
    }
