"""Activity, IOI, and granularity metrics (v3 core)."""

from typing import Any, Dict, List, Tuple

import numpy as np

from .note_types import NoteMatrix
from .temporal_density import TemporalDensityAnalyzer


def _onset_end(row: Dict[str, Any]) -> Tuple[float, float]:
    onset = float(row.get("onset_sec", row.get("onset_beats", 0)))
    dur = float(row.get("duration_sec", row.get("duration_beats", 0)))
    return onset, onset + dur


def get_onsets_sorted(note_matrix: NoteMatrix) -> np.ndarray:
    if not note_matrix:
        return np.array([])
    onsets = [float(n.get("onset_sec", n.get("onset_beats", 0))) for n in note_matrix]
    return np.sort(onsets)


def inter_onset_intervals(note_matrix: NoteMatrix) -> np.ndarray:
    onsets = get_onsets_sorted(note_matrix)
    if len(onsets) < 2:
        return np.array([])
    return np.diff(onsets)


def activity_rate_per_window(
    note_matrix: NoteMatrix,
    window_sec: float = 1.0,
    step_sec: float | None = None,
) -> Tuple[np.ndarray, np.ndarray, float]:
    if not note_matrix:
        return np.array([]), np.array([]), float(window_sec)
    onsets = get_onsets_sorted(note_matrix)
    t_max = float(max(_onset_end(n)[1] for n in note_matrix))
    if t_max <= 0:
        return np.array([]), np.array([]), float(window_sec)
    window = float(window_sec)
    if t_max < window:
        window = max(t_max * 0.5, 1e-9)
    step = step_sec if step_sec is not None and step_sec > 0 else max(window / 4.0, 1e-9)
    t_centres = np.arange(window / 2.0, t_max - window / 2.0 + 1e-9, step, dtype=float)
    if len(t_centres) == 0:
        t_centres = np.array([t_max / 2.0])
    rates = np.zeros(len(t_centres), dtype=float)
    for i, tc in enumerate(t_centres):
        t0 = tc - window / 2.0
        t1 = tc + window / 2.0
        count = int(np.sum((onsets >= t0) & (onsets < t1)))
        rates[i] = count / window if window > 0 else 0.0
    return t_centres, rates, float(window)


def density_by_bins(note_matrix: NoteMatrix, bin_sec: float) -> Dict[str, Any]:
    td = TemporalDensityAnalyzer(time_unit="seconds")
    raw = td.run(note_matrix, bin_sec)
    return {
        "time_points": raw["time_points"],
        "onset_density": raw["onset_density"],
        "active_density": raw["active_density"],
        "interval": float(raw["interval"]),
    }


def granularity_metrics(note_matrix: NoteMatrix) -> Dict[str, float]:
    onsets = get_onsets_sorted(note_matrix)
    n_events = len(onsets)
    total_span = float(np.ptp(onsets)) if n_events >= 2 else 0.0
    if total_span <= 0:
        total_span = 1.0
    out = {
        "num_events": n_events,
        "total_span_sec": total_span,
        "events_per_sec_global": n_events / total_span if total_span > 0 else 0.0,
        "ioi_mean_sec": np.nan,
        "ioi_std_sec": np.nan,
        "ioi_cv": np.nan,
        "granularity_index": np.nan,
        "burstiness": np.nan,
    }
    iois = inter_onset_intervals(note_matrix)
    if len(iois) == 0:
        return out
    ioi_mean = float(np.mean(iois))
    ioi_std = float(np.std(iois))
    out["ioi_mean_sec"] = ioi_mean
    out["ioi_std_sec"] = ioi_std
    out["ioi_cv"] = (ioi_std / ioi_mean) if ioi_mean > 0 else np.nan
    out["granularity_index"] = 1.0 / (1.0 + out["ioi_cv"]) if np.isfinite(out["ioi_cv"]) else 0.5
    d = density_by_bins(note_matrix, bin_sec=0.5)
    counts = d["onset_density"]
    if len(counts) >= 2:
        mu = float(np.mean(counts))
        sig = float(np.std(counts))
        out["burstiness"] = (sig - mu) / (sig + mu) if (sig + mu) > 0 else 0.0
    return out


def run_activity_granularity(note_matrix: NoteMatrix, intervals: List[float]) -> Dict[str, Any]:
    if not note_matrix:
        return {
            "by_interval": {},
            "granularity": {},
            "ioi_sec": [],
            "activity_rate": {"time_points": [], "events_per_sec": [], "window_sec": 1.0},
        }
    by_interval = {}
    for interval in intervals:
        d = density_by_bins(note_matrix, interval)
        onset = d["onset_density"]
        by_interval[interval] = {
            "time_points": d["time_points"].tolist(),
            "onset_density": onset.tolist(),
            "active_density": d["active_density"].tolist(),
            "events_per_sec_per_bin": (onset / interval).tolist() if interval > 0 else onset.tolist(),
        }
    iois = inter_onset_intervals(note_matrix)
    t_act, rate_act, win_used = activity_rate_per_window(note_matrix, window_sec=1.0, step_sec=0.25)
    return {
        "by_interval": by_interval,
        "primary_interval": min(intervals) if intervals else 0.1,
        "granularity": granularity_metrics(note_matrix),
        "ioi_sec": iois.tolist(),
        "activity_rate": {
            "time_points": t_act.tolist(),
            "events_per_sec": rate_act.tolist(),
            "window_sec": win_used,
        },
        "num_events": len(note_matrix),
    }
