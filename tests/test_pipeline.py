from pathlib import Path

import pytest

from granular_v2.config import AnalysisConfig
from granular_v2.pipeline import run_analysis


def test_run_analysis_fixture(sample_musicxml, tmp_path):
    pytest.importorskip("matplotlib").use("Agg")
    cfg = AnalysisConfig(enable_heatmaps=True, enable_mustextu=True)
    r = run_analysis(sample_musicxml, cfg, output_dir=tmp_path)
    assert r["num_events"] > 0
    g = r["event_rates"]["global"]
    assert g["events_per_second"] > 0
    assert (tmp_path / "analysis.json").exists()
    assert "mustextu_summary" in r
    assert "heatmap_paths" in r
    assert "tempo_audit" in r
    assert r["tempo_audit"].get("source")


def test_run_analysis_no_heatmaps(sample_musicxml, tmp_path):
    cfg = AnalysisConfig(enable_heatmaps=False, enable_mustextu=True)
    r = run_analysis(sample_musicxml, cfg, output_dir=tmp_path)
    assert "heatmap_paths" not in r
