"""
Unified pitch–time heatmaps for Granular_v2.

Two complementary views (both kept, improved):

1. **Activity heatmap** (from Densidade horizontal_v3)
   - Basic: log-scaled bin counts, time × MIDI pitch.
   - Advanced: Gaussian smoothing, gamma, row percentile, note-name axis, optional ms/cs.

2. **Spectral energy heatmap** (from Granularidade, improved)
   - Velocity-weighted density on a regular grid, Gaussian smooth, contours,
     measure lines and peak markers — always in **seconds** when using note_matrix.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from .config import HeatmapConfig
from .exceptions import VisualizationError
from .note_types import NoteMatrix

log = logging.getLogger(__name__)

_MIDI_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi_to_note_name(midi: float) -> str:
    try:
        from music21 import pitch

        return pitch.Pitch(midi=int(round(midi))).nameWithOctave
    except Exception:
        m = int(round(np.clip(midi, 0, 127)))
        return f"{_MIDI_NAMES[m % 12]}{m // 12 - 1}"


def _time_scale(t_axis: np.ndarray, units: str) -> Tuple[np.ndarray, str]:
    if units == "ms":
        return t_axis * 1000.0, "Time (ms)"
    if units == "cs":
        return t_axis * 100.0, "Time (centiseconds)"
    return t_axis, "Time (s)"


def build_pitch_time_matrix(
    note_matrix: NoteMatrix,
    *,
    bin_sec: float = 0.05,
    pitch_step_semitones: float = 0.5,
    mode: str = "occupancy",
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build H[pitch_row, time_col] from note_matrix (onset_sec, duration_sec, pitch, velocity).

    mode:
      - occupancy: each bin overlapped by a note gets +1 (or +velocity weight if velocity mode)
      - onsets: only onset bin
      - velocity: occupancy weighted by velocity/127
    """
    if not note_matrix:
        return np.zeros((1, 1), dtype=np.float32), np.array([0.0]), np.array([0.0])

    onsets = [float(n.get("onset_sec", n.get("onset_beats", 0))) for n in note_matrix]
    ends = [
        onsets[i] + float(note_matrix[i].get("duration_sec", note_matrix[i].get("duration_beats", 0)))
        for i in range(len(note_matrix))
    ]
    pitches = [float(n.get("pitch", 60)) for n in note_matrix]
    t_max = max(ends) if ends else 1.0
    p_min, p_max = min(pitches), max(pitches)
    pad = max(pitch_step_semitones, 0.5)
    p_min -= pad
    p_max += pad

    n_cols = max(1, int(np.ceil(t_max / bin_sec)))
    n_rows = max(1, int(np.ceil((p_max - p_min) / pitch_step_semitones)) + 1)
    H = np.zeros((n_rows, n_cols), dtype=np.float32)

    def row_idx(p: float) -> int:
        return int(np.clip(np.floor((p - p_min) / pitch_step_semitones), 0, n_rows - 1))

    use_velocity = mode == "velocity"

    for n in note_matrix:
        onset = float(n.get("onset_sec", n.get("onset_beats", 0)))
        dur = float(n.get("duration_sec", n.get("duration_beats", 0)))
        end = onset + dur
        p = float(n.get("pitch", 60))
        r = row_idx(p)
        w = 1.0
        if use_velocity:
            w = float(n.get("velocity", 64)) / 127.0
        j0 = int(onset / bin_sec)
        if mode == "onsets":
            if 0 <= j0 < n_cols:
                H[r, j0] += w
        else:
            j1 = min(n_cols - 1, int(max(end - 1e-9, onset) / bin_sec))
            j0 = max(0, j0)
            if j0 <= j1:
                H[r, j0 : j1 + 1] += w

    t_axis = (np.arange(n_cols, dtype=float) + 0.5) * bin_sec
    p_axis = p_min + np.arange(n_rows, dtype=float) * pitch_step_semitones
    return H, t_axis, p_axis


