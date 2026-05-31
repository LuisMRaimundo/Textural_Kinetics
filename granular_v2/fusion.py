"""Assemble full analysis dict from note matrix + score."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .activity_granularity import run_activity_granularity
from .config import AnalysisConfig
from .event_rates import compute_all_event_rates
from .granularity_mustextu import analyze_mustextu_from_score
from .measures import attach_measure_to_notes, build_measure_timeline
from .note_types import NoteMatrix
from .partition_state import PartitionStateAnalyzer
from .reports import export_metadata


def run_full_analysis(
    note_matrix: NoteMatrix,
    score,
    config: AnalysisConfig,
    tempo_audit: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    cfg = config
    measures = build_measure_timeline(score, default_bpm=cfg.default_bpm) if score is not None else []
    if measures:
        attach_measure_to_notes(note_matrix, measures)

    results: Dict[str, Any] = {
        "num_events": len(note_matrix),
        "activity_granularity": run_activity_granularity(note_matrix, cfg.density_intervals),
        "event_rates": compute_all_event_rates(
            note_matrix,
            density_intervals=cfg.density_intervals,
            ms_windows=cfg.ms_rate_windows,
            measures=measures,
        ),
        "export_metadata": export_metadata(cfg),
        "tempo_audit": tempo_audit or {},
    }

    if cfg.enable_mustextu and score is not None:
        results["mustextu_summary"] = analyze_mustextu_from_score(score, cfg.mustextu)

    if cfg.include_partitional:
        ps = PartitionStateAnalyzer(partition_mode=cfg.partition_mode)
        part_by: Dict[str, Any] = {}
        for iv in cfg.density_intervals:
            part = ps.run(note_matrix, iv)
            part_by[str(iv)] = {
                "time_points": part["time_points"].tolist(),
                "n": part["n"].tolist(),
                "agglomeration": part["agglomeration"].tolist(),
                "dispersion": part["dispersion"].tolist(),
            }
        results["partitional"] = part_by

    return results
