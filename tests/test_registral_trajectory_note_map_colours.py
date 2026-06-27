"""Registral-trajectory note-map overlay colours (display-only, by XML part)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from granular_v2.config import HeatmapConfig
from granular_v2.heatmaps import (
    extract_part_label,
    note_part_overlay_colors,
    part_color_map,
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


def test_extract_part_label_unknown_when_missing() -> None:
    assert extract_part_label({"part": ""}) == "Unknown"
    assert extract_part_label({}) == "Unknown"
    assert extract_part_label({"part": "Flute"}) == "Flute"


def test_plot_heatmap_advanced_creates_separate_part_scatter_groups() -> None:
    note_matrix = _two_part_note_matrix()
    cfg = HeatmapConfig(overlay_points=True, publication_style=False)
    fig = plot_heatmap_advanced(note_matrix, cfg, title="test")
    ax = fig.axes[0]
    scatter_groups = [artist for artist in ax.collections if artist.get_label() in {"Violin", "Cello"}]
    assert len(scatter_groups) == 2
    violin_colors = {tuple(facecolor[:3]) for facecolor in scatter_groups[0].get_facecolors()}
    cello_colors = {tuple(facecolor[:3]) for facecolor in scatter_groups[1].get_facecolors()}
    assert violin_colors.isdisjoint(cello_colors)


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
        (a.get_label(), tuple(a.get_facecolors()[0][:3]))
        for a in fig_a.axes[0].collections
        if a.get_label() in {"Violin", "Cello"}
    )
    artists_b = sorted(
        (a.get_label(), tuple(a.get_facecolors()[0][:3]))
        for a in fig_b.axes[0].collections
        if a.get_label() in {"Violin", "Cello"}
    )
    assert artists_a == artists_b
