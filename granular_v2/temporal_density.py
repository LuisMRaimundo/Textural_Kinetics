"""Multi-scale temporal density: onset and active note count per bin."""

from typing import Any, Dict, List

import numpy as np


def _note_start_end(row):
    onset = float(row.get("onset_sec", row.get("onset_beats", 0)))
    dur = float(row.get("duration_sec", row.get("duration_beats", 0)))
    return onset, onset + dur


class TemporalDensityAnalyzer:
    def __init__(self, time_unit: str = "seconds"):
        self.time_unit = time_unit

    def run(self, note_matrix: List[Dict], interval: float) -> Dict:
        if not note_matrix:
            return {
                "time_points": np.array([]),
                "onset_density": np.array([]),
                "active_density": np.array([]),
                "interval": interval,
            }
        ends = [_note_start_end(r)[1] for r in note_matrix]
        total_time = max(ends)
        if total_time <= 0:
            return {
                "time_points": np.array([]),
                "onset_density": np.array([]),
                "active_density": np.array([]),
                "interval": interval,
            }
        bins = np.arange(0.0, total_time + interval, interval, dtype=float)
        if len(bins) < 2:
            bins = np.array([0.0, total_time], dtype=float)
        onset_density = np.zeros(len(bins) - 1, dtype=float)
        active_density = np.zeros(len(bins) - 1, dtype=float)
        for row in note_matrix:
            s, e = _note_start_end(row)
            idx = int(np.searchsorted(bins, s, side="right") - 1)
            if 0 <= idx < len(onset_density):
                onset_density[idx] += 1.0
            overlap = np.where((bins[:-1] < e) & (bins[1:] > s))[0]
            if overlap.size > 0:
                active_density[overlap] += 1.0
        time_points = bins[:-1] + interval / 2.0
        return {
            "time_points": time_points,
            "onset_density": onset_density,
            "active_density": active_density,
            "interval": float(interval),
        }
