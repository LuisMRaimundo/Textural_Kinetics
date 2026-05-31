from granular_v2.config import AnalysisConfig
from granular_v2.fusion import run_full_analysis
from granular_v2.loader import load_score_and_note_matrix


def test_partitional_layer(sample_musicxml):
    score, nm, _ = load_score_and_note_matrix(sample_musicxml)
    cfg = AnalysisConfig(include_partitional=True, enable_mustextu=False, enable_heatmaps=False)
    r = run_full_analysis(nm, score, cfg)
    assert "partitional" in r
    assert "0.1" in r["partitional"]


def test_empty_matrix():
    cfg = AnalysisConfig(enable_mustextu=False)
    r = run_full_analysis([], None, cfg)
    assert r["num_events"] == 0
