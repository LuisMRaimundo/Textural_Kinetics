"""
Textural_Kinetics — fused symbolic temporal-density analyzer.

Python package: ``granular_v2`` (install name ``granular-v2``).

Event rates (per second, millisecond, bar), Mustextu granularity, activity density,
optional partitional layer, dual heatmaps.
"""

from .config import AnalysisConfig, HeatmapConfig, MustextuConfig, default_analysis_config
from .event_rates import compute_all_event_rates, global_event_rates
from .heatmaps import save_both_heatmaps
from .loader import load_score_and_note_matrix
from .metadata import CANONICAL_TOOL_NAME, __version__
from .pipeline import run_analysis, run_heatmap_analysis
from .trajectory import (
    compute_block_relations,
    compute_vd10,
    compute_vd10_session,
    describe_axis_calibration,
    export_vd10_json,
    export_vd10_session_json,
    format_vd10_summary,
    make_axis_calibration,
)

__all__ = [
    "CANONICAL_TOOL_NAME",
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
    "compute_block_relations",
    "compute_vd10_session",
    "export_vd10_json",
    "export_vd10_session_json",
    "format_vd10_summary",
    "make_axis_calibration",
    "describe_axis_calibration",
]
