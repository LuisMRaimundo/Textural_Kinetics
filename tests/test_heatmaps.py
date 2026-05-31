from pathlib import Path

import pytest

from granular_v2.config import HeatmapConfig
from granular_v2.heatmaps import (
    build_pitch_time_matrix,
    build_spectral_energy_matrix,
    plot_heatmap_advanced,
    plot_heatmap_basic,
    plot_spectral_energy_heatmap,
    save_both_heatmaps,
)


def _synthetic_notes():
    return [
        {"onset_sec": 0.0, "duration_sec": 0.5, "pitch": 60, "velocity": 80},
        {"onset_sec": 0.5, "duration_sec": 0.5, "pitch": 64, "velocity": 90},
        {"onset_sec": 1.0, "duration_sec": 1.0, "pitch": 67, "velocity": 70},
    ]


def test_build_matrix_shapes():
    H, t, p = build_pitch_time_matrix(_synthetic_notes(), bin_sec=0.25, mode="occupancy")
    assert H.ndim == 2
    assert H.sum() >= 3
    assert len(t) == H.shape[1]
    assert len(p) == H.shape[0]


def test_onsets_mode_single_bin_hits():
    notes = [{"onset_sec": 0.0, "duration_sec": 2.0, "pitch": 60, "velocity": 64}]
    H, _, _ = build_pitch_time_matrix(notes, bin_sec=1.0, mode="onsets")
    assert H.sum() == 1.0


def test_spectral_energy_matrix():
    E, (t0, t1), (p0, p1) = build_spectral_energy_matrix(_synthetic_notes(), (32, 64), 0.0)
    assert E.shape == (32, 64)
    assert t1 > t0 and p1 >= p0
    assert E.max() > 0


@pytest.mark.parametrize("plot_fn", [plot_heatmap_basic, plot_heatmap_advanced, plot_spectral_energy_heatmap])
def test_plot_functions_return_figure(plot_fn):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    fig = plot_fn(_synthetic_notes(), HeatmapConfig())
    assert fig is not None


def test_save_both_heatmaps(tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    paths = save_both_heatmaps(_synthetic_notes(), tmp_path, HeatmapConfig())
    assert "heatmap_basic" in paths
    assert "heatmap_advanced" in paths
    assert "heatmap_spectral" in paths
    for p in paths.values():
        assert Path(p).exists()


def test_pipeline_on_fixture(sample_musicxml, tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from granular_v2.pipeline import run_heatmap_analysis

    r = run_heatmap_analysis(sample_musicxml, tmp_path)
    assert r["num_events"] > 0
    assert len(r["heatmap_paths"]) == 3