def preprocess_heatmap(
    H: np.ndarray,
    cfg: HeatmapConfig,
) -> np.ndarray:
    """Smoothing, log1p, row norm, percentile, gamma (advanced path)."""
    X = H.astype(np.float32, copy=True)
    if cfg.normalize_rows:
        row_max = X.max(axis=1, keepdims=True)
        row_max[row_max == 0.0] = 1.0
        X = X / row_max

    st, sp = cfg.smooth_t_bins, cfg.smooth_p_bins
    if (st and st > 0) or (sp and sp > 0):
        try:
            from scipy.ndimage import gaussian_filter

            X = gaussian_filter(X, sigma=[float(sp or 0), float(st or 0)], mode="nearest")
        except ImportError:
            if st > 0:
                k = max(1, int(round(st)))
                if k > 1:
                    ker = np.ones(k, dtype=np.float32) / float(k)
                    X = np.apply_along_axis(lambda v: np.convolve(v, ker, mode="same"), 1, X)
            if sp > 0:
                k = max(1, int(round(sp)))
                if k > 1:
                    ker = np.ones(k, dtype=np.float32) / float(k)
                    X = np.apply_along_axis(lambda v: np.convolve(v, ker, mode="same"), 0, X)

    if cfg.log1p:
        X = np.log1p(X)
    if cfg.rowwise_percentile is not None:
        pr = np.percentile(X, float(cfg.rowwise_percentile), axis=1, keepdims=True)
        pr[pr == 0] = 1.0
        X = X / pr
    if cfg.gamma and cfg.gamma != 1.0:
        m = float(X.max())
        if m > 0:
            X = np.power(X / m, float(cfg.gamma)) * m
    return X


def measure_starts_sec(note_matrix: NoteMatrix) -> List[float]:
    """Unique measure onset times (seconds) if rows carry measure_number + measure_start_sec."""
    seen: Dict[int, float] = {}
    for n in note_matrix:
        mn = n.get("measure_number")
        ms = n.get("measure_start_sec")
        if mn is not None and ms is not None:
            seen[int(mn)] = float(ms)
    return sorted(seen.values())


def extract_measure_starts_from_score(score) -> List[float]:
    """Measure boundary times in seconds (first part)."""
    try:
        from .timebase import build_tempo_segments, ql_to_seconds_fn

        segs = build_tempo_segments(score)
        ql_to_sec = ql_to_seconds_fn(segs)
    except Exception:
        bpm = 120.0
        ql_to_sec = lambda q: float(q) * 60.0 / bpm

    starts: List[float] = []
    parts = list(getattr(score, "parts", []) or [])
    if not parts:
        return starts
    part = parts[0]
    from music21 import stream

    for m in part.getElementsByClass(stream.Measure):
        q = float(getattr(m, "offset", 0.0) or 0.0)
        starts.append(ql_to_sec(q))
    return sorted(set(starts))


def build_spectral_energy_matrix(
    note_matrix: NoteMatrix,
    resolution: Tuple[int, int],
    smoothing: float,
) -> Tuple[np.ndarray, Tuple[float, float], Tuple[float, float]]:
    """
    Velocity-weighted pitch–time energy on a regular grid (seconds × MIDI).
    Improved vs legacy: uses onset_sec, spans full note duration, symmetric padding.
    """
    if not note_matrix:
        raise ValueError("Empty note_matrix")

    starts = [float(n.get("onset_sec", 0)) for n in note_matrix]
    ends = [
        starts[i] + float(note_matrix[i].get("duration_sec", 0)) for i in range(len(note_matrix))
    ]
    pitches = [float(n.get("pitch", 60)) for n in note_matrix]

    t_min, t_max = min(starts), max(ends)
    p_min, p_max = min(pitches), max(pitches)
    t_pad = max((t_max - t_min) * 0.05, 0.01)
    p_pad = max((p_max - p_min) * 0.08, 1.0)
    t_min = max(0.0, t_min - t_pad)
    t_max = t_max + t_pad
    p_min = max(0.0, p_min - p_pad)
    p_max = min(127.0, p_max + p_pad)

    pitch_res, time_res = resolution
    energy = np.zeros((pitch_res, time_res), dtype=np.float64)
    time_edges = np.linspace(t_min, t_max, time_res + 1)
    p_span = p_max - p_min if p_max > p_min else 1.0

    for n in note_matrix:
        s = float(n.get("onset_sec", 0))
        e = s + float(n.get("duration_sec", 0))
        p = float(n.get("pitch", 60))
        intensity = float(n.get("velocity", 64)) / 127.0
        pi = int(np.clip((p - p_min) / p_span * (pitch_res - 1), 0, pitch_res - 1))
        j0 = int(np.searchsorted(time_edges, s, side="right") - 1)
        j1 = int(np.searchsorted(time_edges, e, side="right"))
        j0 = max(0, j0)
        j1 = min(time_res, max(j0 + 1, j1))
        energy[pi, j0:j1] += intensity

    if smoothing > 0:
        try:
            from scipy import ndimage

            energy = ndimage.gaussian_filter(energy, sigma=(smoothing, smoothing))
        except ImportError:
            log.warning("scipy not available; spectral heatmap without Gaussian smooth.")

    return energy, (t_min, t_max), (p_min, p_max)


