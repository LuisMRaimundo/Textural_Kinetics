from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class MustextuConfig:
    default_bpm: float = 120.0
    window_ms: float | None = None
    iei_timbre_ms: float = 20.0
    coincidence_ms: float = 2.0
    adaptive_tolerance: bool = True
    tol_frac_of_min_period: float = 0.05
    align_window_to_beat: bool = True
    gran_max_eps: float = 50.0
    ignore_grace: bool = True


@dataclass
class HeatmapConfig:
    bin_sec: float = 0.05
    pitch_step_semitones: float = 0.5
    mode: str = "occupancy"
    smooth_t_bins: float = 1.2
    smooth_p_bins: float = 0.8
    log1p: bool = True
    gamma: float = 0.82
    normalize_rows: bool = False
    rowwise_percentile: float = 96.0
    overlay_points: bool = False
    time_units: str = "s"
    publication_style: bool = True
    contrast_vmin_percentile: float = 3.0
    contrast_vmax_percentile: float = 97.5
    cmap_basic: str = "granular_blue"
    cmap_advanced: str = "granular_blue"
    spectral_resolution: Tuple[int, int] = (160, 320)
    spectral_smoothing: float = 1.4
    spectral_cmap: str = "granular_ember"
    show_measure_lines: bool = True
    show_event_markers: bool = True
    max_event_markers: int = 16
    save_dpi: int = 200
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.mode not in ("occupancy", "onsets", "velocity"):
            raise ValueError(f"mode must be occupancy|onsets|velocity, got {self.mode!r}")
        if self.time_units not in ("s", "ms", "cs"):
            raise ValueError(f"time_units must be s|ms|cs, got {self.time_units!r}")
        if self.bin_sec <= 0:
            raise ValueError("bin_sec must be > 0")


@dataclass
class AnalysisConfig:
    merge_ties: bool = True
    pitch_domain: str = "written"
    default_bpm: float = 120.0
    density_intervals: List[float] = field(default_factory=lambda: [0.1, 0.5, 1.0])
    ms_rate_windows: List[float] = field(default_factory=lambda: [50.0, 100.0, 500.0])
    include_partitional: bool = False
    partition_mode: str = "channels"
    enable_mustextu: bool = True
    enable_heatmaps: bool = True
    heatmap: HeatmapConfig = field(default_factory=HeatmapConfig)
    mustextu: MustextuConfig = field(default_factory=MustextuConfig)

    def __post_init__(self) -> None:
        if self.pitch_domain not in ("written", "sounding"):
            raise ValueError(f"pitch_domain must be written|sounding, got {self.pitch_domain!r}")
        if self.partition_mode not in ("channels", "rhythmic", "linear"):
            raise ValueError(f"partition_mode invalid: {self.partition_mode!r}")
        bpm = float(self.default_bpm)
        if not math.isfinite(bpm) or bpm <= 0:
            raise ValueError("default_bpm must be > 0")
        for i, x in enumerate(self.density_intervals):
            xf = float(x)
            if not math.isfinite(xf) or xf <= 0:
                raise ValueError(f"density_intervals[{i}] must be positive")
        self.mustextu.default_bpm = self.default_bpm


def default_analysis_config() -> AnalysisConfig:
    return AnalysisConfig()
