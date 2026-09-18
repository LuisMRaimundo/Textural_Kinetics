"""VD4 / VD10 thesis-conformance tests (B, T, G, F, R, V)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from music21 import chord, duration, note, stream, tie

from granular_v2.activity_granularity import (
    COINCIDENCE_TOL_SEC,
    burstiness_fano,
    effective_coincidence_tol_sec,
    granularity_metrics,
    merge_coincident_onsets,
)
from granular_v2.config import MustextuConfig
from granular_v2.event_rates import global_event_rates
from granular_v2.granularity_mustextu import analyze_mustextu_from_score
from granular_v2.loader import load_score_and_note_matrix
from granular_v2.note_extraction import extract_notes_with_ties
from granular_v2.onset_extraction import (
    GRACE_NOMINAL_SPACING_SEC,
    assign_grace_nominal_onsets,
    extract_onsets_per_layer_ms_from_score,
    onsets_per_layer_from_note_matrix,
    onsets_per_layer_ms_from_note_matrix,
)
from granular_v2.trajectory import auto_pick_samples_for_part, compute_vd10

ROOT = Path(__file__).resolve().parents[1]


def _matrix_from_onsets(onsets, part: str = "P"):
    return [
        {"onset_sec": float(t), "duration_sec": 0.05, "pitch": 60, "part": part, "is_grace": False}
        for t in onsets
    ]


def _score_part(*elements, part_name: str = "Voice") -> stream.Score:
    part = stream.Part()
    part.partName = part_name
    offset = 0.0
    for el in elements:
        part.insert(offset, el)
        offset += float(getattr(el, "quarterLength", 0.0) or 0.0)
    score = stream.Score()
    score.insert(0, part)
    return score


# ---------------------------------------------------------------------------
# Burst (Fano)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rate", [0.5, 2.0, 8.0, 20.0])
def test_b1_poisson_burstiness_near_zero(rate: float) -> None:
    rng = np.random.default_rng(20260918 + int(rate * 10))
    n = 4000
    iois = rng.exponential(1.0 / rate, size=n)
    onsets = np.cumsum(iois)
    onsets = onsets - onsets[0]
    b = burstiness_fano(onsets)
    assert math.isfinite(b)
    assert abs(b) < 0.10, f"rate={rate}/s B={b}"


@pytest.mark.parametrize("period", [0.25, 0.125])
def test_b2_regular_burstiness_minus_one(period: float) -> None:
    onsets = [i * period for i in range(80)]
    b = burstiness_fano(onsets)
    assert b == pytest.approx(-1.0, abs=1e-9)


def test_b3_bursts_positive() -> None:
    onsets = []
    for cycle in range(20):
        t0 = cycle * 4.0
        onsets.extend(t0 + i * 0.05 for i in range(8))
    b = burstiness_fano(onsets)
    assert b > 0.5


def test_b4_regular_period_not_dividing_window() -> None:
    onsets = [i * 0.30 for i in range(80)]
    b = burstiness_fano(onsets)
    print(f"B4_VALUE={b!r}")
    assert math.isfinite(b)
    assert b < -0.5


def test_b5_fewer_than_two_full_windows_is_nan() -> None:
    assert math.isnan(burstiness_fano([0.0, 0.2, 0.4]))
    assert math.isnan(burstiness_fano([0.0]))
    g = granularity_metrics(_matrix_from_onsets([0.0, 0.2]))
    assert math.isnan(g["burstiness"])


# ---------------------------------------------------------------------------
# Ties / one onset source
# ---------------------------------------------------------------------------

def test_t1_tied_note_across_barline_one_onset_both_paths() -> None:
    n1 = note.Note("C4", quarterLength=4.0)
    n1.tie = tie.Tie("start")
    n2 = note.Note("C4", quarterLength=4.0)
    n2.tie = tie.Tie("stop")
    part = stream.Part()
    part.partName = "Voice"
    m1 = stream.Measure(number=1)
    m1.append(n1)
    m2 = stream.Measure(number=2)
    m2.append(n2)
    part.append(m1)
    part.append(m2)
    score = stream.Score()
    score.insert(0, part)

    notes = extract_notes_with_ties(score, merge_ties=True)
    assert len(notes) == 1
    layers, _, _, _ = extract_onsets_per_layer_ms_from_score(score)
    n_onsets = sum(len(v) for v in layers.values())
    assert n_onsets == 1
    g = granularity_metrics(
        [{"onset_sec": 0.0, "duration_sec": 4.0, "pitch": 60, "part": "Voice", "is_grace": False}]
    )
    assert g["num_events"] == 1


def test_t2_partially_tied_chord_is_new_onset() -> None:
    c1 = chord.Chord(["C4", "E4"], quarterLength=1.0)
    c1.notes[0].tie = tie.Tie("start")
    c2 = chord.Chord(["C4", "G4"], quarterLength=1.0)
    c2.notes[0].tie = tie.Tie("stop")
    score = _score_part(c1, c2, part_name="Piano")

    notes = extract_notes_with_ties(score, merge_ties=True)
    starts = sorted({round(float(n["start"]), 6) for n in notes})
    assert starts == [pytest.approx(0.0), pytest.approx(1.0)]
    pitches_at_second = {int(n["pitch"]) for n in notes if abs(float(n["start"]) - 1.0) < 1e-9}
    assert 67 in pitches_at_second
    assert 60 not in pitches_at_second

    layers, _, _, _ = extract_onsets_per_layer_ms_from_score(score)
    pooled = sorted(t for ts in layers.values() for t in ts)
    assert len(pooled) == 2


def test_t3_rate_and_ioi_cv_share_onset_set(sample_musicxml) -> None:
    score, nm, _ = load_score_and_note_matrix(sample_musicxml)
    layers = onsets_per_layer_from_note_matrix(nm)
    pooled = [t for ts in layers.values() for t in ts]
    tol = effective_coincidence_tol_sec(layers.values())
    cv_onsets, _ = merge_coincident_onsets(pooled, tol)

    must = analyze_mustextu_from_score(score, MustextuConfig(), note_matrix=nm)
    rate_onsets = np.array(must["mustextu"]["sequences"]["merged_times_ms"], dtype=float) / 1000.0
    assert cv_onsets.size == rate_onsets.size
    assert cv_onsets == pytest.approx(rate_onsets, abs=1e-9)

    extract_layers = extract_onsets_per_layer_ms_from_score(score)[0]
    matrix_layers = onsets_per_layer_ms_from_note_matrix(nm)
    assert {k: [round(x, 6) for x in v] for k, v in extract_layers.items()} == {
        k: [round(x, 6) for x in v] for k, v in matrix_layers.items()
    }
    g = granularity_metrics(nm)
    assert g["coincidence_tol_sec_effective"] == pytest.approx(tol)


# ---------------------------------------------------------------------------
# Grace notes
# ---------------------------------------------------------------------------

def test_g1_two_graces_before_principal() -> None:
    notes = [
        {"onset_sec": 1.0, "duration_sec": 0.0, "pitch": 64, "part": "Fl", "is_grace": True},
        {"onset_sec": 1.0, "duration_sec": 0.0, "pitch": 65, "part": "Fl", "is_grace": True},
        {"onset_sec": 1.0, "duration_sec": 0.5, "pitch": 67, "part": "Fl", "is_grace": False},
        {"onset_sec": 0.0, "duration_sec": 0.4, "pitch": 60, "part": "Fl", "is_grace": False},
    ]
    audit = assign_grace_nominal_onsets(notes)
    onsets = sorted({round(float(n["onset_sec"]), 9) for n in notes})
    group = [t for t in onsets if t > 0.0]
    assert len(group) == 3
    s = GRACE_NOMINAL_SPACING_SEC
    assert notes[0]["onset_sec"] == pytest.approx(1.0 - 2 * s)
    assert notes[1]["onset_sec"] == pytest.approx(1.0 - s)
    assert notes[0]["onset_sec"] > 0.0
    merged, _ = merge_coincident_onsets(onsets, COINCIDENCE_TOL_SEC)
    assert merged.size == 4
    assert audit["grace_onsets_included"] == 2
    assert audit["grace_compressed"] is False


def test_g2_small_gap_compresses_and_keeps_events() -> None:
    notes = [
        {"onset_sec": 0.0, "duration_sec": 0.002, "pitch": 60, "part": "Fl", "is_grace": False},
        {"onset_sec": 0.004, "duration_sec": 0.0, "pitch": 64, "part": "Fl", "is_grace": True},
        {"onset_sec": 0.004, "duration_sec": 0.0, "pitch": 65, "part": "Fl", "is_grace": True},
        {"onset_sec": 0.004, "duration_sec": 0.2, "pitch": 67, "part": "Fl", "is_grace": False},
    ]
    audit = assign_grace_nominal_onsets(notes)
    grace_times = sorted(n["onset_sec"] for n in notes if n.get("is_grace"))
    assert len(grace_times) == 2
    assert all(t > 0.0 for t in grace_times)
    assert all(t < 0.004 for t in grace_times)
    assert audit["grace_onsets_included"] == 2
    assert audit["grace_compressed"] is True
    assert all(n.get("grace_compressed") for n in notes if n.get("is_grace"))


# ---------------------------------------------------------------------------
# Fusion
# ---------------------------------------------------------------------------

def test_f1_same_effective_tolerance_and_adaptive_threshold() -> None:
    nm = _matrix_from_onsets([i * 0.050 for i in range(8)], part="Slow")
    nm += _matrix_from_onsets([i * 0.030 for i in range(8)], part="Fast")

    layers = onsets_per_layer_from_note_matrix(nm)
    tol_metrics = effective_coincidence_tol_sec(layers.values())
    g = granularity_metrics(nm)
    assert g["coincidence_tol_sec_effective"] == pytest.approx(tol_metrics)

    must_layers_ms = onsets_per_layer_ms_from_note_matrix(nm)
    from granular_v2.mustextu.horizontal_density import _effective_coincidence_ms

    tol_must_s = _effective_coincidence_ms(
        list(must_layers_ms.values()), 2.0, 0.05, True
    ) / 1000.0
    assert tol_must_s == pytest.approx(tol_metrics)
    assert min(float(np.median(np.diff(ts))) for ts in layers.values()) == pytest.approx(0.030)
    assert tol_metrics == pytest.approx(0.05 * 0.030)

    slow_only = onsets_per_layer_from_note_matrix(
        _matrix_from_onsets([i * 0.050 for i in range(8)], part="Slow")
    )
    tol_slow = effective_coincidence_tol_sec(slow_only.values())
    assert min(float(np.median(np.diff(ts))) for ts in slow_only.values()) == pytest.approx(0.050)
    assert tol_slow == pytest.approx(COINCIDENCE_TOL_SEC)


# ---------------------------------------------------------------------------
# Remove GI
# ---------------------------------------------------------------------------

def test_r1_no_granularity_index_in_exports_gui_or_live_docs() -> None:
    g = global_event_rates(_matrix_from_onsets([0.0, 0.5, 1.0]))
    assert "granularity_index" not in g
    assert "granularity_index_raw" not in g
    assert "granularity_index" not in (g.get("definition") or {})

    skip_dirs = {".git", "__pycache__", "docs/audit"}
    skip_names = {
        "CHANGELOG.md",
        "VD4_VD10_CONFORMANCE_2026-09-18.md",
        "_before_vd4_vd10.json",
        "test_vd4_vd10_conformance.py",
    }
    hits = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs or str(path.as_posix()).find("docs/audit") >= 0 for part in path.parts):
            continue
        if path.name in skip_names:
            continue
        if path.suffix.lower() not in {".py", ".md", ".html", ".js", ".css"}:
            continue
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "granularity_index" in text:
            hits.append(str(path.relative_to(ROOT)))
    assert hits == [], f"granularity_index still mentioned in {hits}"


# ---------------------------------------------------------------------------
# VD10
# ---------------------------------------------------------------------------

def test_v1_monody_c4_to_d4() -> None:
    notes = [
        {"onset_sec": 0.0, "duration_sec": 0.4, "pitch": 60, "part": "vl", "is_grace": False},
        {"onset_sec": 1.0, "duration_sec": 0.4, "pitch": 62, "part": "vl", "is_grace": False},
    ]
    samples = auto_pick_samples_for_part(notes)
    assert [s["high"] - s["low"] for s in samples] == [0.0, 0.0]
    assert [s["low"] for s in samples] == [60.0, 62.0]
    assert [s["high"] for s in samples] == [60.0, 62.0]
    vd10 = compute_vd10(samples)
    assert vd10["samples"][0]["centre"] == pytest.approx(60.0)
    assert vd10["samples"][1]["centre"] == pytest.approx(62.0)
    assert vd10["aggregates"]["net_displacement"] == pytest.approx(2.0)


def test_v2_c4_then_b3_cs4_net_zero() -> None:
    notes = [
        {"onset_sec": 0.0, "duration_sec": 0.4, "pitch": 60, "part": "vl", "is_grace": False},
        {"onset_sec": 1.0, "duration_sec": 0.4, "pitch": 59, "part": "vl", "is_grace": False},
        {"onset_sec": 1.0, "duration_sec": 0.4, "pitch": 61, "part": "vl", "is_grace": False},
    ]
    samples = auto_pick_samples_for_part(notes)
    vd10 = compute_vd10(samples)
    assert vd10["aggregates"]["net_displacement"] == pytest.approx(0.0)


def test_v3_pedal_under_rising_line() -> None:
    notes = [
        {"onset_sec": 0.0, "duration_sec": 4.0, "pitch": 36, "part": "pno", "is_grace": False},
        {"onset_sec": 0.0, "duration_sec": 0.8, "pitch": 60, "part": "pno", "is_grace": False},
        {"onset_sec": 1.0, "duration_sec": 0.8, "pitch": 62, "part": "pno", "is_grace": False},
        {"onset_sec": 2.0, "duration_sec": 0.8, "pitch": 64, "part": "pno", "is_grace": False},
    ]
    samples = auto_pick_samples_for_part(notes)
    assert [s["low"] for s in samples] == [36.0, 36.0, 36.0]
    widths = [s["high"] - s["low"] for s in samples]
    assert widths[0] < widths[1] < widths[2]
    centres = [(s["low"] + s["high"]) / 2.0 for s in samples]
    assert centres[1] - centres[0] == pytest.approx(1.0)
    assert centres[2] - centres[1] == pytest.approx(1.0)
    assert (64 - 60) / 2.0 == pytest.approx(2.0)


def test_grace_notes_are_not_vd10_sample_times() -> None:
    notes = [
        {"onset_sec": 0.95, "duration_sec": 0.0, "pitch": 64, "part": "fl", "is_grace": True},
        {"onset_sec": 1.0, "duration_sec": 0.5, "pitch": 67, "part": "fl", "is_grace": False},
        {"onset_sec": 2.0, "duration_sec": 0.5, "pitch": 69, "part": "fl", "is_grace": False},
    ]
    samples = auto_pick_samples_for_part(notes)
    assert [s["time_s"] for s in samples] == [1.0, 2.0]
