import math

import pytest

from granular_v2.event_rates import (
    compute_all_event_rates,
    global_event_rates,
    rates_by_ms_window,
    rates_by_time_bin,
)


def _notes():
    return [
        {"onset_sec": 0.0, "duration_sec": 0.5, "pitch": 60, "velocity": 80},
        {"onset_sec": 0.5, "duration_sec": 0.5, "pitch": 64, "velocity": 80},
        {"onset_sec": 1.0, "duration_sec": 0.5, "pitch": 67, "velocity": 80},
    ]


def test_global_events_per_second():
    g = global_event_rates(_notes())
    assert g["num_events"] == 3
    # onsets 0, 0.5, 1.0 → span = 1.0 s → 3 events/s
    assert abs(g["events_per_second"] - 3.0) < 1e-9
    assert abs(g["events_per_millisecond"] - 0.003) < 1e-12


def test_ms_window_definition():
    r = rates_by_ms_window(_notes(), window_ms=500.0, step_ms=250.0)
    assert "events_per_millisecond_in_window" in r["definition"]
    assert len(r["time_points_sec"]) >= 1


def test_per_bar_with_measure_fields():
    notes = [
        {
            "onset_sec": 0.1,
            "duration_sec": 0.4,
            "pitch": 60,
            "measure_number": 1,
            "measure_start_sec": 0.0,
            "measure_duration_sec": 2.0,
            "measure_beats": 4.0,
        },
        {
            "onset_sec": 0.6,
            "duration_sec": 0.4,
            "pitch": 62,
            "measure_number": 1,
            "measure_start_sec": 0.0,
            "measure_duration_sec": 2.0,
            "measure_beats": 4.0,
        },
    ]
    full = compute_all_event_rates(notes, density_intervals=[0.5])
    assert len(full["per_bar"]) == 1
    bar = full["per_bar"][0]
    assert bar["onset_count"] == 2
    assert abs(bar["events_per_second_in_bar"] - 1.0) < 1e-9
    assert abs(bar["events_per_beat_in_bar"] - 0.5) < 1e-9


def test_bin_events_per_sec():
    b = rates_by_time_bin(_notes(), 0.5)
    assert len(b["events_per_second_per_bin"]) >= 1
