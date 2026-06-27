import json
from pathlib import Path

import pytest

from granular_v2.trajectory import (
    TrajectoryError,
    compute_vd10,
    export_vd10_json,
    format_vd10_summary,
    normalize_sample,
    normalize_samples,
    snap_semitone,
)


def test_snap_semitone_clamps_and_rounds():
    assert snap_semitone(60.4) == 60
    assert snap_semitone(60.6) == 61
    assert snap_semitone(-5) == 0
    assert snap_semitone(200) == 127


def test_normalize_sample_orders_bounds():
    s = normalize_sample(1.5, 64.0, 60.0)
    assert s["low"] == 60
    assert s["high"] == 64
    assert s["centre"] == 62.0
    assert s["width"] == 4.0


def test_normalize_samples_sorts_by_time():
    raw = [
        {"time_s": 2.0, "low": 68, "high": 72},
        {"time_s": 0.0, "low": 60, "high": 64},
    ]
    out = normalize_samples(raw)
    assert [s["time_s"] for s in out] == [0.0, 2.0]


def test_ascending_net_speed():
    r = compute_vd10(
        [
            {"time_s": 0.0, "low": 60, "high": 64},
            {"time_s": 2.0, "low": 68, "high": 72},
        ]
    )
    agg = r["aggregates"]
    assert r["metric"] == "VD10"
    assert agg["net_displacement"] == 8.0
    assert abs(agg["net_speed"] - 4.0) < 1e-9
    assert r["labels"]["direction"] == "ascending"
    assert r["labels"]["shape_hint"] == "unidirectional"
    assert len(r["segments"]) == 1
    assert abs(r["segments"][0]["speed_centre"] - 4.0) < 1e-9


def test_oscillation_net_speed_zero():
    r = compute_vd10(
        [
            {"time_s": 0.0, "low": 60, "high": 64},
            {"time_s": 1.0, "low": 64, "high": 68},
            {"time_s": 2.0, "low": 60, "high": 64},
        ]
    )
    agg = r["aggregates"]
    assert abs(agg["net_displacement"]) < 1e-9
    assert abs(agg["net_speed"]) < 1e-9
    assert agg["total_path"] > 0
    assert r["labels"]["direction"] == "static"
    assert r["labels"]["shape_hint"] == "undulating"


def test_inflections_and_mixed_shape():
    r = compute_vd10(
        [
            {"time_s": 0.0, "low": 60, "high": 60},
            {"time_s": 1.0, "low": 68, "high": 68},
            {"time_s": 2.0, "low": 66, "high": 66},
        ]
    )
    assert r["aggregates"]["inflections"] == 1
    assert r["labels"]["shape_hint"] == "mixed"


def test_descending_summary():
    r = compute_vd10(
        [
            {"time_s": 0.0, "low": 72, "high": 72},
            {"time_s": 2.0, "low": 64, "high": 64},
        ]
    )
    assert r["labels"]["direction"] == "descending"
    assert "descends at" in r["summary"]


def test_band_behaviour_diverging_and_converging():
    up = compute_vd10(
        [
            {"time_s": 0.0, "low": 60, "high": 60},
            {"time_s": 1.0, "low": 60, "high": 64},
        ]
    )
    down = compute_vd10(
        [
            {"time_s": 0.0, "low": 60, "high": 64},
            {"time_s": 1.0, "low": 62, "high": 62},
        ]
    )
    assert up["labels"]["band_behaviour"] == "diverging"
    assert down["labels"]["band_behaviour"] == "converging"


def test_requires_two_samples():
    with pytest.raises(TrajectoryError, match="at least two"):
        compute_vd10([{"time_s": 0.0, "low": 60, "high": 64}])


def test_rejects_duplicate_times():
    with pytest.raises(TrajectoryError, match="same time"):
        compute_vd10(
            [
                {"time_s": 0.0, "low": 60, "high": 64},
                {"time_s": 1.0, "low": 62, "high": 66},
                {"time_s": 1.0, "low": 68, "high": 72},
            ]
        )


def test_format_vd10_summary_static():
    r = compute_vd10(
        [
            {"time_s": 0.0, "low": 60, "high": 64},
            {"time_s": 1.0, "low": 60, "high": 64},
        ]
    )
    summary = format_vd10_summary(r)
    assert "static" in summary
    assert summary == r["summary"]


def test_export_vd10_json(tmp_path: Path):
    r = compute_vd10(
        [
            {"time_s": 0.0, "low": 60, "high": 64},
            {"time_s": 1.0, "low": 66, "high": 70},
        ]
    )
    out = tmp_path / "nested" / "vd10.json"
    export_vd10_json(r, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["metric"] == "VD10"
    assert data["aggregates"]["net_displacement"] == 6.0
