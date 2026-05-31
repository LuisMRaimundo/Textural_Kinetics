"""Activity & granularity plots (from v3 visualization)."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np


def _apply_density_plot_style(ax):
    ax.grid(True, alpha=0.2, linestyle="--", linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_color("#bdc3c7")


def plot_activity_granularity(
    results: Dict[str, Any],
    interval_key: Optional[float] = None,
):
    """results['activity_granularity'] or flat activity dict from run_analysis."""
    import matplotlib.pyplot as plt

    ag = results.get("activity_granularity", results)
    by_interval = ag.get("by_interval", {})
    interval_key = interval_key or ag.get("primary_interval")
    if interval_key is None and by_interval:
        interval_key = min(by_interval.keys())
    data = by_interval.get(interval_key, {})
    if not data and interval_key is not None:
        data = by_interval.get(float(interval_key), by_interval.get(str(interval_key), {}))
    t = data.get("time_points", [])
    onset = data.get("onset_density", [])
    active = data.get("active_density", [])
    act = ag.get("activity_rate", {})
    t_act = act.get("time_points", [])
    rate_act = act.get("events_per_sec", [])
    win_act = float(act.get("window_sec", 1.0))
    ioi_sec = ag.get("ioi_sec", [])
    gr = ag.get("granularity", {})
    er_g = results.get("event_rates", {}).get("global", {})

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(13, 10), dpi=110)
    if t and onset:
        ax1.plot(t, onset, label="Onset count/bin", color="#1a5f7a", linewidth=1.8)
        if active:
            ax1.plot(t, active, label="Active count/bin", color="#159895", linewidth=1.5)
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Count per bin")
        ax1.set_title("Temporal density")
        ax1.legend(fontsize=9)
    _apply_density_plot_style(ax1)

    if t_act and rate_act:
        ax2.plot(t_act, rate_act, color="#2d5a4a", linewidth=1.6)
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Events / s")
        ax2.set_title(f"Activity rate (window {win_act:.3g} s)")
    _apply_density_plot_style(ax2)

    if ioi_sec:
        ioi = np.asarray(ioi_sec, dtype=float)
        ioi = ioi[ioi > 0]
        if len(ioi):
            ax3.hist(ioi, bins=min(50, max(10, len(ioi) // 5)), color="#1a5f7a", alpha=0.6)
        ax3.set_xlabel("IOI (s)")
        ax3.set_title("Inter-onset intervals (positive)")
    _apply_density_plot_style(ax3)

    ax4.set_axis_off()
    lines = ["Summary", ""]
    if er_g:
        lines.append(f"events_per_second: {er_g.get('events_per_second', '—')}")
        lines.append(f"events_per_millisecond: {er_g.get('events_per_millisecond', '—')}")
    if gr:
        lines.append(f"IOI CV: {gr.get('ioi_cv', '—')}")
        lines.append(f"granularity_index: {gr.get('granularity_index', '—')}")
        lines.append(f"burstiness: {gr.get('burstiness', '—')}")
    ms = results.get("mustextu_summary", {})
    if ms:
        lines.append(f"Mustextu rate_eps: {ms.get('rate_events_per_second', '—')}")
    ax4.text(0.08, 0.92, "\n".join(lines), transform=ax4.transAxes, fontsize=10, va="top", family="monospace")
    plt.tight_layout()
    return fig
