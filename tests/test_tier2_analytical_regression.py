"""
Tier-2 analytical/corpus regression — high-level invariants without full snapshots.

Complements corpus/scripts/compare_all.py (locked numeric snapshots) and
tests/test_musicological_regression.py (loader-level structural checks).
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
from music21 import converter, note, stream, tie

from granular_v2.config import AnalysisConfig
from granular_v2.loader import load_score_and_note_matrix
from granular_v2.note_extraction import extract_notes_with_ties
from granular_v2.pipeline import run_analysis
from granular_v2.reports import export_results_json
from granular_v2.trajectory import compute_vd10
from granular_v2.util_tempo import expand_repeats_if_requested

ROOT = Path(__file__).resolve().parents[1]
CORPUS_FIX_DIR = ROOT / "corpus" / "fixtures"
MUSIC_FIX_DIR = ROOT / "corpus" / "fixtures" / "musicological_regression"

CORPUS_NAMES = ("dense_onset_burst", "layered_async", "sparse_homophony")

CORE_RESULT_KEYS = frozenset(
    {
        "num_events",
        "activity_granularity",
        "event_rates",
        "export_metadata",
        "tempo_audit",
    }
)

VD10_DIRECTION_LABELS = frozenset({"ascending", "descending", "static"})
VD10_SHAPE_HINT_LABELS = frozenset({"unidirectional", "undulating", "mixed"})

DEFAULT_CFG = AnalysisConfig(enable_heatmaps=False, enable_mustextu=True)


def _corpus_path(name: str) -> Path:
    path = CORPUS_FIX_DIR / f"{name}.musicxml"
    if not path.exists():
        pytest.skip(f"corpus fixture missing: {path.name}")
    return path


def _musicological_path(name: str) -> Path:
    path = MUSIC_FIX_DIR / f"{name}.musicxml"
    if not path.exists():
        pytest.skip(f"musicological fixture missing: {path.name}")
    return path


def _run_corpus(name: str, *, include_partitional: bool = False) -> dict[str, Any]:
    cfg = AnalysisConfig(
        enable_heatmaps=False,
        enable_mustextu=True,
        include_partitional=include_partitional,
    )
    return run_analysis(_corpus_path(name), cfg, output_dir=None, export_json=False)


def _global_rates(result: dict[str, Any]) -> dict[str, Any]:
    return result["event_rates"]["global"]


def _unique_onsets(note_matrix) -> int:
    return len({round(float(row["onset_sec"]), 4) for row in note_matrix})


def _max_simultaneous(note_matrix) -> int:
    counts: dict[float, int] = defaultdict(int)
    for row in note_matrix:
        counts[round(float(row["onset_sec"]), 4)] += 1
    return max(counts.values()) if counts else 0


def _collect_numeric_leaves(obj: Any, prefix: str = "") -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append((prefix, float(obj)))
        return out
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "definition":
                continue
            child = f"{prefix}.{key}" if prefix else str(key)
            out.extend(_collect_numeric_leaves(value, child))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            child = f"{prefix}[{index}]"
            out.extend(_collect_numeric_leaves(value, child))
    return out


def _assert_warnings_structured(audit: dict[str, Any]) -> None:
    warnings = audit.get("warnings")
    assert isinstance(warnings, list)
    for warning in warnings:
        assert isinstance(warning, dict)
        assert "code" in warning


def _write_two_attack_score(path: Path) -> None:
    part = stream.Part()
    part.append(note.Note("C4", quarterLength=1.0))
    part.append(note.Note("C4", quarterLength=1.0))
    score = stream.Score()
    score.insert(0, part)
    score.write("musicxml", fp=str(path))


def _write_tied_sustain_score(path: Path) -> None:
    part = stream.Part()
    n1 = note.Note("C4", quarterLength=1.0)
    n1.tie = tie.Tie("start")
    n2 = note.Note("C4", quarterLength=1.0)
    n2.tie = tie.Tie("stop")
    part.insert(0, n1)
    part.insert(1, n2)
    score = stream.Score()
    score.insert(0, part)
    score.write("musicxml", fp=str(path))


@pytest.mark.parametrize("name", CORPUS_NAMES)
def test_corpus_result_has_core_sections(name: str) -> None:
    result = _run_corpus(name)
    assert CORE_RESULT_KEYS.issubset(result.keys())
    assert "mustextu_summary" in result
    assert "granularity" in result["activity_granularity"]
    assert "global" in result["event_rates"]


@pytest.mark.parametrize("name", CORPUS_NAMES)
def test_corpus_numeric_summaries_finite(name: str) -> None:
    result = _run_corpus(name)
    for path, value in _collect_numeric_leaves(result):
        assert math.isfinite(value), f"{name}: non-finite at {path} = {value}"


@pytest.mark.parametrize("name", CORPUS_NAMES)
def test_corpus_non_negative_event_counts(name: str) -> None:
    result = _run_corpus(name)
    global_rates = _global_rates(result)
    assert result["num_events"] >= 0
    assert global_rates["num_events"] >= 0
    assert global_rates["num_events_raw"] >= 0
    assert global_rates["events_per_second"] >= 0


@pytest.mark.parametrize("name", CORPUS_NAMES)
def test_corpus_tempo_audit_warnings_structured(name: str) -> None:
    result = _run_corpus(name)
    _assert_warnings_structured(result["tempo_audit"])


def test_dense_higher_activity_rate_than_layered_and_sparse() -> None:
    dense = _global_rates(_run_corpus("dense_onset_burst"))
    layered = _global_rates(_run_corpus("layered_async"))
    sparse = _global_rates(_run_corpus("sparse_homophony"))
    assert dense["events_per_second"] > layered["events_per_second"] > sparse["events_per_second"]
    assert dense["num_events"] > layered["num_events"] > sparse["num_events"]


def test_layered_async_higher_onset_dispersion_than_sparse_homophony() -> None:
    _, layered_nm, _ = load_score_and_note_matrix(_corpus_path("layered_async"))
    _, sparse_nm, _ = load_score_and_note_matrix(_corpus_path("sparse_homophony"))
    layered = _global_rates(_run_corpus("layered_async"))
    sparse = _global_rates(_run_corpus("sparse_homophony"))
    assert _unique_onsets(layered_nm) > _unique_onsets(sparse_nm)
    assert layered["num_events"] > sparse["num_events"]
    assert layered["ioi_cv"] > sparse["ioi_cv"]


def test_layered_async_not_collapsed_to_homorhythmic_block() -> None:
    _, note_matrix, _ = load_score_and_note_matrix(_corpus_path("layered_async"))
    assert _max_simultaneous(note_matrix) == 1
    assert _unique_onsets(note_matrix) == len(note_matrix)


def test_layered_async_partitional_state_non_trivial() -> None:
    result = _run_corpus("layered_async", include_partitional=True)
    partitional = result.get("partitional") or {}
    assert partitional
    band = partitional.get("0.5") or next(iter(partitional.values()))
    assert max(band["n"]) >= 2
    assert max(band["agglomeration"]) > 0


def test_layered_async_distinguishable_from_sparse_homophony() -> None:
    layered = _global_rates(_run_corpus("layered_async"))
    sparse = _global_rates(_run_corpus("sparse_homophony"))
    assert layered["num_events_raw"] > sparse["num_events_raw"]
    assert layered["events_per_second"] > sparse["events_per_second"]
    assert sparse["num_events"] < sparse["num_events_raw"]


def test_tied_texture_merged_reduces_fused_onset_activity() -> None:
    path = _musicological_path("tied_sustained_texture")
    cfg_merged = AnalysisConfig(enable_heatmaps=False, enable_mustextu=True, merge_ties=True)
    cfg_raw = AnalysisConfig(enable_heatmaps=False, enable_mustextu=True, merge_ties=False)
    merged = _global_rates(run_analysis(path, cfg_merged, output_dir=None, export_json=False))
    raw = _global_rates(run_analysis(path, cfg_raw, output_dir=None, export_json=False))
    assert merged["num_events"] < raw["num_events"]


def test_new_attacks_increase_onset_activity_synthetic(tmp_path: Path) -> None:
    one_attack = tmp_path / "one_attack.musicxml"
    two_attacks = tmp_path / "two_attacks.musicxml"
    _write_tied_sustain_score(one_attack)
    _write_two_attack_score(two_attacks)
    cfg = AnalysisConfig(enable_heatmaps=False, enable_mustextu=False, merge_ties=True)
    single = _global_rates(run_analysis(one_attack, cfg, output_dir=None, export_json=False))
    repeated = _global_rates(run_analysis(two_attacks, cfg, output_dir=None, export_json=False))
    assert repeated["num_events"] > single["num_events"]
    assert repeated["events_per_second"] > single["events_per_second"]


def test_sustained_vs_repeated_attacks_distinguishable(tmp_path: Path) -> None:
    tied_path = tmp_path / "tied.musicxml"
    repeated_path = tmp_path / "repeated.musicxml"
    _write_tied_sustain_score(tied_path)
    _write_two_attack_score(repeated_path)
    cfg = AnalysisConfig(enable_heatmaps=False, enable_mustextu=False, merge_ties=True)
    tied = _global_rates(run_analysis(tied_path, cfg, output_dir=None, export_json=False))
    repeated = _global_rates(run_analysis(repeated_path, cfg, output_dir=None, export_json=False))
    assert tied["num_events"] == 1
    assert repeated["num_events"] == 2


def test_repeated_section_expansion_analytical_invariants(tmp_path: Path) -> None:
    path = _musicological_path("repeated_section")
    score = converter.parse(str(path))
    before = len(extract_notes_with_ties(score, merge_ties=True))
    expanded = expand_repeats_if_requested(score, True)
    after = len(extract_notes_with_ties(expanded, merge_ties=True))
    assert after > before

    expanded_path = tmp_path / "expanded.musicxml"
    expanded.write("musicxml", fp=str(expanded_path))
    _, note_matrix, _ = load_score_and_note_matrix(expanded_path, merge_ties=True)
    onsets = [float(row["onset_sec"]) for row in note_matrix]
    assert onsets == sorted(onsets)

    baseline = run_analysis(path, DEFAULT_CFG, output_dir=None, export_json=False)
    expanded_result = run_analysis(expanded_path, DEFAULT_CFG, output_dir=None, export_json=False)
    assert expanded_result["num_events"] > baseline["num_events"]
    assert _global_rates(expanded_result)["num_events"] >= before


def test_vd10_outputs_finite_with_documented_labels() -> None:
    result = compute_vd10(
        [
            {"time_s": 0.0, "low": 72, "high": 76},
            {"time_s": 2.0, "low": 60, "high": 64},
        ]
    )
    aggregates = result["aggregates"]
    labels = result["labels"]
    assert -1.0 <= aggregates["straightness"] <= 1.0
    assert labels["direction"] in VD10_DIRECTION_LABELS
    assert labels["shape_hint"] in VD10_SHAPE_HINT_LABELS
    assert math.isfinite(aggregates["net_speed"])
    assert math.isfinite(aggregates["total_path"])
    assert labels["shape_hint"] == "unidirectional"


def test_export_json_core_fields_and_serialisable(tmp_path: Path) -> None:
    result = _run_corpus("sparse_homophony")
    out_path = tmp_path / "analysis.json"
    export_results_json(result, out_path)
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    for key in CORE_RESULT_KEYS:
        assert key in loaded
    json.dumps(loaded)
    for path, value in _collect_numeric_leaves(loaded):
        assert math.isfinite(value), f"non-finite export value at {path}"
