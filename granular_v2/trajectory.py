"""
VD10 — Registral trajectory (velocidade de deslocação registral).

This module measures how a user-defined textural block displaces in register over
time. It is a **separate dimension** from granularity (event rate over time):

- **Granularity** counts how many symbolic events occur per unit time.
- **VD10** measures where the registral band of a block goes and how fast its centre
  and width change, in semitones per second.

Never conflate event-rate density with registral displacement. A passage may be
granular (many events) yet registral static (net displacement ≈ 0), or sparse yet
ascending rapidly.

Conceptual core — trajectory speed
----------------------------------
The headline **net speed** is ``net_displacement / total_time`` (centre[end] −
centre[start] over elapsed seconds). It is **never** ``total_path / total_time``.
A block that rises and returns to its starting register yields net ≈ 0; that is
correct. ``total_path`` and ``inflections`` are descriptive oscillation metrics,
not substitutes for net speed.

Robust vs sampling-dependent descriptors
---------------------------------------
**Robust** (invariant to how many picks lie between endpoints; thesis interpretation):

- ``net_speed``, ``net_displacement``, ``straightness``, ``total_path``, ``inflections``

**Sampling-dependent** (segment quotients ``Δcentre/Δt``; explode when picks are
very close in time):

- ``mean_speed``, ``max_speed``, ``median_speed``, per-segment ``speed_centre``

Always inspect ``segments[].dt_s`` before citing ``max_speed``. A tiny ``dt_s`` can
yield thousands of st/s without any musically plausible registral gesture.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, TypedDict

DEFAULT_EPS = 0.01
DEFAULT_TIME_TOL_S = 0.001
DEFAULT_MIN_DT_RECOMMENDED_S = 0.1


class TrajectoryInput(TypedDict):
    time_s: float
    low: float
    high: float


class TrajectorySample(TypedDict):
    time_s: float
    low: int
    high: int
    centre: float
    width: float


class TrajectorySegment(TypedDict):
    time_from_s: float
    time_to_s: float
    dt_s: float
    speed_centre: float
    speed_width: float


class TrajectoryLabels(TypedDict):
    direction: str
    band_behaviour: str
    shape_hint: str


class TrajectoryAggregates(TypedDict):
    net_displacement: float
    total_path: float
    straightness: float
    inflections: int
    mean_speed: float
    median_speed: float
    max_speed: float
    net_speed: float
    total_time_s: float
    min_segment_dt_s: float


class TrajectoryError(ValueError):
    """Invalid VD10 sample series or non-monotonic time."""


class TrajectoryCalibrationError(TrajectoryError):
    """Invalid axis calibration for image-based VD10 picking."""


def snap_semitone(pitch: float) -> int:
    """Round to nearest integer MIDI pitch (semitone resolution)."""
    return int(max(0, min(127, round(float(pitch)))))


def normalize_sample(time_s: float, low: float, high: float) -> TrajectorySample:
    """
    Build one VD10 sample with integer semitone bounds.

    centre = (low + high) / 2 ; width = high − low (low ≤ high).
    """
    lo = snap_semitone(low)
    hi = snap_semitone(high)
    if lo > hi:
        lo, hi = hi, lo
    return {
        "time_s": float(time_s),
        "low": lo,
        "high": hi,
        "centre": (lo + hi) / 2.0,
        "width": float(hi - lo),
    }


def normalize_samples(raw: Sequence[Mapping[str, float]]) -> List[TrajectorySample]:
    """Sort by time and normalize each pick to semitone bounds."""
    items = [
        normalize_sample(float(s["time_s"]), float(s["low"]), float(s["high"]))
        for s in raw
    ]
    items.sort(key=lambda s: s["time_s"])
    return items


def _centre_deltas(samples: Sequence[TrajectorySample]) -> List[float]:
    return [samples[i + 1]["centre"] - samples[i]["centre"] for i in range(len(samples) - 1)]


def _count_inflections(deltas: Sequence[float], eps: float) -> int:
    signs: List[int] = []
    for d in deltas:
        if d > eps:
            signs.append(1)
        elif d < -eps:
            signs.append(-1)
    if len(signs) < 2:
        return 0
    return sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])


def _label_direction(net_displacement: float, eps: float) -> str:
    if net_displacement > eps:
        return "ascending"
    if net_displacement < -eps:
        return "descending"
    return "static"


def _label_band_behaviour(width_first: float, width_last: float, eps: float) -> str:
    delta = width_last - width_first
    if delta > eps:
        return "diverging"
    if delta < -eps:
        return "converging"
    return "stable width"


def _label_shape_hint(straightness: float) -> str:
    if straightness > 0.8:
        return "unidirectional"
    if straightness < 0.4:
        return "undulating"
    return "mixed"


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _sampling_warnings(
    segments: Sequence[TrajectorySegment],
    *,
    min_dt_recommended_s: float = DEFAULT_MIN_DT_RECOMMENDED_S,
) -> List[Dict[str, Any]]:
    warnings: List[Dict[str, Any]] = []
    for i, seg in enumerate(segments):
        dt = float(seg["dt_s"])
        if dt >= min_dt_recommended_s:
            continue
        speed = float(seg["speed_centre"])
        warnings.append(
            {
                "code": "short_segment_dt",
                "segment_index": i,
                "dt_s": dt,
                "speed_centre": speed,
                "abs_speed_centre": abs(speed),
                "time_from_s": float(seg["time_from_s"]),
                "time_to_s": float(seg["time_to_s"]),
                "message": (
                    f"Segment {i}: dt={dt:.4f}s → |speed_centre|={abs(speed):.1f} st/s. "
                    "Very short Δt inflates segment speed; inspect before citing max/mean."
                ),
            }
        )
    return warnings


def compute_vd10(
    raw_samples: Sequence[Mapping[str, float]],
    *,
    eps: float = DEFAULT_EPS,
) -> Dict[str, Any]:
    """
    Compute VD10 registral trajectory from user picks.

    Parameters
    ----------
    raw_samples
        Sequence of dicts with keys ``time_s``, ``low``, ``high`` (semitones).
    eps
        Tolerance for static / label thresholds (semitones).

    Returns
    -------
    dict
        ``samples``, ``segments``, ``aggregates``, ``labels``, ``summary``,
        plus metadata keys ``metric`` and ``label``.

    Raises
    ------
    TrajectoryError
        If fewer than two samples, duplicate sample times, or non-positive dt
        between consecutive samples.
    """
    samples = normalize_samples(raw_samples)
    if len(samples) < 2:
        raise TrajectoryError("VD10 requires at least two samples along the time axis.")

    segments: List[TrajectorySegment] = []
    speed_centres: List[float] = []

    for i in range(len(samples) - 1):
        t0 = samples[i]["time_s"]
        t1 = samples[i + 1]["time_s"]
        dt = t1 - t0
        if dt <= 0.0:
            if abs(t1 - t0) <= max(eps, DEFAULT_TIME_TOL_S):
                raise TrajectoryError(
                    f"Two samples share the same time (t={t0:.3f}s). "
                    "Each pick must be at a distinct time on the heatmap; "
                    "delete the duplicate in the sample list or re-pick at a different x."
                )
            raise TrajectoryError(
                f"Sample times must strictly increase (got t[{i}]={t0}, t[{i + 1}]={t1})."
            )
        dc = samples[i + 1]["centre"] - samples[i]["centre"]
        dw = samples[i + 1]["width"] - samples[i]["width"]
        sc = dc / dt
        sw = dw / dt
        speed_centres.append(sc)
        segments.append(
            {
                "time_from_s": t0,
                "time_to_s": t1,
                "dt_s": dt,
                "speed_centre": sc,
                "speed_width": sw,
            }
        )

    deltas = _centre_deltas(samples)
    net_displacement = samples[-1]["centre"] - samples[0]["centre"]
    total_path = sum(abs(d) for d in deltas)
    straightness = net_displacement / total_path if total_path > eps else 0.0
    inflections = _count_inflections(deltas, eps)
    abs_speeds = [abs(s) for s in speed_centres]
    mean_speed = sum(abs_speeds) / len(abs_speeds) if abs_speeds else 0.0
    median_speed = _median(abs_speeds)
    max_speed = max(abs_speeds) if abs_speeds else 0.0
    min_segment_dt_s = min(float(seg["dt_s"]) for seg in segments) if segments else 0.0

    total_time = samples[-1]["time_s"] - samples[0]["time_s"]
    net_speed = net_displacement / total_time if total_time > eps else 0.0

    aggregates: TrajectoryAggregates = {
        "net_displacement": net_displacement,
        "total_path": total_path,
        "straightness": straightness,
        "inflections": inflections,
        "mean_speed": mean_speed,
        "median_speed": median_speed,
        "max_speed": max_speed,
        "net_speed": net_speed,
        "total_time_s": total_time,
        "min_segment_dt_s": min_segment_dt_s,
    }

    labels: TrajectoryLabels = {
        "direction": _label_direction(net_displacement, eps),
        "band_behaviour": _label_band_behaviour(samples[0]["width"], samples[-1]["width"], eps),
        "shape_hint": _label_shape_hint(straightness),
    }

    result: Dict[str, Any] = {
        "metric": "VD10",
        "label": "Registral trajectory",
        "units": {
            "pitch": "semitones (MIDI integer)",
            "speed": "semitones_per_second",
            "time": "seconds",
        },
        "eps": float(eps),
        "min_dt_recommended_s": float(DEFAULT_MIN_DT_RECOMMENDED_S),
        "samples": samples,
        "segments": segments,
        "aggregates": aggregates,
        "labels": labels,
        "sampling_warnings": _sampling_warnings(segments),
        "descriptor_roles": {
            "robust": [
                "net_speed",
                "net_displacement",
                "straightness",
                "total_path",
                "inflections",
            ],
            "sampling_dependent": [
                "mean_speed",
                "median_speed",
                "max_speed",
                "segments[].speed_centre",
            ],
        },
    }
    result["summary"] = format_vd10_summary(result)
    return result


def format_vd10_summary(result: Mapping[str, Any]) -> str:
    """One-line human summary for the results panel."""
    labels = result["labels"]
    agg = result["aggregates"]
    inflections = int(agg["inflections"])
    band = labels["band_behaviour"]
    shape = labels["shape_hint"]

    direction = labels["direction"]
    if direction == "static":
        motion = "Block static (net 0 semitones/s)"
    elif direction == "ascending":
        motion = f"Block rises at {abs(float(agg['net_speed'])):.1f} semitones/s (net)"
    else:
        motion = f"Block descends at {abs(float(agg['net_speed'])):.1f} semitones/s (net)"

    band_text = {
        "diverging": "band diverging",
        "converging": "band converging",
        "stable width": "band stable",
    }.get(band, band)

    return (
        f"{motion}, {inflections} inflections, {band_text}, shape: {shape}."
    )


def export_vd10_json(result: Mapping[str, Any], path: Path | str) -> None:
    """Write VD10 result dict to JSON (same style as ``reports.export_results_json``)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(dict(result), f, indent=2, ensure_ascii=False)


