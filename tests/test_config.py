import pytest

from granular_v2.config import AnalysisConfig, HeatmapConfig


def test_invalid_pitch_domain():
    with pytest.raises(ValueError):
        AnalysisConfig(pitch_domain="invalid")


def test_heatmap_mode():
    with pytest.raises(ValueError):
        HeatmapConfig(mode="bad")
