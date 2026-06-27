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
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, TypedDict

DEFAULT_EPS = 0.01


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
    max_speed: float
    net_speed: float
    total_time_s: float


class TrajectoryError(ValueError):
    """Invalid VD10 sample series or non-monotonic time."""


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
    max_speed = max(abs_speeds) if abs_speeds else 0.0

    total_time = samples[-1]["time_s"] - samples[0]["time_s"]
    net_speed = net_displacement / total_time if total_time > eps else 0.0

    aggregates: TrajectoryAggregates = {
        "net_displacement": net_displacement,
        "total_path": total_path,
        "straightness": straightness,
        "inflections": inflections,
        "mean_speed": mean_speed,
        "max_speed": max_speed,
        "net_speed": net_speed,
        "total_time_s": total_time,
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
        "samples": samples,
        "segments": segments,
        "aggregates": aggregates,
        "labels": labels,
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
