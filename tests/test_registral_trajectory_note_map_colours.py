"""Registral-trajectory note-map overlay colours (display-only, by XML part)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from granular_v2.config import HeatmapConfig
from granular_v2.heatmaps import (
    extract_part_label,
    note_part_overlay_colors,
    part_color_map,
    part_note_sequences,
    plot_heatmap_advanced,
)


def _two_part_note_matrix() -> list[dict]:
    return [
        {"onset_sec": 0.0, "duration_sec": 0.5, "pitch": 60, "velocity": 80, "part": "Violin"},
        {"onset_sec": 0.25, "duration_sec": 0.5, "pitch": 64, "velocity": 80, "part": "Cello"},
        {"onset_sec": 0.5, "duration_sec": 0.5, "pitch": 67, "velocity": 80, "part": "Violin"},
    ]


def test_part_color_map_is_deterministic() -> None:
    first = part_color_map(["Cello", "Violin", "Violin"])
    second = part_color_map(["Violin", "Cello"])
    assert first == second
    assert first["Violin"] != first["Cello"]


def test_note_part_overlay_colors_group_by_part() -> None:
    note_matrix = _two_part_note_matrix()
    colors = note_part_overlay_colors(note_matrix)
    assert colors[0] == colors[2]
    assert colors[0] != colors[1]
    assert note_part_overlay_colors(note_matrix) == colors


def test_part_note_sequences_sorted_chronologically_within_part() -> None:
    note_matrix = _two_part_note_matrix()
    sequences = part_note_sequences(note_matrix)
    assert sequences["Violin"] == [(0.25, 60.0), (0.75, 67.0)]
    assert sequences["Cello"] == [(0.5, 64.0)]


def test_extract_part_label_unknown_when_missing() -> None:
    assert extract_part_label({"part": ""}) == "Unknown"
    assert extract_part_label({}) == "Unknown"
    assert extract_part_label({"part": "Flute"}) == "Flute"


def test_plot_heatmap_advanced_draws_connected_part_lines() -> None:
    note_matrix = _two_part_note_matrix()
    cfg = HeatmapConfig(overlay_points=True, publication_style=False)
    fig = plot_heatmap_advanced(note_matrix, cfg, title="test")
    ax = fig.axes[0]
    line_groups = {line.get_label(): line for line in ax.lines if line.get_label() in {"Violin", "Cello"}}
    assert set(line_groups) == {"Violin", "Cello"}
    assert len(line_groups["Violin"].get_xdata()) == 2
    assert len(line_groups["Cello"].get_xdata()) == 1


def test_plot_part_lines_use_distinct_colours() -> None:
    import matplotlib.colors as mcolors

    note_matrix = _two_part_note_matrix()
    cfg = HeatmapConfig(overlay_points=True, publication_style=False)
    fig = plot_heatmap_advanced(note_matrix, cfg, title="test")
    ax = fig.axes[0]
    line_colors = {
        line.get_label(): mcolors.to_rgb(line.get_color())
        for line in ax.lines
        if line.get_label() in {"Violin", "Cello"}
    }
    assert line_colors["Violin"] != line_colors["Cello"]


def test_plot_heatmap_advanced_legend_lists_parts() -> None:
    note_matrix = _two_part_note_matrix()
    cfg = HeatmapConfig(overlay_points=True, publication_style=False)
    fig = plot_heatmap_advanced(note_matrix, cfg, title="test")
    legend = fig.axes[0].get_legend()
    assert legend is not None
    labels = {text.get_text() for text in legend.get_texts()}
    assert labels == {"Violin", "Cello"}


def test_plot_overlay_colours_repeat_across_calls() -> None:
    note_matrix = _two_part_note_matrix()
    cfg = HeatmapConfig(overlay_points=True, publication_style=False)
    fig_a = plot_heatmap_advanced(note_matrix, cfg, title="a")
    fig_b = plot_heatmap_advanced(note_matrix, cfg, title="b")
    artists_a = sorted(
        (line.get_label(), line.get_color())
        for line in fig_a.axes[0].lines
        if line.get_label() in {"Violin", "Cello"}
    )
    artists_b = sorted(
        (line.get_label(), line.get_color())
        for line in fig_b.axes[0].lines
        if line.get_label() in {"Violin", "Cello"}
    )
    assert artists_a == artists_b
