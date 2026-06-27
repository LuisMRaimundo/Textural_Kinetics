"""Focused tests for audit.merge_audits warning and metadata merge semantics."""

from __future__ import annotations

import json
from typing import Any

import pytest

from granular_v2.audit import append_warning, merge_audits


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _tempo_audit(
    *,
    source: str = "timebase_segments",
    n_segments: int = 1,
    warnings: list[dict[str, str]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    audit: dict[str, Any] = {
        "tempo_fallback_used": n_segments <= 1,
        "n_tempo_segments": n_segments,
        "reason": None,
        "source": source,
        "default_bpm": 120.0,
        "tempo_model": "stepwise_plateau",
        "warnings": list(warnings or []),
    }
    audit.update(extra)
    return audit


# --- 1. Empty and missing inputs ---


def test_merge_audits_no_arguments_returns_empty_dict() -> None:
    assert merge_audits() == {}


def test_merge_audits_skips_empty_dicts() -> None:
    assert merge_audits({}, {}) == {}
    assert merge_audits({"source": "midi_seconds"}, {}) == {"source": "midi_seconds"}


def test_merge_audits_skips_none_like_falsy_entries() -> None:
    assert merge_audits(None) == {}  # type: ignore[arg-type]
    assert merge_audits({"source": "a"}, None, {"tempo_model": "stepwise_plateau"}) == {  # type: ignore[arg-type]
        "source": "a",
        "tempo_model": "stepwise_plateau",
    }


def test_merge_audits_single_audit_without_warnings_omits_warnings_key() -> None:
    audit = {"source": "timebase_segments", "n_tempo_segments": 2}
    assert merge_audits(audit) == audit
    assert "warnings" not in merge_audits(audit)


# --- 2. Warning merge behaviour ---


def test_merge_audits_concatenates_warnings_in_input_order() -> None:
    first = _tempo_audit(warnings=[_warning("code_a", "first")])
    second = _tempo_audit(warnings=[_warning("code_b", "second")])
    merged = merge_audits(first, second)
    assert merged["warnings"] == [
        _warning("code_a", "first"),
        _warning("code_b", "second"),
    ]


def test_merge_audits_preserves_duplicate_warnings() -> None:
    dup = _warning("repeat", "same message")
    first = _tempo_audit(warnings=[dup])
    second = _tempo_audit(warnings=[dup])
    merged = merge_audits(first, second)
    assert merged["warnings"] == [dup, dup]


def test_merge_audits_empty_warning_lists_produce_no_warnings_key() -> None:
    merged = merge_audits(_tempo_audit(warnings=[]), _tempo_audit(warnings=[]))
    assert merged == {
        "tempo_fallback_used": True,
        "n_tempo_segments": 1,
        "reason": None,
        "source": "timebase_segments",
        "default_bpm": 120.0,
        "tempo_model": "stepwise_plateau",
    }
    assert "warnings" not in merged


def test_merge_audits_missing_warnings_key_treated_as_empty() -> None:
    no_warnings = {"source": "timebase_segments", "tempo_model": "stepwise_plateau"}
    with_one = _tempo_audit(warnings=[_warning("only", "one")])
    merged = merge_audits(no_warnings, with_one)
    assert merged["warnings"] == [_warning("only", "one")]


def test_merge_audits_three_way_warning_order() -> None:
    audits = [
        _tempo_audit(warnings=[_warning(f"c{i}", f"m{i}")]) for i in range(3)
    ]
    merged = merge_audits(*audits)
    assert [w["code"] for w in merged["warnings"]] == ["c0", "c1", "c2"]


# --- 3. Scalar / metadata merge behaviour ---


def test_merge_audits_later_scalar_values_override_earlier() -> None:
    first = _tempo_audit(source="timebase_segments", n_segments=1, default_bpm=120.0)
    second = _tempo_audit(source="metronomeMarkBoundaries", n_segments=3, default_bpm=96.0)
    merged = merge_audits(first, second)
    assert merged["source"] == "metronomeMarkBoundaries"
    assert merged["n_tempo_segments"] == 3
    assert merged["default_bpm"] == 96.0


def test_merge_audits_unrelated_keys_from_earlier_audit_persist() -> None:
    first = _tempo_audit(reason="uniform segment map", tempo_fallback_used=True)
    second = {"source": "midi_seconds", "warnings": []}
    merged = merge_audits(first, second)
    assert merged["source"] == "midi_seconds"
    assert merged["reason"] == "uniform segment map"
    assert merged["tempo_fallback_used"] is True
    assert merged["tempo_model"] == "stepwise_plateau"


def test_merge_audits_boolean_and_numeric_fields_preserved() -> None:
    first = {"tempo_fallback_used": False, "note_count": 42, "warnings": []}
    second = {"pitch_domain": "written", "merge_ties": True, "warnings": []}
    merged = merge_audits(first, second)
    assert merged["tempo_fallback_used"] is False
    assert merged["note_count"] == 42
    assert merged["pitch_domain"] == "written"
    assert merged["merge_ties"] is True


def test_merge_audits_string_metadata_override() -> None:
    merged = merge_audits(
        {"source": "a", "reason": "first", "warnings": []},
        {"source": "b", "reason": "second", "warnings": []},
    )
    assert merged["source"] == "b"
    assert merged["reason"] == "second"


# --- 4. Nested dictionary behaviour (shallow replace) ---


def test_merge_audits_nested_dict_later_value_replaces_entire_nested_dict() -> None:
    first = {"meta": {"a": 1, "b": 2}, "warnings": []}
    second = {"meta": {"b": 99, "c": 3}, "warnings": []}
    merged = merge_audits(first, second)
    assert merged["meta"] == {"b": 99, "c": 3}


def test_merge_audits_nested_dict_from_earlier_audit_persists_if_not_overwritten() -> None:
    first = {"extra": {"nested": True}, "warnings": []}
    second = {"source": "timebase_segments", "warnings": []}
    merged = merge_audits(first, second)
    assert merged["extra"] == {"nested": True}
    assert merged["source"] == "timebase_segments"


# --- 5. Type robustness ---


def test_merge_audits_non_list_warnings_are_not_concatenated() -> None:
    """Non-list warnings are skipped for concatenation (current implementation)."""
    first = {"source": "a", "warnings": "not-a-list"}
    second = _tempo_audit(warnings=[_warning("ok", "list warning")])
    merged = merge_audits(first, second)
    assert merged["warnings"] == [_warning("ok", "list warning")]
    assert merged["source"] == "timebase_segments"


def test_merge_audits_dict_warnings_are_not_concatenated() -> None:
    first = {"warnings": {"code": "bad", "message": "shape"}}
    second = _tempo_audit(warnings=[_warning("good", "list")])
    merged = merge_audits(first, second)
    assert merged["warnings"] == [_warning("good", "list")]


def test_merge_audits_mixed_realistic_fields_with_append_warning_output() -> None:
    audit_a: dict[str, Any] = {"source": "timebase_segments", "n_tempo_segments": 2}
    append_warning(audit_a, "timebase_segments_failed", "simulated failure")
    audit_b: dict[str, Any] = {
        "source": "metronomeMarkBoundaries",
        "tempo_fallback_used": True,
        "warnings": [],
    }
    append_warning(audit_b, "metronome_boundaries_failed", "fallback path")
    merged = merge_audits(audit_a, audit_b)
    assert merged["source"] == "metronomeMarkBoundaries"
    assert merged["n_tempo_segments"] == 2
    assert [w["code"] for w in merged["warnings"]] == [
        "timebase_segments_failed",
        "metronome_boundaries_failed",
    ]


# --- 6. Integration smoke ---


def test_merge_audits_loader_shaped_tempo_audits(sample_musicxml) -> None:
    from granular_v2.loader import load_score_and_note_matrix

    _, _, audit_xml = load_score_and_note_matrix(sample_musicxml, merge_ties=True)
    synthetic = _tempo_audit(
        source="synthetic_overlay",
        warnings=[_warning("overlay", "constructed for merge smoke test")],
    )
    merged = merge_audits(audit_xml, synthetic)
    assert isinstance(merged.get("warnings"), list)
    assert merged.get("source") == "synthetic_overlay"
    assert merged.get("tempo_model") == "stepwise_plateau"
    assert any(w.get("code") for w in merged["warnings"])


def test_merge_audits_two_loader_audits_remain_list_like(sample_musicxml, monkeypatch) -> None:
    import granular_v2.loader as loader_mod
    from granular_v2.loader import load_score_and_note_matrix

    real_bts = loader_mod.build_tempo_segments
    calls = {"n": 0}

    def _raise_first(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated build_tempo_segments failure")
        return real_bts(*args, **kwargs)

    monkeypatch.setattr(loader_mod, "build_tempo_segments", _raise_first)

    _, _, fallback_audit = load_score_and_note_matrix(sample_musicxml, merge_ties=True)
    _, _, primary_audit = load_score_and_note_matrix(sample_musicxml, merge_ties=True)

    merged = merge_audits(primary_audit, fallback_audit)
    warnings = merged.get("warnings")
    assert isinstance(warnings, list)
    assert all(isinstance(w, dict) for w in warnings)
    assert merged.get("source") == fallback_audit.get("source")


# --- 7. JSON serialisability ---


@pytest.mark.parametrize(
    "audits",
    [
        (),
        (_tempo_audit(),),
        (
            _tempo_audit(warnings=[_warning("a", "one")]),
            _tempo_audit(source="midi_seconds", warnings=[_warning("b", "two")]),
        ),
        (
            {"tempo_fallback_used": True, "nested": {"x": 1}, "warnings": []},
            {"note_count": 10, "warnings": [_warning("c", "three")]},
        ),
    ],
)
def test_merge_audits_result_is_json_serialisable(audits: tuple[dict[str, Any], ...]) -> None:
    merged = merge_audits(*audits)
    payload = json.dumps(merged)
    roundtrip = json.loads(payload)
    assert roundtrip == merged
