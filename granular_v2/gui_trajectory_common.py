"""Shared VD10 session state, side panel, and pick/edit interaction (heatmap + image)."""

from __future__ import annotations

import copy
import tkinter as tk
from abc import ABC, abstractmethod
from tkinter import filedialog, messagebox, simpledialog
from typing import Any, Dict, List, Mapping, Optional, Tuple

TIME_MATCH_TOL_S = 0.001
HIT_TOL_T_S = 0.08
HIT_TOL_P_ST = 1.5

BLOCK_PALETTE = [
    {"edge": "#0ea5e9", "face": "#0ea5e933", "line": "#0284c7", "centre": "#f59e0b"},
    {"edge": "#a855f7", "face": "#a855f733", "line": "#7c3aed", "centre": "#c084fc"},
    {"edge": "#22c55e", "face": "#22c55e33", "line": "#15803d", "centre": "#86efac"},
    {"edge": "#f97316", "face": "#f9731633", "line": "#c2410c", "centre": "#fdba74"},
    {"edge": "#ec4899", "face": "#ec489933", "line": "#be185d", "centre": "#f9a8d4"},
]


class SampleEditDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, sample: Dict[str, float]) -> None:
        super().__init__(parent)
        self.title("Edit sample")
        self.resizable(False, False)
        self.result: Optional[Dict[str, float]] = None
        self._time_var = tk.StringVar(value=f"{sample['time_s']:.4f}")
        self._low_var = tk.StringVar(value=str(int(sample["low"])))
        self._high_var = tk.StringVar(value=str(int(sample["high"])))
        frm = tk.Frame(self, padx=10, pady=10)
        frm.pack()
        for row, (label, var) in enumerate(
            [("time_s", self._time_var), ("low (st)", self._low_var), ("high (st)", self._high_var)]
        ):
            tk.Label(frm, text=label, width=10, anchor="w").grid(row=row, column=0, pady=3)
            tk.Entry(frm, textvariable=var, width=16).grid(row=row, column=1, pady=3)
        btns = tk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, pady=(8, 0))
        tk.Button(btns, text="OK", width=8, command=self._ok).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Cancel", width=8, command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

    def _ok(self) -> None:
        try:
            self.result = {
                "time_s": float(self._time_var.get()),
                "low": float(self._low_var.get()),
                "high": float(self._high_var.get()),
            }
        except ValueError:
            messagebox.showerror("Edit sample", "Enter numeric values.", parent=self)
            return
        self.destroy()


