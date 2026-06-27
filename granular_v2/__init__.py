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
from .trajectory import compute_vd10, export_vd10_json, format_vd10_summary

__version__ = "1.0.9"

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
    "compute_vd10",
    "export_vd10_json",
    "format_vd10_summary",
]
