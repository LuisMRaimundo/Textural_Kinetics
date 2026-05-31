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
    assert g["burstiness"] == pytest.approx(-1.0, abs=1e-6)


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
