"""Activity, IOI, and granularity metrics (v3 core)."""

from typing import Any, Dict, List, Tuple

import numpy as np

from .note_types import NoteMatrix
from .temporal_density import TemporalDensityAnalyzer

# VD4 normative reading: granularity is horizontal, computed on unique *fused* onsets.
COINCIDENCE_TOL_SEC = 0.002  # tau = 2 ms (annex VD4 default)
BURST_WINDOW_SEC = 0.5       # fixed 0.5 s window for VD4_burst


def merge_coincident_onsets(onsets, tol_sec=COINCIDENCE_TOL_SEC):
    """Fuse onsets within tol_sec of the GROUP ANCHOR (first onset of the group, not
    the previous onset, to avoid transitive chaining). Returns (merged_times, multiplicities)."""
    arr = np.sort(np.asarray(onsets, dtype=float))
    if arr.size == 0:
        return np.array([], dtype=float), np.array([], dtype=int)
    merged, mult = [], []
    group = [float(arr[0])]; anchor = float(arr[0])
    for t in arr[1:]:
        t = float(t)
        if (t - anchor) <= tol_sec:
            group.append(t)
        else:
            merged.append(sum(group)/len(group)); mult.append(len(group))
            group = [t]; anchor = t
    merged.append(sum(group)/len(group)); mult.append(len(group))
    return np.array(merged, dtype=float), np.array(mult, dtype=int)


def unique_inter_onset_intervals(note_matrix, tol_sec=COINCIDENCE_TOL_SEC):
    """IOIs over unique fused onsets (no zero IOIs from vertical simultaneities)."""
    merged, _ = merge_coincident_onsets(get_onsets_sorted(note_matrix), tol_sec)
    if merged.size < 2:
        return np.array([])
    return np.diff(merged)


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


def granularity_metrics(note_matrix: NoteMatrix, tol_sec: float = COINCIDENCE_TOL_SEC) -> Dict[str, float]:
    """Horizontal granularity on UNIQUE FUSED onsets (annex VD4). Raw counterparts
    kept as *_raw diagnostics; sync_fraction records onsets absorbed by fusion. The
    canonical VD4_s rate remains the Mustextu rate_eps; events_per_sec_global here is
    a span-referenced diagnostic on the unique series."""
    raw_onsets = get_onsets_sorted(note_matrix)
    n_raw = int(raw_onsets.size)
    merged, _ = merge_coincident_onsets(raw_onsets, tol_sec)
    n_unique = int(merged.size)
    total_span = float(np.ptp(merged)) if n_unique >= 2 else 0.0
    support = total_span if total_span > 0 else 1.0
    out = {
        "num_events": n_unique,
        "num_events_raw": n_raw,
        "sync_fraction": (1.0 - n_unique / n_raw) if n_raw > 0 else 0.0,
        "total_span_sec": total_span,
        "events_per_sec_global": n_unique / support,
        "events_per_sec_global_raw": n_raw / support,
        "ioi_mean_sec": np.nan, "ioi_std_sec": np.nan,
        "ioi_cv": np.nan, "granularity_index": np.nan,
        "ioi_cv_raw": np.nan, "granularity_index_raw": np.nan,
        "burstiness": np.nan,
    }
    raw_iois = np.diff(raw_onsets) if n_raw >= 2 else np.array([])
    if raw_iois.size > 0:
        rmean = float(np.mean(raw_iois)); rstd = float(np.std(raw_iois))
        out["ioi_cv_raw"] = (rstd / rmean) if rmean > 0 else np.nan
        out["granularity_index_raw"] = (1.0/(1.0+out["ioi_cv_raw"])
                                        if np.isfinite(out["ioi_cv_raw"]) else 0.5)
    iois = np.diff(merged) if n_unique >= 2 else np.array([])
    if iois.size == 0:
        return out
    imean = float(np.mean(iois)); istd = float(np.std(iois))
    out["ioi_mean_sec"] = imean; out["ioi_std_sec"] = istd
    out["ioi_cv"] = (istd / imean) if imean > 0 else np.nan
    out["granularity_index"] = (1.0/(1.0+out["ioi_cv"])
                                if np.isfinite(out["ioi_cv"]) else 0.5)
    if total_span > 0:
        n_bins = max(1, int(np.ceil(total_span / BURST_WINDOW_SEC)))
        edges = float(merged.min()) + BURST_WINDOW_SEC * np.arange(n_bins + 1)
        edges[-1] = max(edges[-1], float(merged.max()) + 1e-9)
        counts, _ = np.histogram(merged, bins=edges)
        if counts.size >= 2:
            mu = float(np.mean(counts)); sig = float(np.std(counts))
            out["burstiness"] = (sig - mu)/(sig + mu) if (sig + mu) > 0 else 0.0
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
