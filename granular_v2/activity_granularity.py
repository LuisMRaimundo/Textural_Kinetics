"""Activity, IOI, and granularity metrics (v3 core)."""

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .note_types import NoteMatrix
from .temporal_density import TemporalDensityAnalyzer

# VD4 normative reading: granularity is horizontal, computed on unique *fused* onsets.
COINCIDENCE_TOL_SEC = 0.002  # tau = 2 ms (annex VD4 default)
TOL_FRAC_OF_MIN_MEDIAN_IOI = 0.05
BURST_WINDOW_SEC = 0.5       # fixed 0.5 s window for VD4_burst


def effective_coincidence_tol_sec(
    per_layer_onsets: Iterable[Sequence[float]],
    *,
    base_tol_sec: float = COINCIDENCE_TOL_SEC,
    frac: float = TOL_FRAC_OF_MIN_MEDIAN_IOI,
    adaptive: bool = True,
) -> float:
    """min(base, frac × min over layers of the median IOI). Adaptive when min median < 40 ms."""
    if not adaptive:
        return float(base_tol_sec)
    min_median = float("inf")
    base = float(base_tol_sec)
    for onsets in per_layer_onsets:
        arr = np.unique(np.sort(np.asarray(list(onsets), dtype=float)))
        if arr.size < 2:
            continue
        iois = np.diff(arr)
        musical = iois[iois > base]
        use = musical if musical.size else iois
        med = float(np.median(use))
        if np.isfinite(med) and med > 0.0:
            min_median = min(min_median, med)
    if np.isfinite(min_median):
        return max(0.0, min(float(base_tol_sec), float(frac) * min_median))
    return float(base_tol_sec)


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


def burstiness_fano(
    onsets,
    *,
    support: Optional[Tuple[float, float]] = None,
    window_sec: float = BURST_WINDOW_SEC,
) -> float:
    """
    Rate-independent clustering: F = var(counts)/mean(counts); B = (F-1)/(F+1).

    Windows tile [t_start, t_end). A trailing partial window is dropped (its
    events are excluded from this measure only). Requires ≥ 2 full windows and
    mean(counts) > 0; otherwise NaN.
    """
    arr = np.sort(np.asarray(onsets, dtype=float))
    if arr.size == 0:
        return float("nan")
    if support is not None:
        t0, t1 = float(support[0]), float(support[1])
    else:
        t0, t1 = float(arr[0]), float(arr[-1])
    if not np.isfinite(t0) or not np.isfinite(t1) or t1 <= t0:
        return float("nan")
    n_full = int(np.floor((t1 - t0) / float(window_sec)))
    if n_full < 2:
        return float("nan")
    window = float(window_sec)
    starts = t0 + window * np.arange(n_full, dtype=float)
    counts = np.empty(n_full, dtype=float)
    for i, a in enumerate(starts):
        counts[i] = float(np.sum((arr >= a) & (arr < a + window)))
    mu = float(np.mean(counts))
    if mu <= 0.0:
        return float("nan")
    fano = float(np.var(counts)) / mu
    return (fano - 1.0) / (fano + 1.0)


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


def _layer_onsets_for_metrics(note_matrix: NoteMatrix) -> Dict[str, List[float]]:
    from .onset_extraction import onsets_per_layer_from_note_matrix

    layers = onsets_per_layer_from_note_matrix(note_matrix, ignore_grace=False)
    if layers:
        return layers
    raw = get_onsets_sorted(note_matrix)
    if raw.size == 0:
        return {}
    return {"_": [float(t) for t in raw]}


def _grace_audit(note_matrix: NoteMatrix) -> Dict[str, Any]:
    n_grace = 0
    compressed = False
    for n in note_matrix:
        if n.get("is_grace"):
            n_grace += 1
            if n.get("grace_compressed"):
                compressed = True
    return {
        "grace_onsets_included": n_grace,
        "grace_compressed": compressed,
    }


def granularity_metrics(
    note_matrix: NoteMatrix,
    tol_sec: Optional[float] = None,
    support: Optional[Tuple[float, float]] = None,
    *,
    adaptive_tolerance: bool = True,
) -> Dict[str, float]:
    """Horizontal granularity on UNIQUE FUSED onsets (annex VD4). Raw counterparts
    kept as *_raw diagnostics; sync_fraction records onsets absorbed by fusion. The
    canonical VD4_s rate remains the Mustextu rate_eps; events_per_sec_global here is
    a span-referenced diagnostic on the unique series.

    Burstiness is the Fano-factor transform B = (F-1)/(F+1) on full 0.5 s windows
    tiling the supplied support, or [t_first, t_last) of the unique series.
    """
    layers = _layer_onsets_for_metrics(note_matrix)
    pooled: List[float] = [t for times in layers.values() for t in times]
    raw_onsets = np.sort(np.asarray(pooled, dtype=float)) if pooled else np.array([])
    n_raw = int(raw_onsets.size)
    if tol_sec is None:
        tol_sec = effective_coincidence_tol_sec(
            layers.values(),
            adaptive=adaptive_tolerance,
        )
    tol_sec = float(tol_sec)
    merged, _ = merge_coincident_onsets(raw_onsets, tol_sec)
    n_unique = int(merged.size)
    total_span = float(np.ptp(merged)) if n_unique >= 2 else 0.0
    support_span = total_span if total_span > 0 else 1.0
    grace = _grace_audit(note_matrix)
    out = {
        "num_events": n_unique,
        "num_events_raw": n_raw,
        "sync_fraction": (1.0 - n_unique / n_raw) if n_raw > 0 else 0.0,
        "total_span_sec": total_span,
        "events_per_sec_global": n_unique / support_span,
        "events_per_sec_global_raw": n_raw / support_span,
        "ioi_mean_sec": np.nan, "ioi_std_sec": np.nan,
        "ioi_cv": np.nan,
        "ioi_cv_raw": np.nan,
        "burstiness": np.nan,
        "coincidence_tol_sec_effective": tol_sec,
        "grace_onsets_included": grace["grace_onsets_included"],
        "grace_compressed": grace["grace_compressed"],
    }
    raw_iois = np.diff(raw_onsets) if n_raw >= 2 else np.array([])
    if raw_iois.size > 0:
        rmean = float(np.mean(raw_iois)); rstd = float(np.std(raw_iois))
        out["ioi_cv_raw"] = (rstd / rmean) if rmean > 0 else np.nan
    iois = np.diff(merged) if n_unique >= 2 else np.array([])
    if iois.size > 0:
        imean = float(np.mean(iois)); istd = float(np.std(iois))
        out["ioi_mean_sec"] = imean; out["ioi_std_sec"] = istd
        out["ioi_cv"] = (istd / imean) if imean > 0 else np.nan
    out["burstiness"] = burstiness_fano(merged, support=support)
    return out


def run_activity_granularity(
    note_matrix: NoteMatrix,
    intervals: List[float],
    support: Optional[Tuple[float, float]] = None,
) -> Dict[str, Any]:
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
    gran = granularity_metrics(note_matrix, support=support)
    gran_out = {}
    for k, v in gran.items():
        if isinstance(v, float) and not np.isfinite(v):
            gran_out[k] = None
        else:
            gran_out[k] = v
    return {
        "by_interval": by_interval,
        "primary_interval": min(intervals) if intervals else 0.1,
        "granularity": gran_out,
        "ioi_sec": iois.tolist(),
        "activity_rate": {
            "time_points": t_act.tolist(),
            "events_per_sec": rate_act.tolist(),
            "window_sec": win_used,
        },
        "num_events": len(note_matrix),
    }
