"""
Precise event-rate metrics (canonical units documented in output).

Units:
  - events_per_second: events / second (SI rate)
  - events_per_millisecond: events_per_second / 1000 (average linear density per ms of timeline)
  - events_per_ms_in_window: count / window_ms for sliding windows in milliseconds
  - events_per_beat_in_bar: onsets / notated beats in that measure
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .activity_granularity import activity_rate_per_window, granularity_metrics
from .measures import MeasureInfo, per_bar_event_rates
from .note_types import NoteMatrix
from .temporal_density import TemporalDensityAnalyzer


def _nan_to_none(d: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in d.items():
        if isinstance(v, float) and not np.isfinite(v):
            out[k] = None
        else:
            out[k] = v
    return out


def global_event_rates(note_matrix: NoteMatrix) -> Dict[str, Any]:
    """Global rates with explicit unit definitions."""
    g = granularity_metrics(note_matrix)
    eps = float(g["events_per_sec_global"])
    span_sec = float(g["total_span_sec"])
    span_ms = span_sec * 1000.0
    n = int(g["num_events"])
    eps_raw = float(g["events_per_sec_global_raw"])
    return _nan_to_none({
        "num_events": n,
        "num_events_raw": int(g["num_events_raw"]),
        "sync_fraction": g.get("sync_fraction"),
        "span_sec": span_sec,
        "span_ms": span_ms,
        "events_per_second": eps,
        "events_per_second_raw": eps_raw,
        "events_per_millisecond": eps / 1000.0,
        "mean_ioi_sec": g.get("ioi_mean_sec"),
        "mean_ioi_ms": float(g["ioi_mean_sec"]) * 1000.0 if np.isfinite(g.get("ioi_mean_sec", np.nan)) else None,
        "ioi_cv": g.get("ioi_cv"),
        "ioi_cv_raw": g.get("ioi_cv_raw"),
        "granularity_index": g.get("granularity_index"),
        "granularity_index_raw": g.get("granularity_index_raw"),
        "burstiness": g.get("burstiness"),
        "definition": {
            "num_events": "count of unique fused onsets (coincident within 2 ms merged)",
            "num_events_raw": "count of raw onsets before fusion",
            "sync_fraction": "1 - num_events / num_events_raw (onsets absorbed by fusion)",
            "events_per_second": (
                "unique fused onsets / (t_last - t_first); span-referenced diagnostic; "
                "canonical VD4_s is Mustextu rate_eps"
            ),
            "events_per_second_raw": "raw onsets / (t_last - t_first) on fused span support",
            "events_per_millisecond": "events_per_second / 1000",
            "ioi_cv": "std/mean of IOIs over unique fused onsets",
            "ioi_cv_raw": "std/mean of IOIs over raw onsets (pre-fusion)",
            "granularity_index": "1 / (1 + ioi_cv) on unique fused onsets",
            "granularity_index_raw": "1 / (1 + ioi_cv_raw) on raw onsets",
            "burstiness": (
                "(sigma - mu) / (sigma + mu) of fused-onset counts in fixed 0.5 s windows"
            ),
        },
    })


def rates_by_time_bin(note_matrix: NoteMatrix, bin_sec: float) -> Dict[str, Any]:
    td = TemporalDensityAnalyzer()
    raw = td.run(note_matrix, bin_sec)
    onset = raw["onset_density"]
    eps_bins = (onset / bin_sec).tolist() if bin_sec > 0 else onset.tolist()
    epm_bins = [x / 1000.0 for x in eps_bins]
    return {
        "bin_sec": bin_sec,
        "bin_ms": bin_sec * 1000.0,
        "time_points_sec": raw["time_points"].tolist(),
        "onset_count_per_bin": onset.tolist(),
        "events_per_second_per_bin": eps_bins,
        "events_per_millisecond_per_bin": epm_bins,
        "active_count_per_bin": raw["active_density"].tolist(),
    }


def rates_by_ms_window(
    note_matrix: NoteMatrix,
    window_ms: float = 100.0,
    step_ms: float = 25.0,
) -> Dict[str, Any]:
    """Sliding window: events_per_ms_in_window = count / window_ms."""
    window_sec = window_ms / 1000.0
    step_sec = step_ms / 1000.0
    t_centres, eps, win_sec = activity_rate_per_window(
        note_matrix, window_sec=window_sec, step_sec=step_sec
    )
    win_ms = win_sec * 1000.0
    counts = eps * win_sec
    epm_win = (counts / win_ms).tolist() if win_ms > 0 else []
    return {
        "window_ms": win_ms,
        "step_ms": step_ms,
        "time_points_sec": t_centres.tolist(),
        "events_per_second": eps.tolist(),
        "events_per_millisecond_in_window": epm_win,
        "onset_count_per_window": counts.tolist(),
        "definition": {
            "events_per_millisecond_in_window": "onset_count_in_window / window_ms",
        },
    }


def compute_all_event_rates(
    note_matrix: NoteMatrix,
    *,
    density_intervals: List[float],
    ms_windows: Optional[List[float]] = None,
    measures: Optional[List[MeasureInfo]] = None,
) -> Dict[str, Any]:
    """Full event-rate report: global, bins, ms windows, per bar."""
    ms_windows = ms_windows or [50.0, 100.0, 500.0]
    out: Dict[str, Any] = {
        "global": global_event_rates(note_matrix),
        "by_bin_sec": {str(iv): rates_by_time_bin(note_matrix, iv) for iv in density_intervals},
        "by_ms_window": {str(int(w)): rates_by_ms_window(note_matrix, w) for w in ms_windows},
        "per_bar": per_bar_event_rates(note_matrix, measures),
    }
    if out["per_bar"]:
        mean_bar_eps = float(np.mean([r["events_per_second_in_bar"] for r in out["per_bar"]]))
        out["per_bar_summary"] = {
            "mean_events_per_second_in_bar": mean_bar_eps,
            "mean_events_per_millisecond_in_bar": mean_bar_eps / 1000.0,
            "num_bars": len(out["per_bar"]),
        }
    return out