def interpolate_band_at_time(
    raw_samples: Sequence[Mapping[str, float]],
    time_s: float,
) -> TrajectorySample:
    """
    Linear interpolation of registral band bounds at ``time_s``.

    Uses piecewise-linear interpolation between consecutive picks; clamps to the
    first/last sample outside the sampled span.
    """
    norm = normalize_samples(raw_samples)
    if not norm:
        return normalize_sample(time_s, 60.0, 60.0)
    if len(norm) == 1:
        s0 = norm[0]
        return normalize_sample(time_s, s0["low"], s0["high"])
    t = float(time_s)
    if t <= norm[0]["time_s"]:
        s0 = norm[0]
        return normalize_sample(t, s0["low"], s0["high"])
    if t >= norm[-1]["time_s"]:
        s1 = norm[-1]
        return normalize_sample(t, s1["low"], s1["high"])
    for i in range(len(norm) - 1):
        s0, s1 = norm[i], norm[i + 1]
        t0, t1 = s0["time_s"], s1["time_s"]
        if t0 <= t <= t1:
            if t1 <= t0:
                return normalize_sample(t, s0["low"], s0["high"])
            alpha = (t - t0) / (t1 - t0)
            low = s0["low"] + alpha * (s1["low"] - s0["low"])
            high = s0["high"] + alpha * (s1["high"] - s0["high"])
            return normalize_sample(t, low, high)
    s1 = norm[-1]
    return normalize_sample(t, s1["low"], s1["high"])


