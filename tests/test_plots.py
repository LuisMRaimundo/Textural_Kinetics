def test_plot_activity_smoke(sample_musicxml):
    pytest = __import__("pytest")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from granular_v2.config import AnalysisConfig
    from granular_v2.fusion import run_full_analysis
    from granular_v2.loader import load_score_and_note_matrix
    from granular_v2.plots import plot_activity_granularity

    score, nm, _ = load_score_and_note_matrix(sample_musicxml)
    r = run_full_analysis(nm, score, AnalysisConfig(enable_mustextu=False))
    fig = plot_activity_granularity(r)
    assert fig is not None