def _major_event_times(energy: np.ndarray, t_min: float, t_max: float, max_n: int) -> List[float]:
    if energy.max() <= 0:
        return []
    time_axis = np.linspace(t_min, t_max, energy.shape[1])
    per_t = energy.max(axis=0)
    thr = np.percentile(per_t, 85)
    out: List[float] = []
    for i, (t, e) in enumerate(zip(time_axis, per_t)):
        if e < thr:
            continue
        if i == 0 and len(per_t) > 1 and e > per_t[1]:
            out.append(float(t))
        elif i == len(per_t) - 1 and e > per_t[i - 1]:
            out.append(float(t))
        elif 0 < i < len(per_t) - 1 and e > per_t[i - 1] and e > per_t[i + 1]:
            out.append(float(t))
    return out[:max_n]


def plot_heatmap_basic(
    note_matrix: NoteMatrix,
    cfg: Optional[HeatmapConfig] = None,
    *,
    title: str = "Activity heatmap (time × pitch)",
) -> "matplotlib.figure.Figure":
    """Heatmap 1 — basic: log1p counts, robust 99.5% vmax."""
    import matplotlib.pyplot as plt

    cfg = cfg or HeatmapConfig()
    H, t_axis, p_axis = build_pitch_time_matrix(
        note_matrix,
        bin_sec=cfg.bin_sec,
        pitch_step_semitones=cfg.pitch_step_semitones,
        mode=cfg.mode if cfg.mode != "velocity" else "occupancy",
    )
    X = np.log1p(H.astype(float))
    vmax = float(np.percentile(X, 99.5)) if X.max() > 0 else 1.0
    t_plot, xlabel = _time_scale(t_axis, cfg.time_units)

    fig, ax = plt.subplots(figsize=(12, 6))
    extent = [float(t_plot[0]), float(t_plot[-1]), float(p_axis[0]), float(p_axis[-1])]
    im = ax.imshow(
        X,
        aspect="auto",
        origin="lower",
        extent=extent,
        cmap=cfg.cmap_basic,
        vmin=0,
        vmax=vmax,
        interpolation="bilinear",
    )
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Pitch (MIDI)")
    ax.set_title(title + "\n(symbolic occupancy — not measured audio)")
    plt.colorbar(im, ax=ax, label="log1p(count)")
    plt.tight_layout()
    return fig


