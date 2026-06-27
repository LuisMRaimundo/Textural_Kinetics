"""Tkinter tab — VD10 Registral trajectory picking on the pitch×time heatmap."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.patches import Rectangle

    HAS_MPL = True
except ImportError:
    HAS_MPL = False


TIME_MATCH_TOL_S = 0.001


class TrajectoryTab:
    """Registral trajectory (VD10) tab: pick spans on the advanced heatmap."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        get_note_matrix: Callable[[], Any],
        get_score: Callable[[], Any],
        get_file_path: Callable[[], Optional[str]],
    ) -> None:
        self._get_note_matrix = get_note_matrix
        self._get_score = get_score
        self._get_file_path = get_file_path

        self.samples: List[Dict[str, float]] = []
        self._undo_stack: List[List[Dict[str, float]]] = []
        self._result: Optional[Dict[str, Any]] = None

        self._pick_mode = tk.BooleanVar(value=False)
        self._two_click = tk.BooleanVar(value=False)
        self._pending_time: Optional[float] = None
        self._pending_low: Optional[int] = None
        self._drag_start: Optional[Tuple[float, int]] = None
        self._edit_index: Optional[int] = None

        self._fig = None
        self._ax = None
        self._canvas = None
        self._overlay_artists: List[Any] = []
        self._cid_press: Optional[int] = None
        self._cid_release: Optional[int] = None
        self._cid_motion: Optional[int] = None
        self._preview_rect: Optional[Rectangle] = None

        self._build(parent)

    def _build(self, parent: tk.Widget) -> None:
        top = tk.Frame(parent)
        top.pack(fill=tk.X, padx=6, pady=4)

        tk.Checkbutton(
            top,
            text="Pick mode",
            variable=self._pick_mode,
            command=self._on_pick_toggle,
        ).pack(side=tk.LEFT, padx=4)
        tk.Checkbutton(
            top,
            text="Two-click span (bottom then top)",
            variable=self._two_click,
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Undo", command=self._undo, width=8).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Clear all", command=self._clear_samples, width=10).pack(
            side=tk.LEFT, padx=4
        )
        tk.Button(top, text="Refresh heatmap", command=self._refresh_heatmap, width=14).pack(
            side=tk.LEFT, padx=4
        )

        body = tk.PanedWindow(parent, orient=tk.HORIZONTAL, sashwidth=4)
        body.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._heatmap_frame = tk.Frame(body)
        body.add(self._heatmap_frame, stretch="always")

        side = tk.Frame(body, width=280)
        body.add(side)

        tk.Label(side, text="Samples (sorted by time)", anchor="w").pack(fill=tk.X, padx=4, pady=(4, 0))
        list_frm = tk.Frame(side)
        list_frm.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        scroll = tk.Scrollbar(list_frm)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._sample_list = tk.Listbox(list_frm, yscrollcommand=scroll.set, height=12)
        self._sample_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self._sample_list.yview)
        self._sample_list.bind("<Double-Button-1>", self._on_edit_sample)

        btn_row = tk.Frame(side)
        btn_row.pack(fill=tk.X, padx=4)
        tk.Button(btn_row, text="Delete selected", command=self._delete_selected).pack(
            side=tk.LEFT, padx=2, pady=2
        )

        act_row = tk.Frame(side)
        act_row.pack(fill=tk.X, padx=4, pady=6)
        tk.Button(act_row, text="Compute VD10", command=self._compute, width=14).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(act_row, text="Export JSON", command=self._export, width=12).pack(
            side=tk.LEFT, padx=2
        )

        tk.Label(side, text="Summary", anchor="w").pack(fill=tk.X, padx=4)
        self._summary_var = tk.StringVar(value="Pick ≥2 samples, then Compute.")
        tk.Label(
            side,
            textvariable=self._summary_var,
            wraplength=260,
            justify=tk.LEFT,
            fg="#1e3a5f",
        ).pack(fill=tk.X, padx=4, pady=2)

        tk.Label(side, text="Aggregates", anchor="w").pack(fill=tk.X, padx=4, pady=(8, 0))
        agg_frm = tk.Frame(side)
        agg_frm.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        agg_scroll = tk.Scrollbar(agg_frm)
        agg_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._agg_text = tk.Text(agg_frm, height=10, width=34, yscrollcommand=agg_scroll.set)
        self._agg_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        agg_scroll.config(command=self._agg_text.yview)
        self._agg_text.config(state=tk.DISABLED)

        self._status_var = tk.StringVar(value="Load a score on the Analysis tab first.")
        tk.Label(parent, textvariable=self._status_var, fg="gray").pack(fill=tk.X, padx=6, pady=2)

    def on_score_loaded(self) -> None:
        """Refresh heatmap when the parent loads a new file."""
        self.samples = []
        self._undo_stack = []
        self._result = None
        self._edit_index = None
        self._pending_time = None
        self._pending_low = None
        self._drag_start = None
        self._refresh_sample_list()
        self._summary_var.set("Pick ≥2 samples, then Compute.")
        self._set_agg_text("")
        self._refresh_heatmap()

    def _on_pick_toggle(self) -> None:
        if self._pick_mode.get() and not self._ax:
            messagebox.showwarning("Warning", "Refresh the heatmap after loading a score.")
            self._pick_mode.set(False)

    def _push_undo(self) -> None:
        self._undo_stack.append([dict(s) for s in self.samples])

    def _undo(self) -> None:
        if not self._undo_stack:
            return
        self.samples = self._undo_stack.pop()
        self._result = None
        self._refresh_sample_list()
        self._redraw_overlays()
        self._summary_var.set("Pick ≥2 samples, then Compute.")
        self._set_agg_text("")

    def _clear_samples(self) -> None:
        if self.samples:
            self._push_undo()
        self.samples = []
        self._result = None
        self._edit_index = None
        self._pending_time = None
        self._pending_low = None
        self._drag_start = None
        self._refresh_sample_list()
        self._redraw_overlays()
        self._summary_var.set("Pick ≥2 samples, then Compute.")
        self._set_agg_text("")

    def _refresh_sample_list(self) -> None:
        self._sample_list.delete(0, tk.END)
        ordered = sorted(self.samples, key=lambda s: s["time_s"])
        for i, s in enumerate(ordered):
            self._sample_list.insert(
                tk.END,
                f"t={s['time_s']:.3f}s  [{int(s['low'])}–{int(s['high'])}] st",
            )

    def _sample_index_from_list(self) -> Optional[int]:
        sel = self._sample_list.curselection()
        if not sel:
            return None
        ordered_idx = int(sel[0])
        ordered = sorted(range(len(self.samples)), key=lambda i: self.samples[i]["time_s"])
        return ordered[ordered_idx]

    def _delete_selected(self) -> None:
        idx = self._sample_index_from_list()
        if idx is None:
            return
        self._push_undo()
        del self.samples[idx]
        self._result = None
        self._refresh_sample_list()
        self._redraw_overlays()

    def _on_edit_sample(self, _event: tk.Event) -> None:
        idx = self._sample_index_from_list()
        if idx is None:
            return
        self._edit_index = idx
        self._pick_mode.set(True)
        self._status_var.set(
            f"Re-pick sample #{idx + 1}: drag or two-click a vertical span on the heatmap."
        )

    def _find_sample_at_time(self, time_s: float) -> Optional[int]:
        for i, s in enumerate(self.samples):
            if abs(float(s["time_s"]) - time_s) <= TIME_MATCH_TOL_S:
                return i
        return None

    def _add_sample(self, time_s: float, low: int, high: int) -> None:
        from .trajectory import snap_semitone

        lo = snap_semitone(low)
        hi = snap_semitone(high)
        if lo > hi:
            lo, hi = hi, lo
        sample = {"time_s": float(time_s), "low": float(lo), "high": float(hi)}

        if self._edit_index is not None:
            for i, s in enumerate(self.samples):
                if i != self._edit_index and abs(float(s["time_s"]) - time_s) <= TIME_MATCH_TOL_S:
                    messagebox.showwarning(
                        "VD10",
                        f"Another sample already exists at t={time_s:.3f}s.\n"
                        "Pick a different time, or delete the other sample first.",
                    )
                    return
            self._push_undo()
            self.samples[self._edit_index] = sample
            self._edit_index = None
            action = "Updated"
        else:
            existing = self._find_sample_at_time(time_s)
            self._push_undo()
            if existing is not None:
                self.samples[existing] = sample
                action = "Updated"
            else:
                self.samples.append(sample)
                action = "Added"

        self._result = None
        self._refresh_sample_list()
        self._redraw_overlays()
        self._status_var.set(f"{action} sample at t={time_s:.3f}s, band {lo}–{hi} st.")

    def _event_to_data(self, event) -> Tuple[float, int]:
        assert self._ax is not None
        x, y = self._ax.transData.inverted().transform((event.x, event.y))
        from .trajectory import snap_semitone

        return max(0.0, float(x)), snap_semitone(y)

    def _connect_pickers(self) -> None:
        if not self._canvas or not self._ax:
            return
        self._disconnect_pickers()
        self._cid_press = self._canvas.mpl_connect("button_press_event", self._on_press)
        self._cid_release = self._canvas.mpl_connect("button_release_event", self._on_release)
        self._cid_motion = self._canvas.mpl_connect("motion_notify_event", self._on_motion)

    def _disconnect_pickers(self) -> None:
        if not self._canvas:
            return
        for cid in (self._cid_press, self._cid_release, self._cid_motion):
            if cid is not None:
                self._canvas.mpl_disconnect(cid)
        self._cid_press = self._cid_release = self._cid_motion = None

    def _on_press(self, event) -> None:
        if not self._pick_mode.get() or event.inaxes != self._ax or event.button != 1:
            return
        t, p = self._event_to_data(event)
        if self._two_click.get():
            if self._pending_time is None:
                self._pending_time = t
                self._pending_low = p
                self._status_var.set(f"First click: t={t:.3f}s, low={p} st — click top.")
            else:
                assert self._pending_time is not None and self._pending_low is not None
                self._add_sample(self._pending_time, self._pending_low, p)
                self._pending_time = None
                self._pending_low = None
            return
        self._drag_start = (t, p)

    def _on_motion(self, event) -> None:
        if not self._pick_mode.get() or self._drag_start is None or event.inaxes != self._ax:
            return
        assert self._ax is not None and self._canvas is not None
        t0, p0 = self._drag_start
        _, p1 = self._event_to_data(event)
        lo, hi = (min(p0, p1), max(p0, p1))
        if self._preview_rect is None:
            self._preview_rect = Rectangle(
                (t0 - 0.025, lo),
                0.05,
                max(hi - lo, 0.5),
                linewidth=1.0,
                edgecolor="#38bdf8",
                facecolor="#38bdf844",
                linestyle="--",
                zorder=10,
            )
            self._ax.add_patch(self._preview_rect)
        else:
            self._preview_rect.set_xy((t0 - 0.025, lo))
            self._preview_rect.set_width(0.05)
            self._preview_rect.set_height(max(hi - lo, 0.5))
        self._canvas.draw_idle()

    def _on_release(self, event) -> None:
        if not self._pick_mode.get() or self._two_click.get() or self._drag_start is None:
            return
        if event.inaxes != self._ax:
            self._drag_start = None
            self._clear_preview()
            return
        t0, p0 = self._drag_start
        _, p1 = self._event_to_data(event)
        self._drag_start = None
        self._clear_preview()
        self._add_sample(t0, p0, p1)

    def _clear_preview(self) -> None:
        if self._preview_rect is not None:
            self._preview_rect.remove()
            self._preview_rect = None
            if self._canvas:
                self._canvas.draw_idle()

    def _clear_overlays(self) -> None:
        for art in self._overlay_artists:
            try:
                art.remove()
            except Exception:
                pass
        self._overlay_artists.clear()
        self._preview_rect = None

    def _redraw_overlays(self) -> None:
        if not self._ax or not self._canvas:
            return
        self._clear_overlays()
        from .trajectory import normalize_samples

        if not self.samples:
            self._canvas.draw_idle()
            return

        norm = normalize_samples(self.samples)
        centres_t: List[float] = []
        centres_p: List[float] = []

        for s in norm:
            t = s["time_s"]
            lo, hi = s["low"], s["high"]
            span = Rectangle(
                (t - 0.025, lo),
                0.05,
                max(hi - lo, 0.5),
                linewidth=1.2,
                edgecolor="#0ea5e9",
                facecolor="#0ea5e933",
                zorder=8,
            )
            self._ax.add_patch(span)
            self._overlay_artists.append(span)
            vline = self._ax.axvline(
                t, color="#0284c7", linestyle=":", alpha=0.7, linewidth=0.9, zorder=7
            )
            self._overlay_artists.append(vline)
            centres_t.append(t)
            centres_p.append(s["centre"])

        if len(centres_t) >= 2:
            line, = self._ax.plot(
                centres_t,
                centres_p,
                color="#f59e0b",
                linewidth=2.0,
                marker="o",
                markersize=5,
                zorder=9,
                label="centre trajectory",
            )
            self._overlay_artists.append(line)

        self._canvas.draw_idle()

    def _refresh_heatmap(self) -> None:
        if not HAS_MPL:
            messagebox.showwarning("Warning", "matplotlib required for VD10 heatmap.")
            return
        nm = self._get_note_matrix()
        if not nm:
            self._status_var.set("Load a score on the Analysis tab first.")
            return

        for w in self._heatmap_frame.winfo_children():
            w.destroy()
        self._disconnect_pickers()
        self._fig = self._ax = self._canvas = None
        self._overlay_artists.clear()

        from .config import HeatmapConfig
        from .heatmaps import extract_measure_starts_from_score, plot_heatmap_advanced

        cfg = HeatmapConfig(time_units="s")
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
        self._status_var.set(
            f"Heatmap ready{f' — {fp}' if fp else ''}. "
            "Enable Pick mode — one sample per time (re-pick replaces same x)."
        )

    def _compute(self) -> None:
        from .trajectory import TrajectoryError, compute_vd10

        if len(self.samples) < 2:
            messagebox.showwarning("Warning", "Place at least two samples before computing VD10.")
            return
        try:
            self._result = compute_vd10(self.samples)
        except TrajectoryError as e:
            messagebox.showerror("VD10", str(e))
            return
        self._summary_var.set(str(self._result["summary"]))
        agg = self._result["aggregates"]
        labels = self._result["labels"]
        lines = [
            f"net_displacement: {agg['net_displacement']:.2f} st",
            f"net_speed: {agg['net_speed']:.3f} st/s",
            f"total_path: {agg['total_path']:.2f} st",
            f"straightness: {agg['straightness']:.3f}",
            f"inflections: {agg['inflections']}",
            f"mean |speed_centre|: {agg['mean_speed']:.3f} st/s",
            f"max |speed_centre|: {agg['max_speed']:.3f} st/s",
            f"direction: {labels['direction']}",
            f"band_behaviour: {labels['band_behaviour']}",
            f"shape_hint: {labels['shape_hint']}",
        ]
        self._set_agg_text("\n".join(lines))
        self._redraw_overlays()

    def _set_agg_text(self, text: str) -> None:
        self._agg_text.config(state=tk.NORMAL)
        self._agg_text.delete("1.0", tk.END)
        self._agg_text.insert("1.0", text)
        self._agg_text.config(state=tk.DISABLED)

    def _export(self) -> None:
        if not self._result:
            messagebox.showwarning("Warning", "Compute VD10 first.")
            return
        fp = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="vd10_registral_trajectory.json",
        )
        if not fp:
            return
        from .trajectory import export_vd10_json

        export_vd10_json(self._result, fp)
        self._status_var.set(f"Exported VD10 JSON: {fp}")