class TrajectorySessionBase(ABC):
    """Multi-block VD10 session, side panel, and shared pick/edit handlers."""

    _require_calibration: bool = False

    def __init__(self) -> None:
        self.blocks: List[Dict[str, Any]] = [
            {"id": "block_1", "name": "Block 1", "samples": []},
        ]
        self._active_block_idx = 0
        self._next_block_num = 2
        self._selected_sample_idx: Optional[int] = None
        self._undo_stack: List[Dict[str, Any]] = []
        self._session_result: Optional[Dict[str, Any]] = None

        self._pick_mode = tk.BooleanVar(value=False)
        self._two_click = tk.BooleanVar(value=False)
        self._pending_time: Optional[float] = None
        self._pending_low: Optional[int] = None
        self._drag_start: Optional[Tuple[float, int]] = None
        self._edit_drag: Optional[str] = None
        self._edit_sample_idx: Optional[int] = None
        self._edit_snapshot: Optional[Dict[str, float]] = None

        self._ax = None
        self._canvas = None
        self._overlay_artists: List[Any] = []
        self._cid_press: Optional[int] = None
        self._cid_release: Optional[int] = None
        self._cid_motion: Optional[int] = None
        self._preview_rect = None
        self._suppress_list_select = False

        self._summary_var: Optional[tk.StringVar] = None
        self._status_var: Optional[tk.StringVar] = None
        self._agg_text: Optional[tk.Text] = None
        self._block_list: Optional[tk.Listbox] = None
        self._sample_list: Optional[tk.Listbox] = None

    @property
    def samples(self) -> List[Dict[str, float]]:
        return self.blocks[self._active_block_idx]["samples"]

    @samples.setter
    def samples(self, value: List[Dict[str, float]]) -> None:
        self.blocks[self._active_block_idx]["samples"] = value

    def _active_block(self) -> Dict[str, Any]:
        return self.blocks[self._active_block_idx]

    def _block_palette(self, block_idx: int) -> Dict[str, str]:
        return BLOCK_PALETTE[block_idx % len(BLOCK_PALETTE)]

    def _build_toolbar(self, parent: tk.Widget) -> tk.Frame:
        top = tk.Frame(parent)
        top.pack(fill=tk.X, padx=6, pady=4)
        tk.Checkbutton(
            top, text="Pick mode (new samples)", variable=self._pick_mode, command=self._on_pick_toggle
        ).pack(side=tk.LEFT, padx=4)
        tk.Checkbutton(top, text="Two-click span", variable=self._two_click).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Undo", command=self._undo, width=8).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Clear block", command=self._clear_active_block, width=10).pack(
            side=tk.LEFT, padx=4
        )
        return top

    def _build_side_panel(self, side: tk.Widget) -> None:
        tk.Label(side, text="Blocks", anchor="w").pack(fill=tk.X, padx=4, pady=(4, 0))
        blk_frm = tk.Frame(side)
        blk_frm.pack(fill=tk.X, padx=4, pady=2)
        self._block_list = tk.Listbox(blk_frm, height=4, exportselection=False)
        self._block_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._block_list.bind("<<ListboxSelect>>", self._on_block_select)
        blk_btns = tk.Frame(blk_frm)
        blk_btns.pack(side=tk.LEFT, padx=4)
        tk.Button(blk_btns, text="Add", command=self._add_block, width=7).pack(pady=1)
        tk.Button(blk_btns, text="Rename", command=self._rename_block, width=7).pack(pady=1)
        tk.Button(blk_btns, text="Delete", command=self._delete_block, width=7).pack(pady=1)

        tk.Label(side, text="Samples (active block, sorted display)", anchor="w").pack(
            fill=tk.X, padx=4, pady=(6, 0)
        )
        list_frm = tk.Frame(side)
        list_frm.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        scroll = tk.Scrollbar(list_frm)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._sample_list = tk.Listbox(list_frm, yscrollcommand=scroll.set, height=10)
        self._sample_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self._sample_list.yview)
        self._sample_list.bind("<<ListboxSelect>>", self._on_sample_list_select)
        self._sample_list.bind("<Double-Button-1>", self._on_numeric_edit_sample)

        btn_row = tk.Frame(side)
        btn_row.pack(fill=tk.X, padx=4)
        tk.Button(btn_row, text="Delete selected", command=self._delete_selected).pack(
            side=tk.LEFT, padx=2, pady=2
        )
        tk.Button(btn_row, text="Insert between", command=self._insert_between_selected).pack(
            side=tk.LEFT, padx=2, pady=2
        )

        act_row = tk.Frame(side)
        act_row.pack(fill=tk.X, padx=4, pady=6)
        tk.Button(act_row, text="Recompute", command=self._recompute_live, width=14).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(act_row, text="Export JSON", command=self._export, width=12).pack(side=tk.LEFT, padx=2)

        tk.Label(side, text="Summary", anchor="w").pack(fill=tk.X, padx=4)
        self._summary_var = tk.StringVar(value="Pick ≥2 samples per block; edits recompute live.")
        tk.Label(
            side, textvariable=self._summary_var, wraplength=280, justify=tk.LEFT, fg="#1e3a5f"
        ).pack(fill=tk.X, padx=4, pady=2)

        tk.Label(side, text="Results", anchor="w").pack(fill=tk.X, padx=4, pady=(8, 0))
        agg_frm = tk.Frame(side)
        agg_frm.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        agg_scroll = tk.Scrollbar(agg_frm)
        agg_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._agg_text = tk.Text(agg_frm, height=12, width=36, yscrollcommand=agg_scroll.set)
        self._agg_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        agg_scroll.config(command=self._agg_text.yview)
        self._agg_text.config(state=tk.DISABLED)

        self._refresh_block_list()

    def _build_body(self, parent: tk.Widget) -> Tuple[tk.Frame, tk.Frame]:
        body = tk.PanedWindow(parent, orient=tk.HORIZONTAL, sashwidth=4)
        body.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        canvas_host = tk.Frame(body)
        body.add(canvas_host, stretch="always")
        side = tk.Frame(body, width=300)
        body.add(side)
        self._build_side_panel(side)
        return canvas_host, side

    def reset_session(self) -> None:
        self.blocks = [{"id": "block_1", "name": "Block 1", "samples": []}]
        self._active_block_idx = 0
        self._next_block_num = 2
        self._selected_sample_idx = None
        self._undo_stack = []
        self._session_result = None
        self._pending_time = None
        self._pending_low = None
        self._drag_start = None
        self._edit_drag = None
        if self._summary_var is not None:
            self._summary_var.set("Pick ≥2 samples per block; edits recompute live.")
        self._set_agg_text("")
        self._refresh_block_list()
        self._refresh_sample_list()

    @abstractmethod
    def _canvas_ready_for_pick(self) -> bool:
        ...

    @abstractmethod
    def _is_calibrated(self) -> bool:
        ...

    @abstractmethod
    def _event_to_data(self, event) -> Tuple[float, int]:
        ...

    @abstractmethod
    def _redraw_overlays(self) -> None:
        ...

    def _preview_time_width(self) -> float:
        return 0.05

    def _update_preview_rect(self, t0: float, lo: float, hi: float) -> None:
        from matplotlib.patches import Rectangle

        assert self._ax is not None and self._canvas is not None
        tw = self._preview_time_width()
        palette = self._block_palette(self._active_block_idx)
        if self._preview_rect is None:
            self._preview_rect = Rectangle(
                (t0 - tw / 2, lo),
                tw,
                max(hi - lo, 0.5),
                linewidth=1.0,
                edgecolor=palette["edge"],
                facecolor=palette["face"],
                linestyle="--",
                zorder=10,
            )
            self._ax.add_patch(self._preview_rect)
        else:
            self._preview_rect.set_xy((t0 - tw / 2, lo))
            self._preview_rect.set_width(tw)
            self._preview_rect.set_height(max(hi - lo, 0.5))
        self._canvas.draw_idle()

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

    def _draw_block_overlays(self) -> None:
        from matplotlib.patches import Rectangle

        from .trajectory import normalize_samples

        assert self._ax is not None
        tw = self._preview_time_width()
        for block_idx, block in enumerate(self.blocks):
            raw = block.get("samples") or []
            if not raw:
                continue
            palette = self._block_palette(block_idx)
            active = block_idx == self._active_block_idx
            norm = normalize_samples(raw)
            centres_t: List[float] = []
            centres_p: List[float] = []
            for s in norm:
                t = s["time_s"]
                lo, hi = s["low"], s["high"]
                sample_idx = None
                if active:
                    for i, raw_s in enumerate(self.samples):
                        if (
                            abs(float(raw_s["time_s"]) - t) < TIME_MATCH_TOL_S
                            and int(raw_s["low"]) == lo
                            and int(raw_s["high"]) == hi
                        ):
                            sample_idx = i
                            break
                selected = active and sample_idx == self._selected_sample_idx
                lw = 2.4 if selected else 1.2
                ec = "#fef08a" if selected else palette["edge"]
                span = Rectangle(
                    (t - tw / 2, lo),
                    tw,
                    max(hi - lo, 0.5),
                    linewidth=lw,
                    edgecolor=ec,
                    facecolor=palette["face"],
                    zorder=8 if active else 6,
                    alpha=1.0 if active else 0.55,
                )
                self._ax.add_patch(span)
                self._overlay_artists.append(span)
                vline = self._ax.axvline(
                    t,
                    color=palette["line"],
                    linestyle=":" if not selected else "-",
                    alpha=0.85 if active else 0.45,
                    linewidth=0.9 if not selected else 1.2,
                    zorder=7,
                )
                self._overlay_artists.append(vline)
                centres_t.append(t)
                centres_p.append(s["centre"])
            if len(centres_t) >= 2:
                line, = self._ax.plot(
                    centres_t,
                    centres_p,
                    color=palette["centre"],
                    linewidth=2.0 if active else 1.2,
                    marker="o",
                    markersize=5 if active else 3,
                    zorder=9 if active else 5,
                    alpha=1.0 if active else 0.6,
                )
                self._overlay_artists.append(line)

    def _export_session_metadata(self) -> Dict[str, Any]:
        return {}

    def _export(self) -> None:
        if not self._session_result:
            self._recompute_live(show_warnings=False)
        if not self._session_result:
            messagebox.showwarning("Warning", "Nothing to export.")
            return
        fp = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="vd10_registral_trajectory.json",
        )
        if not fp:
            return
        from .trajectory import export_vd10_session_json

        payload = dict(self._session_result)
        payload.update(self._export_session_metadata())
        export_vd10_session_json(payload, fp)
        if self._status_var is not None:
            self._status_var.set(f"Exported VD10 session JSON: {fp}")

    def _snapshot_state(self) -> Dict[str, Any]:
        return {
            "blocks": copy.deepcopy(self.blocks),
            "active_block_idx": self._active_block_idx,
            "selected_sample_idx": self._selected_sample_idx,
        }

    def _restore_state(self, state: Dict[str, Any]) -> None:
        self.blocks = copy.deepcopy(state["blocks"])
        self._active_block_idx = int(state["active_block_idx"])
        self._selected_sample_idx = state.get("selected_sample_idx")
        self._refresh_block_list()
        self._refresh_sample_list()
        self._redraw_overlays()

    def _push_undo(self) -> None:
        self._undo_stack.append(self._snapshot_state())

    def _undo(self) -> None:
        if not self._undo_stack:
            return
        state = self._undo_stack.pop()
        self._restore_state(state)
        self._session_result = None
        self._recompute_live(show_warnings=False)

    def _on_pick_toggle(self) -> None:
        if self._pick_mode.get() and not self._canvas_ready_for_pick():
            messagebox.showwarning("Warning", "Load the picking surface first.")
            self._pick_mode.set(False)

    def _warn_if_not_calibrated(self) -> bool:
        if self._require_calibration and not self._is_calibrated():
            messagebox.showwarning(
                "Calibration required",
                "Calibrate pitch (two reference points) and time (start, end, duration) "
                "before picking on the image.",
            )
            return True
        return False

    def _refresh_block_list(self) -> None:
        assert self._block_list is not None
        self._block_list.delete(0, tk.END)
        for i, block in enumerate(self.blocks):
            prefix = "▶ " if i == self._active_block_idx else "  "
            n = len(block.get("samples") or [])
            self._block_list.insert(tk.END, f"{prefix}{block['name']} ({n})")
        self._block_list.selection_clear(0, tk.END)
        self._block_list.selection_set(self._active_block_idx)
        self._block_list.activate(self._active_block_idx)

    def _on_block_select(self, _event: tk.Event | None = None) -> None:
        assert self._block_list is not None
        sel = self._block_list.curselection()
        if not sel:
            return
        self._active_block_idx = int(sel[0])
        self._selected_sample_idx = None
        self._refresh_block_list()
        self._refresh_sample_list()
        self._redraw_overlays()
        self._recompute_live(show_warnings=False)

    def _add_block(self) -> None:
        self._push_undo()
        bid = f"block_{self._next_block_num}"
        name = f"Block {self._next_block_num}"
        self._next_block_num += 1
        self.blocks.append({"id": bid, "name": name, "samples": []})
        self._active_block_idx = len(self.blocks) - 1
        self._selected_sample_idx = None
        self._refresh_block_list()
        self._refresh_sample_list()
        self._redraw_overlays()
        self._recompute_live(show_warnings=False)

    def _rename_block(self) -> None:
        block = self._active_block()
        new_name = simpledialog.askstring("Rename block", "Block name:", initialvalue=block["name"])
        if not new_name:
            return
        self._push_undo()
        block["name"] = new_name.strip()
        self._refresh_block_list()
        self._recompute_live(show_warnings=False)

    def _delete_block(self) -> None:
        if len(self.blocks) <= 1:
            messagebox.showwarning("Blocks", "At least one block is required.")
            return
        self._push_undo()
        del self.blocks[self._active_block_idx]
        self._active_block_idx = min(self._active_block_idx, len(self.blocks) - 1)
        self._selected_sample_idx = None
        self._refresh_block_list()
        self._refresh_sample_list()
        self._redraw_overlays()
        self._recompute_live(show_warnings=False)

    def _clear_active_block(self) -> None:
        if not self.samples:
            return
        self._push_undo()
        self.samples = []
        self._selected_sample_idx = None
        self._refresh_block_list()
        self._refresh_sample_list()
        self._redraw_overlays()
        self._recompute_live(show_warnings=False)

    def _ordered_sample_indices(self) -> List[int]:
        return sorted(range(len(self.samples)), key=lambda i: self.samples[i]["time_s"])

    def _refresh_sample_list(self) -> None:
        assert self._sample_list is not None
        self._suppress_list_select = True
        self._sample_list.delete(0, tk.END)
        ordered = self._ordered_sample_indices()
        selected_row: Optional[int] = None
        for row, idx in enumerate(ordered):
            s = self.samples[idx]
            marker = "● " if idx == self._selected_sample_idx else "  "
            self._sample_list.insert(
                tk.END,
                f"{marker}t={s['time_s']:.3f}s  [{int(s['low'])}–{int(s['high'])}] st",
            )
            if idx == self._selected_sample_idx:
                selected_row = row
        if selected_row is not None:
            self._sample_list.selection_set(selected_row)
            self._sample_list.activate(selected_row)
        self._suppress_list_select = False

    def _sample_index_from_list(self) -> Optional[int]:
        assert self._sample_list is not None
        sel = self._sample_list.curselection()
        if not sel:
            return None
        ordered = self._ordered_sample_indices()
        return ordered[int(sel[0])]

    def _select_sample(self, idx: Optional[int]) -> None:
        self._selected_sample_idx = idx
        self._refresh_sample_list()
        self._redraw_overlays()

    def _on_sample_list_select(self, _event: tk.Event | None = None) -> None:
        if self._suppress_list_select:
            return
        idx = self._sample_index_from_list()
        self._select_sample(idx)

    def _delete_selected(self) -> None:
        idx = self._selected_sample_idx if self._selected_sample_idx is not None else self._sample_index_from_list()
        if idx is None:
            return
        self._push_undo()
        del self.samples[idx]
        self._selected_sample_idx = None
        self._refresh_block_list()
        self._refresh_sample_list()
        self._redraw_overlays()
        self._recompute_live(show_warnings=False)

    def _insert_between_selected(self) -> None:
        ordered = self._ordered_sample_indices()
        if len(ordered) < 2:
            messagebox.showwarning("Insert", "Need at least two samples to insert between.")
            return
        idx = self._selected_sample_idx if self._selected_sample_idx is not None else ordered[0]
        if idx not in ordered:
            idx = ordered[0]
        pos = ordered.index(idx)
        if pos >= len(ordered) - 1:
            messagebox.showwarning("Insert", "Select a sample that is not the last one.")
            return
        i0, i1 = ordered[pos], ordered[pos + 1]
        s0, s1 = self.samples[i0], self.samples[i1]
        t_mid = (float(s0["time_s"]) + float(s1["time_s"])) / 2.0
        from .trajectory import interpolate_band_at_time

        ins = interpolate_band_at_time(self.samples, t_mid)
        self._push_undo()
        self.samples.append(
            {"time_s": ins["time_s"], "low": float(ins["low"]), "high": float(ins["high"])}
        )
        self._selected_sample_idx = len(self.samples) - 1
        self._refresh_block_list()
        self._refresh_sample_list()
        self._redraw_overlays()
        self._recompute_live(show_warnings=False)

    def _on_numeric_edit_sample(self, _event: tk.Event) -> None:
        assert self._sample_list is not None
        idx = self._sample_index_from_list()
        if idx is None:
            return
        dlg = SampleEditDialog(self._sample_list, self.samples[idx])
        self._sample_list.wait_window(dlg)
        if dlg.result is None:
            return
        self._push_undo()
        self._apply_sample_values(idx, dlg.result, push_undo=False)
        self._select_sample(idx)
        self._recompute_live(show_warnings=True)

    def _find_sample_at_time(self, time_s: float, exclude_idx: Optional[int] = None) -> Optional[int]:
        for i, s in enumerate(self.samples):
            if exclude_idx is not None and i == exclude_idx:
                continue
            if abs(float(s["time_s"]) - time_s) <= TIME_MATCH_TOL_S:
                return i
        return None

    def _apply_sample_values(
        self,
        idx: int,
        values: Mapping[str, float],
        *,
        push_undo: bool = True,
    ) -> bool:
        from .trajectory import snap_semitone

        if push_undo:
            self._push_undo()
        lo = snap_semitone(float(values["low"]))
        hi = snap_semitone(float(values["high"]))
        if lo > hi:
            lo, hi = hi, lo
        time_s = max(0.0, float(values["time_s"]))
        conflict = self._find_sample_at_time(time_s, exclude_idx=idx)
        if conflict is not None:
            if push_undo and self._undo_stack:
                self._undo_stack.pop()
            messagebox.showwarning(
                "VD10",
                f"Another sample already exists at t={time_s:.3f}s.",
            )
            return False
        self.samples[idx] = {"time_s": time_s, "low": float(lo), "high": float(hi)}
        self._refresh_block_list()
        self._refresh_sample_list()
        self._redraw_overlays()
        return True

    def _add_sample(self, time_s: float, low: int, high: int) -> None:
        from .trajectory import snap_semitone

        lo = snap_semitone(low)
        hi = snap_semitone(high)
        if lo > hi:
            lo, hi = hi, lo
        existing = self._find_sample_at_time(time_s)
        self._push_undo()
        sample = {"time_s": float(time_s), "low": float(lo), "high": float(hi)}
        if existing is not None:
            self.samples[existing] = sample
            self._selected_sample_idx = existing
            action = "Updated"
        else:
            self.samples.append(sample)
            self._selected_sample_idx = len(self.samples) - 1
            action = "Added"
        self._refresh_block_list()
        self._refresh_sample_list()
        self._redraw_overlays()
        if self._status_var is not None:
            self._status_var.set(f"{action} sample at t={time_s:.3f}s, band {lo}–{hi} st.")
        self._recompute_live(show_warnings=False)

    def _hit_test_sample(self, t: float, p: int) -> Optional[Tuple[int, str]]:
        for idx in self._ordered_sample_indices():
            s = self.samples[idx]
            st = float(s["time_s"])
            lo, hi = int(s["low"]), int(s["high"])
            if abs(t - st) > HIT_TOL_T_S:
                continue
            if abs(p - hi) <= HIT_TOL_P_ST:
                return idx, "top"
            if abs(p - lo) <= HIT_TOL_P_ST:
                return idx, "bottom"
            if lo - HIT_TOL_P_ST <= p <= hi + HIT_TOL_P_ST:
                return idx, "band"
            return idx, "time"
        return None

    def _hit_test_centre_segment(self, t: float, p: float) -> Optional[float]:
        ordered = self._ordered_sample_indices()
        if len(ordered) < 2:
            return None
        from .trajectory import normalize_samples

        norm = normalize_samples(self.samples)
        best_t: Optional[float] = None
        best_dist = float("inf")
        for i in range(len(norm) - 1):
            t0, c0 = norm[i]["time_s"], norm[i]["centre"]
            t1, c1 = norm[i + 1]["time_s"], norm[i + 1]["centre"]
            if t < t0 or t > t1:
                continue
            if t1 <= t0:
                continue
            alpha = (t - t0) / (t1 - t0)
            c_line = c0 + alpha * (c1 - c0)
            dist = abs(p - c_line)
            if dist < best_dist:
                best_dist = dist
                best_t = t
        if best_dist <= HIT_TOL_P_ST * 2 and best_t is not None:
            return best_t
        return None

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
        if event.inaxes != self._ax:
            return
        if self._warn_if_not_calibrated():
            return
        t, p = self._event_to_data(event)

        if event.button == 3:
            t_ins = self._hit_test_centre_segment(t, float(p))
            if t_ins is not None:
                from .trajectory import interpolate_band_at_time

                ins = interpolate_band_at_time(self.samples, t_ins)
                self._push_undo()
                self.samples.append(
                    {"time_s": ins["time_s"], "low": float(ins["low"]), "high": float(ins["high"])}
                )
                self._selected_sample_idx = len(self.samples) - 1
                self._refresh_block_list()
                self._refresh_sample_list()
                self._redraw_overlays()
                self._recompute_live(show_warnings=False)
            return

        if event.button != 1:
            return

        hit = self._hit_test_sample(t, p)
        if hit is not None:
            idx, part = hit
            self._select_sample(idx)
            self._edit_drag = part
            self._edit_sample_idx = idx
            self._edit_snapshot = dict(self.samples[idx])
            self._push_undo()
            return

        if not self._pick_mode.get():
            return

        if self._two_click.get():
            if self._pending_time is None:
                self._pending_time = t
                self._pending_low = p
                if self._status_var is not None:
                    self._status_var.set(f"First click: t={t:.3f}s, low={p} st — click top.")
            else:
                assert self._pending_time is not None and self._pending_low is not None
                self._add_sample(self._pending_time, self._pending_low, p)
                self._pending_time = None
                self._pending_low = None
            return
        self._drag_start = (t, p)

    def _on_motion(self, event) -> None:
        if event.inaxes != self._ax:
            return
        if self._require_calibration and not self._is_calibrated():
            return

        if self._edit_drag and self._edit_sample_idx is not None:
            t, p = self._event_to_data(event)
            idx = self._edit_sample_idx
            s = dict(self.samples[idx])
            lo, hi = int(s["low"]), int(s["high"])
            width = hi - lo
            from .trajectory import snap_semitone

            if self._edit_drag == "band":
                new_centre = float(p)
                new_lo = snap_semitone(new_centre - width / 2.0)
                new_hi = snap_semitone(new_centre + width / 2.0)
                if new_lo > new_hi:
                    new_lo, new_hi = new_hi, new_lo
                s["low"] = float(new_lo)
                s["high"] = float(new_hi)
            elif self._edit_drag == "top":
                s["high"] = float(max(snap_semitone(p), int(s["low"])))
            elif self._edit_drag == "bottom":
                s["low"] = float(min(snap_semitone(p), int(s["high"])))
            elif self._edit_drag == "time":
                s["time_s"] = max(0.0, t)
            self.samples[idx] = s
            self._refresh_sample_list()
            self._redraw_overlays()
            return

        if not self._pick_mode.get() or self._drag_start is None:
            return
        t0, p0 = self._drag_start
        _, p1 = self._event_to_data(event)
        lo, hi = (min(p0, p1), max(p0, p1))
        self._update_preview_rect(t0, lo, hi)

    def _on_release(self, event) -> None:
        if self._edit_drag and self._edit_sample_idx is not None:
            idx = self._edit_sample_idx
            ok = self._apply_sample_values(idx, self.samples[idx], push_undo=False)
            if not ok and self._edit_snapshot is not None:
                self.samples[idx] = self._edit_snapshot
                if self._undo_stack:
                    self._undo_stack.pop()
            self._edit_drag = None
            self._edit_sample_idx = None
            self._edit_snapshot = None
            self._recompute_live(show_warnings=True)
            return

        if not self._pick_mode.get() or self._two_click.get() or self._drag_start is None:
            return
        if event.inaxes != self._ax:
            self._drag_start = None
            self._clear_preview()
            return
        if self._warn_if_not_calibrated():
            self._drag_start = None
            self._clear_preview()
            return
        t0, p0 = self._drag_start
        _, p1 = self._event_to_data(event)
        self._drag_start = None
        self._clear_preview()
        self._add_sample(t0, p0, p1)

    def _format_block_vd10(self, block_entry: Dict[str, Any]) -> List[str]:
        lines = [f"=== {block_entry['name']} ==="]
        vd10 = block_entry.get("vd10")
        if not vd10:
            lines.append(str(block_entry.get("vd10_error") or "VD10 not available."))
            return lines
        lines.append(str(vd10.get("summary", "")))
        agg = vd10["aggregates"]
        lines.extend(
            [
                f"  net_speed: {agg['net_speed']:.3f} st/s",
                f"  straightness: {agg['straightness']:.3f}",
                f"  net_displacement: {agg['net_displacement']:.2f} st",
            ]
        )
        for i, seg in enumerate(vd10.get("segments", [])):
            lines.append(
                f"  seg[{i}] dt={seg['dt_s']:.4f}s  speed={seg['speed_centre']:+.2f} st/s"
            )
        return lines

    def _recompute_live(self, *, show_warnings: bool = True) -> None:
        from .trajectory import compute_vd10_session

        self._session_result = compute_vd10_session(self.blocks)
        lines: List[str] = []
        summaries: List[str] = []
        any_warnings = False
        for block_entry in self._session_result.get("blocks", []):
            lines.extend(self._format_block_vd10(block_entry))
            lines.append("")
            vd10 = block_entry.get("vd10")
            if vd10:
                summaries.append(f"{block_entry['name']}: {vd10.get('summary', '')}")
                if show_warnings and vd10.get("sampling_warnings"):
                    any_warnings = True
                    lines.append("  — sampling warnings —")
                    for w in vd10["sampling_warnings"]:
                        lines.append(f"  {w['message']}")
                    lines.append("")

        relations = self._session_result.get("relations") or {}
        pairs = relations.get("pairs") or []
        if pairs:
            lines.append("=== Block relations ===")
            for pair in pairs:
                if pair.get("relation") == "no_overlap":
                    lines.append(
                        f"{pair['block_a']} ↔ {pair['block_b']}: no overlap"
                    )
                    continue
                lines.append(
                    f"{pair['block_a']} ↔ {pair['block_b']}: "
                    f"{pair['relation']}, {pair['direction']}, "
                    f"rate={pair['mean_inter_distance_rate_st_per_s']:+.3f} st/s "
                    f"(dt={pair['overlap_duration_s']:.3f}s)"
                )

        if self._summary_var is not None:
            if summaries:
                self._summary_var.set(" | ".join(summaries[:2]) + (" …" if len(summaries) > 2 else ""))
            elif len(self.blocks) == 1 and len(self.samples) < 2:
                self._summary_var.set("Pick ≥2 samples in the active block.")
        self._set_agg_text("\n".join(lines).strip())
        self._refresh_block_list()

        if show_warnings and any_warnings:
            messagebox.showwarning(
                "VD10 sampling",
                "Some segments have very short dt (< 0.1 s).\n"
                "Rely on net_speed and straightness; inspect segment dt in Results.",
            )

    def _set_agg_text(self, text: str) -> None:
        assert self._agg_text is not None
        self._agg_text.config(state=tk.NORMAL)
        self._agg_text.delete("1.0", tk.END)
        self._agg_text.insert("1.0", text)
        self._agg_text.config(state=tk.DISABLED)
