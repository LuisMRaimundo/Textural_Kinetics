"""
Granular_v2 — fused symbolic density analyzer.

Event rates (per second, millisecond, bar), Mustextu granularity, activity density,
optional partitional layer, dual heatmaps.
"""

from .config import AnalysisConfig, HeatmapConfig, MustextuConfig, default_analysis_config
from .event_rates import compute_all_event_rates, global_event_rates
from .heatmaps import save_both_heatmaps
from .loader import load_score_and_note_matrix
from .pipeline import run_analysis, run_heatmap_analysis

__version__ = "1.0.5"

__all__ = [
    "AnalysisConfig",
    "HeatmapConfig",
    "MustextuConfig",
    "default_analysis_config",
    "run_analysis",
    "run_heatmap_analysis",
    "load_score_and_note_matrix",
    "compute_all_event_rates",
    "global_event_rates",
    "save_both_heatmaps",
]
