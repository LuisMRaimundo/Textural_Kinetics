"""Optional partition-state layer (channel-based n, alpha, d indices)."""

from typing import Any, Dict, List, Tuple

import numpy as np


def _note_start_end(row):
    onset = float(row.get("onset_sec", row.get("onset_beats", 0)))
    dur = float(row.get("duration_sec", row.get("duration_beats", 0)))
    return onset, onset + dur


def _pairs(n: int) -> int:
    return n * (n - 1) // 2 if n >= 2 else 0


def _agglomeration_from_partition(partition: Tuple[int, ...]) -> int:
    return sum(_pairs(ni) for ni in partition if ni >= 2)


def partition_mode_channels(note_matrix: List[Dict], bin_start: float, bin_end: float) -> Tuple[int, Tuple[int, ...]]:
    channel_counts: Dict[int, int] = {}
    for row in note_matrix:
        onset = float(row.get("onset_sec", row.get("onset_beats", 0)))
        end = onset + float(row.get("duration_sec", row.get("duration_beats", 0)))
        if end <= bin_start or onset >= bin_end:
            continue
        ch = int(row.get("channel", 0)) % 16
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
    if not channel_counts:
        return 0, ()
    counts = tuple(sorted(channel_counts.values(), reverse=True))
    return sum(counts), counts


class PartitionStateAnalyzer:
    def __init__(self, partition_mode: str = "channels", time_unit: str = "seconds"):
        self.partition_mode = partition_mode
        self.time_unit = time_unit

    def _get_partition(self, note_matrix: List[Dict], bin_start: float, bin_end: float) -> Tuple[int, Tuple[int, ...]]:
        if self.partition_mode == "channels":
            return partition_mode_channels(note_matrix, bin_start, bin_end)
        n_active = 0
        for row in note_matrix:
            onset = float(row.get("onset_sec", row.get("onset_beats", 0)))
            end = onset + float(row.get("duration_sec", row.get("duration_beats", 0)))
            if end > bin_start and onset < bin_end:
                n_active += 1
        return (n_active, (n_active,)) if n_active else (0, ())

    def run(self, note_matrix: List[Dict], interval: float) -> Dict:
        empty = {
            "time_points": np.array([]),
            "n": np.array([], dtype=int),
            "partition_vectors": [],
            "T": np.array([]),
            "agglomeration": np.array([]),
            "dispersion": np.array([]),
            "interval": interval,
        }
        if not note_matrix:
            return empty
        ends = [_note_start_end(row)[1] for row in note_matrix]
        total_time = max(ends)
        if total_time <= 0:
            return empty
        bins = np.arange(0.0, total_time + interval, interval, dtype=float)
        if len(bins) < 2:
            bins = np.array([0.0, total_time], dtype=float)
        time_points = bins[:-1] + interval / 2.0
        n_list, partition_vectors, T_list, alpha_list, d_list = [], [], [], [], []
        for i in range(len(bins) - 1):
            b0, b1 = float(bins[i]), float(bins[i + 1])
            n, part = self._get_partition(note_matrix, b0, b1)
            n_list.append(n)
            partition_vectors.append(part)
            T_val = _pairs(n)
            alpha_val = _agglomeration_from_partition(part)
            d_list.append(T_val - alpha_val)
            T_list.append(T_val)
            alpha_list.append(alpha_val)
        return {
            "time_points": time_points,
            "n": np.array(n_list, dtype=int),
            "partition_vectors": partition_vectors,
            "T": np.array(T_list, dtype=float),
            "agglomeration": np.array(alpha_list, dtype=float),
            "dispersion": np.array(d_list, dtype=float),
            "interval": float(interval),
        }
