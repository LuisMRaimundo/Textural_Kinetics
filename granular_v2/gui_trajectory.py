"""Tkinter tab — VD10 Registral trajectory picking on the pitch×time heatmap."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Optional, Tuple

log = logging.getLogger(__name__)

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from .gui_trajectory_common import TrajectorySessionBase


class TrajectoryTab(TrajectorySessionBase):
    """Registral trajectory (VD10) tab: editable picks and multi-block analysis on heatmap."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        get_note_matrix: Callable[[], Any],
        get_score: Callable[[], Any],
        get_file_path: Callable[[], Optional[str]],
    ) -> None:
        super().__init__()
        self._get_note_matrix = get_note_matrix
        self._get_score = get_score
        self._get_file_path = get_file_path
        self._fig = None
        self._heatmap_frame: Optional[tk.Frame] = None
        self._build(parent)

    def _build(self, parent: tk.Widget) -> None:
        top = self._build_toolbar(parent)
        tk.Button(top, text="Refresh heatmap", command=self._refresh_heatmap, width=14).pack(
            side=tk.LEFT, padx=4
        )
        canvas_host, _side = self._build_body(parent)
        self._heatmap_frame = canvas_host

        self._status_var = tk.StringVar(value="Load a score on the Analysis tab first.")
        tk.Label(parent, textvariable=self._status_var, fg="gray").pack(fill=tk.X, padx=6, pady=2)

    def on_score_loaded(self) -> None:
        self.reset_session()
        self._refresh_heatmap()

    def _canvas_ready_for_pick(self) -> bool:
        return self._ax is not None

    def _is_calibrated(self) -> bool:
        return True

    def _event_to_data(self, event) -> Tuple[float, int]:
        assert self._ax is not None
        x, y = self._ax.transData.inverted().transform((event.x, event.y))
        from .trajectory import snap_semitone

        return max(0.0, float(x)), snap_semitone(y)

    def _redraw_overlays(self) -> None:
        if not self._ax or not self._canvas:
            return
        self._clear_overlays()
        self._draw_block_overlays()
        self._canvas.draw_idle()

    def _refresh_heatmap(self) -> None:
        if not HAS_MPL:
            messagebox.showwarning("Warning", "matplotlib required for VD10 heatmap.")
            return
        nm = self._get_note_matrix()
        if not nm:
            if self._status_var is not None:
                self._status_var.set("Load a score on the Analysis tab first.")
            return

        assert self._heatmap_frame is not None
        for w in self._heatmap_frame.winfo_children():
            w.destroy()
        self._disconnect_pickers()
        self._fig = self._ax = self._canvas = None
        self._overlay_artists.clear()

        from .config import HeatmapConfig
        from .heatmaps import extract_measure_starts_from_score, plot_heatmap_advanced

        cfg = HeatmapConfig(time_units="s", overlay_points=True)
        score = self._get_score()
        mstarts = extract_measure_starts_from_score(score) if score else []
        self._fig = plot_heatmap_advanced(
            nm,
            cfg,
            title="Pitch×time heatmap — VD10 picking",
            measure_starts=mstarts,
        )
        self._ax = self._fig.axes[0]
        self._canvas = FigureCanvasTkAgg(self._fig, master=self._heatmap_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self._canvas, self._heatmap_frame)
        self._connect_pickers()
        self._redraw_overlays()
        fp = self._get_file_path()
        if self._status_var is not None:
            self._status_var.set(
                f"Heatmap ready{f' — {fp}' if fp else ''}. "
                "Drag markers to edit; right-click centre line to insert; Pick mode for new spans."
            )

    def _on_pick_toggle(self) -> None:
        if self._pick_mode.get() and not self._ax:
            messagebox.showwarning("Warning", "Refresh the heatmap after loading a score.")
            self._pick_mode.set(False)
