"""VD10 auto-pick from note matrix (one block per XML part)."""

from __future__ import annotations

import pytest

from granular_v2.trajectory import (
    AUTO_PICK_DENSE_SAMPLE_WARN,
    TrajectoryError,
    auto_pick_blocks_from_note_matrix,
    auto_pick_samples_for_part,
    band_from_pitches,
    compute_vd10,
    compute_vd10_session,
    part_label_from_note,
)


def _note(onset: float, pitch: int, part: str, dur: float = 0.5) -> dict:
    return {
        "onset_sec": onset,
        "duration_sec": dur,
        "pitch": pitch,
        "velocity": 80,
        "part": part,
    }


def test_part_label_from_note_defaults_unknown() -> None:
    assert part_label_from_note({}) == "Unknown"
    assert part_label_from_note({"part": ""}) == "Unknown"
    assert part_label_from_note({"part": "  fl  "}) == "fl"


def test_band_from_pitches_single_note_gets_unit_width() -> None:
    assert band_from_pitches([60]) == (60, 61)


def test_band_from_pitches_chord_uses_span() -> None:
    assert band_from_pitches([60, 64, 67]) == (60, 67)


def test_band_from_pitches_top_pitch_clamped_at_127() -> None:
    assert band_from_pitches([127]) == (127, 127)


def test_band_from_pitches_empty_raises() -> None:
    with pytest.raises(TrajectoryError, match="empty pitch"):
        band_from_pitches([])


def test_auto_pick_samples_merges_chord_at_same_onset() -> None:
    notes = [
        _note(1.0, 60, "vl"),
        _note(1.0, 64, "vl"),
        _note(2.0, 67, "vl"),
    ]
    samples = auto_pick_samples_for_part(notes)
    assert len(samples) == 2
    assert samples[0]["time_s"] == 1.0
    assert samples[0]["low"] == 60.0
    assert samples[0]["high"] == 64.0
    assert samples[1]["low"] == 67.0
    assert samples[1]["high"] == 68.0


def test_auto_pick_samples_sorted_when_notes_unordered() -> None:
    notes = [
        _note(2.0, 67, "vl"),
        _note(0.0, 60, "vl"),
        _note(1.0, 64, "vl"),
    ]
    samples = auto_pick_samples_for_part(notes)
    times = [sample["time_s"] for sample in samples]
    assert times == sorted(times)
    assert times == [0.0, 1.0, 2.0]


def test_auto_pick_samples_produce_strictly_increasing_times() -> None:
    notes = [_note(float(i), 60 + i, "p") for i in range(5)]
    samples = auto_pick_samples_for_part(notes)
    times = [sample["time_s"] for sample in samples]
    assert times == sorted(times)
    assert len(times) == len(set(times))


def test_auto_pick_empty_matrix_returns_empty_stats() -> None:
    result = auto_pick_blocks_from_note_matrix([])
    assert result["blocks"] == []
    assert result["stats"]["num_parts"] == 0
    assert result["stats"]["total_samples"] == 0
    assert result["stats"]["dense_sample_warning"] is False


def test_auto_pick_blocks_one_block_per_part_ordered_by_first_onset() -> None:
    note_matrix = [
        _note(0.0, 60, "ob"),
        _note(0.5, 64, "fl"),
        _note(1.0, 67, "ob"),
    ]
    result = auto_pick_blocks_from_note_matrix(note_matrix)
    blocks = result["blocks"]
    assert [block["name"] for block in blocks] == ["ob", "fl"]
    assert len(blocks[0]["samples"]) == 2
    assert len(blocks[1]["samples"]) == 1
    assert result["stats"]["computable_parts"] == 1
    assert result["stats"]["parts_with_few_samples"] == ["fl"]


def test_auto_pick_unknown_parts_grouped() -> None:
    note_matrix = [
        _note(0.0, 60, ""),
        _note(1.0, 64, ""),
        _note(0.0, 72, "fl"),
        _note(1.0, 76, "fl"),
    ]
    result = auto_pick_blocks_from_note_matrix(note_matrix)
    names = {block["name"] for block in result["blocks"]}
    assert names == {"Unknown", "fl"}
    unknown = next(b for b in result["blocks"] if b["name"] == "Unknown")
    assert len(unknown["samples"]) == 2


def test_auto_pick_block_ids_unique_and_stable() -> None:
    note_matrix = [
        _note(0.0, 60, "fl 1"),
        _note(1.0, 64, "fl 1"),
        _note(0.0, 67, "cl 2"),
        _note(1.0, 69, "cl 2"),
    ]
    first = auto_pick_blocks_from_note_matrix(note_matrix)
    second = auto_pick_blocks_from_note_matrix(note_matrix)
    ids_first = [block["id"] for block in first["blocks"]]
    ids_second = [block["id"] for block in second["blocks"]]
    assert len(ids_first) == len(set(ids_first))
    assert ids_first == ids_second
    assert all(block_id.startswith("block_") for block_id in ids_first)


def test_auto_pick_dense_sample_warning() -> None:
    note_matrix = [
        _note(float(i) * 0.01, 60 + (i % 12), "dense")
        for i in range(AUTO_PICK_DENSE_SAMPLE_WARN + 1)
    ]
    result = auto_pick_blocks_from_note_matrix(note_matrix)
    assert result["stats"]["total_samples"] == AUTO_PICK_DENSE_SAMPLE_WARN + 1
    assert result["stats"]["dense_sample_warning"] is True


def test_auto_pick_blocks_compatible_with_compute_vd10() -> None:
    note_matrix = [
        _note(0.0, 60, "A"),
        _note(1.0, 64, "A"),
        _note(2.0, 67, "A"),
    ]
    picked = auto_pick_blocks_from_note_matrix(note_matrix)
    block = picked["blocks"][0]
    vd10 = compute_vd10(block["samples"])
    assert vd10["metric"] == "VD10"
    assert vd10["aggregates"]["net_displacement"] == pytest.approx(7.0)


def test_auto_pick_session_computes_vd10_for_multi_sample_parts() -> None:
    note_matrix = [
        _note(0.0, 60, "A"),
        _note(1.0, 64, "A"),
        _note(0.0, 72, "B"),
        _note(1.0, 76, "B"),
    ]
    picked = auto_pick_blocks_from_note_matrix(note_matrix)
    session = compute_vd10_session(picked["blocks"])
    assert session["blocks"][0]["vd10"] is not None
    assert session["blocks"][1]["vd10"] is not None
    assert len(session["relations"]["pairs"]) == 1


def test_auto_pick_is_deterministic() -> None:
    note_matrix = [_note(0.0, 60, "x"), _note(0.5, 62, "y"), _note(1.0, 64, "x")]
    first = auto_pick_blocks_from_note_matrix(note_matrix)
    second = auto_pick_blocks_from_note_matrix(note_matrix)
    assert first == second