def interpolate_centre_at_times(
    raw_samples: Sequence[Mapping[str, float]],
    times: Sequence[float],
) -> List[float]:
    """Piecewise-linear centre values at each time in ``times``."""
    return [interpolate_band_at_time(raw_samples, t)["centre"] for t in times]


def _pair_direction_label(
    net_a: float,
    net_b: float,
    *,
    eps: float,
) -> str:
    dir_a = _label_direction(net_a, eps)
    dir_b = _label_direction(net_b, eps)
    if dir_a == "static" and dir_b == "static":
        return "both_static"
    if dir_a == "static" or dir_b == "static":
        return "one_static"
    if dir_a == dir_b:
        return "same_direction"
    return "opposite_direction"


def compute_block_relations(
    blocks: Sequence[Mapping[str, Any]],
    *,
    eps: float = DEFAULT_EPS,
    n_points: int = 64,
) -> Dict[str, Any]:
    """
    Characterise pairwise relationships between block centre-trajectories.

    Resamples each block's centre with linear interpolation over the shared
    overlap of all block time spans, then for each pair reports whether
    inter-centre distance converges, diverges, or stays parallel, plus whether
    net centre motion is in the same or opposite direction.

    This describes **inter-block registral geometry**, not intra-block coherence
    (orientation / anisotropy — VD8) and not VD10 net speed per block.
    """
    valid: List[Mapping[str, Any]] = []
    for block in blocks:
        samples = block.get("samples") or []
        if len(normalize_samples(samples)) >= 2:
            valid.append(block)
    pairs: List[Dict[str, Any]] = []
    if len(valid) < 2:
        return {
            "metric": "VD10_block_relations",
            "pairs": pairs,
            "note": "At least two blocks with ≥2 samples each are required.",
        }

    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            a, b = valid[i], valid[j]
            name_a = str(a.get("name") or a.get("id") or f"block_{i}")
            name_b = str(b.get("name") or b.get("id") or f"block_{j}")
            samples_a = a.get("samples") or []
            samples_b = b.get("samples") or []
            norm_a = normalize_samples(samples_a)
            norm_b = normalize_samples(samples_b)
            t0 = max(norm_a[0]["time_s"], norm_b[0]["time_s"])
            t1 = min(norm_a[-1]["time_s"], norm_b[-1]["time_s"])
            duration = t1 - t0
            if duration <= eps:
                pairs.append(
                    {
                        "block_a": name_a,
                        "block_b": name_b,
                        "overlap_from_s": t0,
                        "overlap_to_s": t1,
                        "overlap_duration_s": duration,
                        "relation": "no_overlap",
                        "direction": "n/a",
                        "mean_inter_distance_rate_st_per_s": 0.0,
                        "distance_start_st": None,
                        "distance_end_st": None,
                    }
                )
                continue

            n = max(2, int(n_points))
            step = duration / float(n - 1)
            times = [t0 + k * step for k in range(n)]
            centres_a = interpolate_centre_at_times(samples_a, times)
            centres_b = interpolate_centre_at_times(samples_b, times)
            distances = [abs(cb - ca) for ca, cb in zip(centres_a, centres_b)]
            d0, d1 = distances[0], distances[-1]
            delta_d = d1 - d0
            mean_rate = delta_d / duration if duration > eps else 0.0
            if delta_d > eps:
                relation = "diverging"
            elif delta_d < -eps:
                relation = "converging"
            else:
                relation = "parallel"
            net_a = centres_a[-1] - centres_a[0]
            net_b = centres_b[-1] - centres_b[0]
            pairs.append(
                {
                    "block_a": name_a,
                    "block_b": name_b,
                    "overlap_from_s": t0,
                    "overlap_to_s": t1,
                    "overlap_duration_s": duration,
                    "distance_start_st": d0,
                    "distance_end_st": d1,
                    "mean_inter_distance_rate_st_per_s": mean_rate,
                    "relation": relation,
                    "direction": _pair_direction_label(net_a, net_b, eps=eps),
                }
            )

    return {"metric": "VD10_block_relations", "pairs": pairs, "eps": float(eps)}


