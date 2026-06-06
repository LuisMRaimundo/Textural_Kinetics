"""
Qualitative invariants for musicological regression fixtures (phase 1).

No locked golden metrics — structural checks only.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest
from music21 import converter

from granular_v2.config import AnalysisConfig
from granular_v2.loader import load_score_and_note_matrix
from granular_v2.note_extraction import extract_notes_with_ties
from granular_v2.onset_extraction import extract_onsets_per_layer_ms_from_score
from granular_v2.pipeline import run_analysis
from granular_v2.util_tempo import expand_repeats_if_requested

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "corpus" / "fixtures" / "musicological_regression"


def _fixture(name: str) -> Path:
    path = FIXTURE_DIR / f"{name}.musicxml"
    if not path.exists():
        pytest.skip(f"fixture missing: {path.name} — run create_musicological_regression_fixtures.py")
    return path


def _max_simultaneous_pitches(note_matrix) -> int:
    counts: dict[float, int] = defaultdict(int)
    for row in note_matrix:
        counts[round(float(row["onset_sec"]), 4)] += 1
    return max(counts.values()) if counts else 0


def _unique_onsets(note_matrix) -> int:
    return len({round(float(row["onset_sec"]), 4) for row in note_matrix})


def _mustextu_sync(fixture_name: str) -> float:
    cfg = AnalysisConfig(enable_heatmaps=False, enable_mustextu=True)
    result = run_analysis(_fixture(fixture_name), cfg, output_dir=None, export_json=False)
    summary = result.get("mustextu_summary") or {}
    return float(summary.get("synchrony_fraction", 0.0))


@pytest.mark.parametrize("name", [
    "regular_homorhythm",
    "tied_sustained_texture",
    "dense_chordal_blocks",
    "layered_async",
    "tempo_change_mid_score",
    "repeated_section",
    "grace_note_passage",
    "transposing_instrument_score",
    "multi_voice_polyphony",
    "empty_or_degenerate_score",
])
def test_fixture_loads_without_crash(name: str):
    path = _fixture(name)
    score, note_matrix, audit = load_score_and_note_matrix(path)
    assert score is not None
    assert isinstance(note_matrix, list)
    assert isinstance(audit, dict)


def test_empty_fixture_returns_empty_matrix():
    _, note_matrix, _ = load_score_and_note_matrix(_fixture("empty_or_degenerate_score"))
    assert note_matrix == []


@pytest.mark.parametrize("name", [
    "regular_homorhythm",
    "dense_chordal_blocks",
    "multi_voice_polyphony",
])
def test_non_negative_onsets_and_positive_durations(name: str):
    _, note_matrix, _ = load_score_and_note_matrix(_fixture(name))
    assert note_matrix, f"{name} expected note events"
    for row in note_matrix:
        onset = float(row["onset_sec"])
        duration = float(row["duration_sec"])
        end = onset + duration
        assert onset >= 0.0
        assert duration > 0.0
        assert end >= onset


def test_tied_texture_merged_has_fewer_onsets_than_raw():
    path = _fixture("tied_sustained_texture")
    _, merged, _ = load_score_and_note_matrix(path, merge_ties=True)
    _, raw, _ = load_score_and_note_matrix(path, merge_ties=False)
    assert _unique_onsets(merged) < _unique_onsets(raw)
    assert len(merged) < len(raw)


def test_dense_chordal_blocks_more_simultaneous_pitches_than_homorhythm():
    _, homo, _ = load_score_and_note_matrix(_fixture("regular_homorhythm"))
    _, dense, _ = load_score_and_note_matrix(_fixture("dense_chordal_blocks"))
    assert _max_simultaneous_pitches(dense) > _max_simultaneous_pitches(homo)


def test_homorhythm_higher_synchrony_than_layered_async():
    homo_sync = _mustextu_sync("regular_homorhythm")
    layered_sync = _mustextu_sync("layered_async")
    assert homo_sync > layered_sync


def test_grace_note_passage_respects_ignore_grace_flag():
    score = converter.parse(str(_fixture("grace_note_passage")))
    ignore_layers, _, _, _ = extract_onsets_per_layer_ms_from_score(score, ignore_grace=True)
    include_layers, _, _, _ = extract_onsets_per_layer_ms_from_score(score, ignore_grace=False)
    ignore_count = sum(len(v) for v in ignore_layers.values())
    include_count = sum(len(v) for v in include_layers.values())
    assert include_count > ignore_count


def test_transposing_instrument_same_timing_different_pitch():
    path = _fixture("transposing_instrument_score")
    _, written, _ = load_score_and_note_matrix(path, pitch_domain="written")
    _, sounding, _ = load_score_and_note_matrix(path, pitch_domain="sounding")
    assert len(written) == len(sounding)
    written_onsets = [float(n["onset_sec"]) for n in written]
    sounding_onsets = [float(n["onset_sec"]) for n in sounding]
    assert written_onsets == pytest.approx(sounding_onsets)
    written_pitches = [int(n["pitch"]) for n in written]
    sounding_pitches = [int(n["pitch"]) for n in sounding]
    assert written_pitches != sounding_pitches
    assert written_pitches == [60, 64, 67]
    assert sounding_pitches == [58, 62, 65]


def test_multi_voice_polyphony_preserves_both_voices():
    _, note_matrix, _ = load_score_and_note_matrix(_fixture("multi_voice_polyphony"))
    assert len(note_matrix) >= 4
    pitches = {int(n["pitch"]) for n in note_matrix}
    assert 60 in pitches
    assert 67 in pitches
    onsets = sorted({round(float(n["onset_sec"]), 3) for n in note_matrix})
    assert len(onsets) >= 4


def test_tempo_change_alters_onset_sec_spacing():
    _, note_matrix, audit = load_score_and_note_matrix(_fixture("tempo_change_mid_score"))
    assert int(audit.get("n_tempo_segments", 0)) >= 2
    onsets = sorted({round(float(n["onset_sec"]), 3) for n in note_matrix})
    iois = [round(onsets[i + 1] - onsets[i], 3) for i in range(len(onsets) - 1)]
    assert any(ioi >= 0.9 for ioi in iois[:8])
    assert any(ioi <= 0.6 for ioi in iois[8:])


def test_repeated_section_expands_when_enabled():
    score = converter.parse(str(_fixture("repeated_section")))
    before = len(extract_notes_with_ties(score, merge_ties=True))
    expanded = expand_repeats_if_requested(score, True)
    after = len(extract_notes_with_ties(expanded, merge_ties=True))
    assert after > before