def plot_heatmap_advanced(
    note_matrix: NoteMatrix,
    cfg: Optional[HeatmapConfig] = None,
    *,
    title: str = "Advanced activity heatmap (time × pitch)",
    measure_starts: Optional[List[float]] = None,
) -> "matplotlib.figure.Figure":
    """Heatmap 2 — advanced: smoothing, gamma, note names, overlays, measure lines."""
    import matplotlib.pyplot as plt

    cfg = cfg or HeatmapConfig()
    mode = cfg.mode
    H, t_axis, p_axis = build_pitch_time_matrix(
        note_matrix,
        bin_sec=cfg.bin_sec,
        pitch_step_semitones=cfg.pitch_step_semitones,
        mode=mode,
    )
    X = preprocess_heatmap(H, cfg)
    vmax = float(np.percentile(X, 99.5)) if np.isfinite(X).all() and X.max() > 0 else 1.0
    t_plot, xlabel = _time_scale(t_axis, cfg.time_units)

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        pass

    fig, ax = plt.subplots(figsize=(12, 7))
    extent = [float(t_plot[0]), float(t_plot[-1]), float(p_axis[0]), float(p_axis[-1])]
    im = ax.imshow(
        X,
        aspect="auto",
        origin="lower",
        extent=extent,
        cmap=cfg.cmap_advanced,
        vmin=0,
        vmax=vmax,
        interpolation="bilinear",
    )
    ax.set_axisbelow(True)
    ax.grid(True, color="#cccccc", alpha=0.25, linestyle="--", linewidth=0.6)

    if len(p_axis) > 1:
        step = max(1, int(round(1.0 / max(p_axis[1] - p_axis[0], 0.5))))
        step = min(step, max(1, len(p_axis) // 30))
        idx = np.arange(0, len(p_axis), step)
        ax.set_yticks(p_axis[idx])
        ax.set_yticklabels([midi_to_note_name(float(v)) for v in p_axis[idx]])

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Pitch")
    ax.set_title(title + "\n(symbolic — not measured audio)")

    if cfg.show_measure_lines and measure_starts:
        scale = 1000.0 if cfg.time_units == "ms" else (100.0 if cfg.time_units == "cs" else 1.0)
        for t in measure_starts:
            ax.axvline(t * scale, color="#555555", linestyle=":", alpha=0.45, linewidth=0.8)

    plt.colorbar(im, ax=ax, label="Intensity")

    if cfg.overlay_points and note_matrix:
        xs = np.array(
            [
                float(n.get("onset_sec", 0)) + float(n.get("duration_sec", 0)) / 2
                for n in note_matrix
            ]
        )
        ys = np.array([float(n.get("pitch", 60)) for n in note_matrix])
        xs_plot, _ = _time_scale(xs, cfg.time_units)
        ax.scatter(xs_plot, ys, s=8.0, c="white", alpha=0.22, linewidths=0, zorder=5)

    plt.tight_layout()
    return fig


def plot_spectral_energy_heatmap(
    note_matrix: NoteMatrix,
    cfg: Optional[HeatmapConfig] = None,
    *,
    score=None,
    title: str = "Spectral energy heatmap (velocity-weighted, symbolic)",
) -> "matplotlib.figure.Figure":
    """
    Heatmap 3 — Granularidade-style spectral energy, improved:
    seconds on X-axis, no duplicate event markers, optional contours & measures.
    """
    import matplotlib.pyplot as plt

    cfg = cfg or HeatmapConfig()
    try:
        energy, (t_min, t_max), (p_min, p_max) = build_spectral_energy_matrix(
            note_matrix,
            cfg.spectral_resolution,
            cfg.spectral_smoothing,
        )
    except Exception as e:
        raise VisualizationError(str(e)) from e

    fig, ax = plt.subplots(figsize=(14, 8), facecolor="white")
    im = ax.imshow(
        energy,
        aspect="auto",
        origin="lower",
        extent=[t_min, t_max, p_min, p_max],
        cmap=cfg.spectral_cmap,
    )

    pitch_ticks = np.arange(int(p_min), int(p_max) + 1, max(1, int((p_max - p_min) / 12)))
    ax.set_yticks(pitch_ticks)
    ax.set_yticklabels([midi_to_note_name(float(v)) for v in pitch_ticks])

    if cfg.show_event_markers:
        for t in _major_event_times(energy, t_min, t_max, cfg.max_event_markers):
            ax.axvline(t, color="#FFD54F", linestyle="--", linewidth=1.2, alpha=0.75)

    if energy.max() > 0:
        levels = np.linspace(energy.max() * 0.25, energy.max() * 0.85, 6)
        tx = np.linspace(t_min, t_max, energy.shape[1])
        py = np.linspace(p_min, p_max, energy.shape[0])
        ax.contour(tx, py, energy, levels=levels, colors="white", alpha=0.35, linewidths=0.6)

    mstarts = measure_starts_sec(note_matrix)
    if not mstarts and score is not None:
        mstarts = extract_measure_starts_from_score(score)
    if cfg.show_measure_lines:
        for t in mstarts:
            ax.axvline(t, color="#888888", linestyle=":", alpha=0.4, linewidth=0.7)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Pitch")
    ax.set_title(title)
    cbar = plt.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label("Symbolic energy (velocity-weighted)")
    plt.tight_layout()
    return fig


def save_both_heatmaps(
    note_matrix: NoteMatrix,
    output_dir: Union[str, Path],
    cfg: Optional[HeatmapConfig] = None,
    *,
    score=None,
    dpi: int = 150,
) -> Dict[str, str]:
    """
    Save all three heatmap PNGs (basic, advanced, spectral).
    Returns paths keyed by type.
    """
    import matplotlib.pyplot as plt

    cfg = cfg or HeatmapConfig()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    mstarts = measure_starts_sec(note_matrix)
    if not mstarts and score is not None:
        mstarts = extract_measure_starts_from_score(score)

    paths: Dict[str, str] = {}
    for name, plot_fn, kwargs in (
        ("heatmap_basic", plot_heatmap_basic, {}),
        (
            "heatmap_advanced",
            plot_heatmap_advanced,
            {"measure_starts": mstarts},
        ),
        ("heatmap_spectral", plot_spectral_energy_heatmap, {"score": score}),
    ):
        fig = plot_fn(note_matrix, cfg, **kwargs)
        p = out / f"{name}.png"
        fig.savefig(p, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        paths[name] = str(p)
        log.info("Saved %s", p)
    return paths


# Backward-compatible aliases (v3 / Granularidade names)
build_heatmap_from_note_matrix = build_pitch_time_matrix
plot_heatmap_from_note_matrix = plot_heatmap_basic