def compute_vd10_session(
    blocks: Sequence[Mapping[str, Any]],
    *,
    eps: float = DEFAULT_EPS,
) -> Dict[str, Any]:
    """
    Compute VD10 for each block and pairwise block relations.

    Blocks with fewer than two samples are included with ``vd10: null`` and an
    error message; single-block sessions match legacy ``compute_vd10`` output
    inside ``blocks[0]["vd10"]``.
    """
    block_results: List[Dict[str, Any]] = []
    for block in blocks:
        name = str(block.get("name") or block.get("id") or "block")
        block_id = str(block.get("id") or name)
        raw = list(block.get("samples") or [])
        entry: Dict[str, Any] = {
            "id": block_id,
            "name": name,
            "samples": raw,
            "vd10": None,
            "vd10_error": None,
        }
        if len(raw) < 2:
            entry["vd10_error"] = "VD10 requires at least two samples."
        else:
            try:
                entry["vd10"] = compute_vd10(raw, eps=eps)
            except TrajectoryError as exc:
                entry["vd10_error"] = str(exc)
        block_results.append(entry)

    relations = compute_block_relations(blocks, eps=eps)
    return {
        "metric": "VD10_session",
        "label": "Registral trajectory (multi-block)",
        "blocks": block_results,
        "relations": relations,
    }


