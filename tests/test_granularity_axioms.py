"""IOI, burstiness, granularity index — textbook checks."""

import pytest

from granular_v2.activity_granularity import (
    granularity_metrics,
    inter_onset_intervals,
)


def _matrix_from_onsets(onsets):
    return [
        {"onset_sec": float(t), "duration_sec": 0.1, "pitch": 60}
        for t in onsets
    ]


def test_regular_train_maximally_regular():
    onsets = [i * 0.5 for i in range(8)]
    g = granularity_metrics(_matrix_from_onsets(onsets))
    assert g["ioi_cv"] == pytest.approx(0.0, abs=1e-12)
    assert g["granularity_index"] == pytest.approx(1.0, abs=1e-12)
    assert g["burstiness"] < 0.0


def test_global_rate_exact():
    onsets = [0.0, 0.19, 0.38, 0.57, 0.76, 0.95]
    g = granularity_metrics(_matrix_from_onsets(onsets))
    expected = 6 / (0.95 - 0.0)
    assert g["events_per_sec_global"] == pytest.approx(expected, rel=1e-9)


def test_bursty_positive():
    # cluster at t=0 then sparse — σ > μ in 0.5s bins
    onsets = [0.0, 0.01, 0.02, 0.03, 0.04, 2.0, 4.0, 6.0]
    g = granularity_metrics(_matrix_from_onsets(onsets))
    assert g["burstiness"] > 0.0
    assert g["burstiness"] < 1.0


def test_ioi_diff():
    onsets = [0.0, 0.5, 1.0]
    iois = inter_onset_intervals(_matrix_from_onsets(onsets))
    assert list(iois) == pytest.approx([0.5, 0.5])


def test_vd4_fused_onsets_doubled_grid():
    """Regular 1 s grid doubled +0.5 ms: fused metrics regular; raw IOI CV inflated."""
    base = [float(i) for i in range(5)]
    doubled = base + [t + 0.0005 for t in base]
    g = granularity_metrics(_matrix_from_onsets(doubled))
    assert g["num_events"] == 5
    assert g["num_events_raw"] == 10
    assert g["sync_fraction"] == pytest.approx(0.5)
    assert g["ioi_cv"] == pytest.approx(0.0, abs=1e-12)
    assert g["granularity_index"] == pytest.approx(1.0, abs=1e-12)
    assert g["ioi_cv_raw"] > 0.5


def test_vd4_no_simultaneity_raw_matches_fused():
    onsets = [0.0, 0.37, 0.91, 1.55, 2.8]
    g = granularity_metrics(_matrix_from_onsets(onsets))
    assert g["ioi_cv"] == pytest.approx(g["ioi_cv_raw"])
    assert g["granularity_index"] == pytest.approx(g["granularity_index_raw"])
    assert g["sync_fraction"] == pytest.approx(0.0)
