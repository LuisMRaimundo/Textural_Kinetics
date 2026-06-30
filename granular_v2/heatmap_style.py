"""
Publication-style matplotlib setup for Temporal_Granularity heatmaps.

Sobré palettes, robust percentile scaling, and consistent typography.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

import numpy as np

_CMAPS_REGISTERED = False

# Light, print-friendly sequential maps (high contrast, restrained hue)
_PALETTES = {
    "granular_blue": [
        "#fafbfc",
        "#e3eaf2",
        "#b8c9db",
        "#7a9ab8",
        "#4a6d8c",
        "#2d4a66",
        "#152a45",
    ],
    "granular_ember": [
        "#fafaf9",
        "#efe8e4",
        "#d4c4b8",
        "#a68b72",
        "#7a5c45",
        "#52382a",
        "#2a1c14",
    ],
    "granular_teal": [
        "#f8fafb",
        "#dce8ec",
        "#a8c4c8",
        "#6a9498",
        "#3d6468",
        "#234044",
        "#122428",
    ],
}


def register_colormaps() -> None:
    global _CMAPS_REGISTERED
    if _CMAPS_REGISTERED:
        return
    try:
        from matplotlib.colors import LinearSegmentedColormap

        for name, colors in _PALETTES.items():
            cmap = LinearSegmentedColormap.from_list(name, colors, N=256)
            try:
                from matplotlib import colormaps as mpl_cmaps

                if name not in mpl_cmaps:
                    mpl_cmaps.register(cmap, name=name)
            except Exception:
                cmap.register(name)  # type: ignore[attr-defined]
        _CMAPS_REGISTERED = True
    except Exception:
        pass


def resolve_cmap(name: str):
    """Return a matplotlib Colormap (custom or built-in)."""
    register_colormaps()
    try:
        from matplotlib import colormaps as mpl_cmaps

        return mpl_cmaps[name]
    except Exception:
        import matplotlib.cm as cm

        return cm.get_cmap(name)


def apply_publication_style() -> None:
    """Global rcParams for sober, high-contrast figures."""
    register_colormaps()
    try:
        import matplotlib as mpl

        mpl.rcParams.update(
            {
                "figure.facecolor": "#f7f8fa",
                "axes.facecolor": "#ffffff",
                "axes.edgecolor": "#4a5568",
                "axes.labelcolor": "#2d3748",
                "axes.titleweight": "600",
                "axes.titlesize": 13,
                "axes.labelsize": 11,
                "xtick.color": "#4a5568",
                "ytick.color": "#4a5568",
                "font.family": "sans-serif",
                "font.sans-serif": [
                    "Segoe UI",
                    "Helvetica Neue",
                    "Arial",
                    "DejaVu Sans",
                ],
                "grid.color": "#c5ccd6",
                "grid.linestyle": "-",
                "grid.linewidth": 0.45,
                "grid.alpha": 0.35,
            }
        )
        try:
            mpl.style.use("seaborn-v0_8-whitegrid")
        except OSError:
            pass
    except Exception:
        pass


def robust_display_range(
    data: np.ndarray,
    *,
    vmin_pct: float = 3.0,
    vmax_pct: float = 97.5,
    floor: float = 0.0,
) -> Tuple[float, float]:
    """Percentile-based limits for stronger contrast without clipping all peaks."""
    flat = np.asarray(data, dtype=float).ravel()
    flat = flat[np.isfinite(flat)]
    if flat.size == 0 or float(np.max(flat)) <= floor:
        return floor, 1.0
    lo = float(np.percentile(flat, vmin_pct))
    hi = float(np.percentile(flat, vmax_pct))
    if hi <= lo:
        hi = float(np.max(flat))
        lo = floor
    return max(floor, lo), hi


def style_axes(ax: Any, *, grid: bool = True) -> None:
    ax.set_facecolor("#ffffff")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#94a3b8")
        ax.spines[spine].set_linewidth(0.8)
    if grid:
        ax.set_axisbelow(True)
        ax.grid(True, which="major")


def add_professional_colorbar(
    fig: Any,
    im: Any,
    ax: Any,
    label: str,
    *,
    extend: Optional[str] = None,
) -> Any:
    cbar = fig.colorbar(
        im,
        ax=ax,
        pad=0.02,
        fraction=0.046,
        extend=extend or "neither",
    )
    cbar.outline.set_edgecolor("#94a3b8")
    cbar.outline.set_linewidth(0.6)
    cbar.ax.tick_params(colors="#4a5568", labelsize=9)
    cbar.set_label(label, color="#2d3748", fontsize=10, labelpad=8)
    return cbar


def display_norm_and_cmap(
    data: np.ndarray,
    cmap_name: str,
    *,
    vmin: float,
    vmax: float,
    gamma: float = 1.0,
):
    """Optional gamma compression on normalized data for mid-tone contrast."""
    from matplotlib.colors import Normalize, PowerNorm

    cmap = resolve_cmap(cmap_name)
    if gamma and abs(gamma - 1.0) > 1e-6:
        return PowerNorm(gamma=float(gamma), vmin=vmin, vmax=vmax), cmap
    return Normalize(vmin=vmin, vmax=vmax), cmap