def export_vd10_session_json(session: Mapping[str, Any], path: Path | str) -> None:
    """Write multi-block VD10 session (blocks + relations) to JSON."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(dict(session), f, indent=2, ensure_ascii=False)


def make_axis_calibration(
    p0_px: float,
    p0_val: float,
    p1_px: float,
    p1_val: float,
) -> Callable[[float], float]:
    """
    Build a linear pixel → axis-value map for image-based VD10 picking.

    Assumes **linear** correspondence between image position and musical pitch
    (vertical axis, semitones/MIDI) or time (horizontal axis, seconds). Valid for
    proportional graphic / spatial scores; **not** for conventional non-spatial
    symbolic notation where layout does not encode pitch or duration.

    Parameters
    ----------
    p0_px, p1_px
        Reference pixel positions along the image axis (must differ).
    p0_val, p1_val
        Musical values at those pixels (semitones or seconds).

    Returns
    -------
    callable
        ``map_px(px) -> value``, extrapolating linearly beyond the reference span.

    Raises
    ------
    TrajectoryCalibrationError
        If ``p0_px`` and ``p1_px`` are equal.
    """
    dp = float(p1_px) - float(p0_px)
    if abs(dp) < 1e-12:
        raise TrajectoryCalibrationError(
            "Calibration reference points must differ in pixel position."
        )
    slope = (float(p1_val) - float(p0_val)) / dp
    intercept = float(p0_val) - slope * float(p0_px)

    def map_px(px: float) -> float:
        return slope * float(px) + intercept

    return map_px


def describe_axis_calibration(
    p0_px: float,
    p0_val: float,
    p1_px: float,
    p1_val: float,
) -> Dict[str, float]:
    """
    Serialisable axis calibration record (reference points plus slope/intercept).

    Same linear assumption as :func:`make_axis_calibration`.
    """
    dp = float(p1_px) - float(p0_px)
    if abs(dp) < 1e-12:
        raise TrajectoryCalibrationError(
            "Calibration reference points must differ in pixel position."
        )
    slope = (float(p1_val) - float(p0_val)) / dp
    intercept = float(p0_val) - slope * float(p0_px)
    return {
        "p0_px": float(p0_px),
        "p0_val": float(p0_val),
        "p1_px": float(p1_px),
        "p1_val": float(p1_val),
        "slope": slope,
        "intercept": intercept,
    }
