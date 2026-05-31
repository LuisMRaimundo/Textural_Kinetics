"""Canonical analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .config import AnalysisConfig, default_analysis_config
from .fusion import run_full_analysis
from .heatmaps import save_both_heatmaps
from .loader import load_score_and_note_matrix
from .reports import export_results_json


def run_analysis(
    file_path: Union[str, Path],
    config: Optional[AnalysisConfig] = None,
    *,
    output_dir: Optional[Union[str, Path]] = None,
    export_json: bool = True,
) -> Dict[str, Any]:
    """
    Full fused analysis: event rates (s/ms/bar), activity, Mustextu, optional heatmaps.
    """
    cfg = config or default_analysis_config()
    path = Path(file_path)
    score, note_matrix, tempo_audit = load_score_and_note_matrix(
        path,
        merge_ties=cfg.merge_ties,
        pitch_domain=cfg.pitch_domain,
        default_bpm=cfg.default_bpm,
    )

    results = run_full_analysis(note_matrix, score, cfg, tempo_audit=tempo_audit)
    results["source_file"] = str(path.resolve())

    out_dir = Path(output_dir) if output_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        if export_json:
            export_results_json(results, out_dir / "analysis.json")
        if cfg.enable_heatmaps:
            results["heatmap_paths"] = save_both_heatmaps(
                note_matrix, out_dir, cfg.heatmap, score=score
            )

    return results


def run_heatmap_analysis(
    file_path: Union[str, Path],
    output_dir: Union[str, Path],
    config: Optional[AnalysisConfig] = None,
) -> Dict[str, Any]:
    """Heatmaps only (backward compatible)."""
    cfg = config or default_analysis_config()
    cfg.enable_heatmaps = True
    score, nm, _ = load_score_and_note_matrix(
        file_path,
        merge_ties=cfg.merge_ties,
        pitch_domain=cfg.pitch_domain,
        default_bpm=cfg.default_bpm,
    )
    paths = save_both_heatmaps(nm, output_dir, cfg.heatmap, score=score)
    return {"num_events": len(nm), "heatmap_paths": paths}
