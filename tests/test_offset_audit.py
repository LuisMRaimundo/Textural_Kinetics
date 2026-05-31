"""
Offset audit: corpus invariants + forbidden measure-local patterns in core paths.

See docs/OFFSET_AUDIT.md for the module manifest.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from granular_v2.loader import load_score_and_note_matrix
from granular_v2.onset_extraction import extract_onsets_per_layer_ms_from_score
from granular_v2.pipeline import run_analysis
from granular_v2.config import AnalysisConfig

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "fixtures"
CORE_PKG = ROOT / "granular_v2"

# Modules that must not read el.offset / mm.offset for timeline (use offsets.global_ql)
AUDITED_MODULES = [
    "timebase.py",
    "note_extraction.py",
    "onset_extraction.py",
    "loader.py",
]

FORBIDDEN_PATTERNS = [
    re.compile(r"\bel\.offset\b"),
    re.compile(r"\bmm\.offset\b"),
    re.compile(r"\bn\.offset\b"),
    re.compile(r"\belem\.offset\b"),
    re.compile(r"float\(\s*el\.offset"),
]


def _timeline_span_sec(note_matrix) -> float:
    onsets = [float(n["onset_sec"]) for n in note_matrix]
    if len(onsets) < 2:
        return 0.0
    return max(onsets) - min(onsets)


def _n_measures(score) -> int:
    if not getattr(score, "parts", None):
        return 0
    from music21 import stream

    return len(list(score.parts[0].getElementsByClass(stream.Measure)))


@pytest.mark.parametrize("fixture", sorted(CORPUS.glob("*.musicxml")), ids=lambda p: p.stem)
def test_corpus_timeline_not_collapsed(fixture: Path):
    """Multi-measure exports must span more than a single measure-local compression."""
    score, nm, audit = load_score_and_note_matrix(fixture)
    span = _timeline_span_sec(nm)
    n_meas = _n_measures(score)
    assert audit.get("source") in (
        "timebase_segments",
        "metronomeMarkBoundaries",
        "global_bpm_fallback",
        "midi_seconds",
    )
    if n_meas >= 2 and len(nm) >= 4:
        assert span > 1.5, (
            f"{fixture.name}: span={span:.3f}s with {n_meas} measures "
            f"suggests measure-local offset collapse"
        )


@pytest.mark.parametrize("fixture", sorted(CORPUS.glob("*.musicxml")), ids=lambda p: p.stem)
def test_mustextu_onsets_align_with_loader(fixture: Path):
    """Mustextu path uses same global-offset policy as note matrix."""
    score, nm, _ = load_score_and_note_matrix(fixture)
    onsets_nm = sorted({round(float(n["onset_sec"]), 4) for n in nm})
    layers, _, _, _ = extract_onsets_per_layer_ms_from_score(score)
    onsets_mx = sorted(
        {round(t / 1000.0, 4) for times in layers.values() for t in times}
    )
    if not onsets_nm or not onsets_mx:
        pytest.skip("empty onset set")
    # Layer onsets are a subset of note onsets (ms conversion, grace may differ slightly)
    for t in onsets_mx[: min(5, len(onsets_mx))]:
        assert any(abs(t - u) < 0.05 for u in onsets_nm), f"Mustextu onset {t} not near note matrix"


def test_core_modules_avoid_raw_element_offset():
    """Static guard: core timeline modules must not use bare element.offset."""
    violations = []
    for name in AUDITED_MODULES:
        path = CORE_PKG / name
        text = path.read_text(encoding="utf-8")
        for pat in FORBIDDEN_PATTERNS:
            if pat.search(text):
                violations.append(f"{name}: {pat.pattern}")
    assert not violations, "Use granular_v2.offsets.global_ql / global_offset:\n" + "\n".join(violations)


def test_export_includes_tempo_model_and_warnings_key():
    fx = CORPUS / "sparse_homophony.musicxml"
    if not fx.exists():
        pytest.skip("fixture missing")
    r = run_analysis(fx, AnalysisConfig(enable_heatmaps=False), output_dir=None, export_json=False)
    audit = r.get("tempo_audit") or {}
    assert audit.get("tempo_model") == "stepwise_plateau"
    assert "warnings" in audit
