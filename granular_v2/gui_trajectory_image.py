"""Tkinter tab — VD10 registral trajectory picking on a calibrated score image."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger(__name__)

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    from matplotlib.image import imread

    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from .gui_trajectory_common import TrajectorySessionBase
from .trajectory import describe_axis_calibration, make_axis_calibration, snap_semitone

CALIBRATION_NOTE = (
    "Assumes linear image position ↔ pitch/time (proportional graphic scores). "
    "Not valid for non-spatial symbolic notation."
)


class _PitchValueDialog(tk.Toplevel):
    """Enter MIDI semitone for a calibration click (optional note name hint)."""

    def __init__(self, parent: tk.Widget, *, title: str, initial: str = "60") -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result: Optional[float] = None
        self._var = tk.StringVar(value=initial)
        frm = tk.Frame(self, padx=10, pady=10)
        frm.pack()
        tk.Label(frm, text="MIDI semitone (e.g. 48 = C3):", anchor="w").pack(fill=tk.X)
        tk.Entry(frm, textvariable=self._var, width=18).pack(pady=4)
        tk.Label(frm, text="Or note name (e.g. C3):", anchor="w").pack(fill=tk.X)
        self._note_var = tk.StringVar(value="")
        tk.Entry(frm, textvariable=self._note_var, width=18).pack(pady=4)
        btns = tk.Frame(frm)
        btns.pack(pady=(6, 0))
        tk.Button(btns, text="OK", width=8, command=self._ok).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Cancel", width=8, command=self.destroy).pack(side=tk.LEFT, padx=4)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

    def _ok(self) -> None:
        note = self._note_var.get().strip()
        if note:
            try:
                from music21 import pitch as m21_pitch

                self.result = float(m21_pitch.Pitch(note).midi)
                self.destroy()
                return
            except Exception:
                messagebox.showerror("Pitch", f"Could not parse note name '{note}'.", parent=self)
                return
        try:
            self.result = float(self._var.get())
        except ValueError:
            messagebox.showerror("Pitch", "Enter a numeric MIDI value or note name.", parent=self)
            return
        self.destroy()


class TrajectoryImageTab(TrajectorySessionBase):
    """VD10 picking on a PNG/JPG score excerpt with two-axis calibration."""

    _require_calibration = True

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__()
        self._fig: Optional[Figure] = None
        self._image_frame: Optional[tk.Frame] = None
        self._image_path: Optional[str] = None
        self._image_array = None
        self._img_height = 0
        self._img_width = 0
        self._duration_s = 0.0

        self._pitch_p0: Optional[Tuple[float, float]] = None
        self._pitch_p1: Optional[Tuple[float, float]] = None
        self._time_p0_px: Optional[float] = None
        self._time_p1_px: Optional[float] = None

        self._map_time: Optional[Any] = None
        self._map_pitch: Optional[Any] = None

        self._cal_mode: Optional[str] = None
        self._cal_var = tk.StringVar(value="Pitch: — | Time: —")
        self._build(parent)

    def _build(self, parent: tk.Widget) -> None:
        top = self._build_toolbar(parent)
        tk.Button(top, text="Load image…", command=self._load_image, width=12).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Calibrate pitch", command=self._start_pitch_calibration, width=14).pack(
            side=tk.LEFT, padx=4
        )
        tk.Button(top, text="Calibrate time", command=self._start_time_calibration, width=14).pack(
            side=tk.LEFT, padx=4
        )

        cal_row = tk.Frame(parent)
        cal_row.pack(fill=tk.X, padx=6, pady=(0, 2))
        tk.Label(cal_row, textvariable=self._cal_var, anchor="w", fg="#1e3a5f").pack(side=tk.LEFT)
        tk.Label(cal_row, text=CALIBRATION_NOTE, anchor="w", fg="gray", wraplength=520, justify=tk.LEFT).pack(
            side=tk.LEFT, padx=8
        )

        canvas_host, _side = self._build_body(parent)
        self._image_frame = canvas_host

        self._status_var = tk.StringVar(
            value="Load a score excerpt image (PNG/JPG), calibrate pitch and time, then pick."
        )
        tk.Label(parent, textvariable=self._status_var, fg="gray").pack(fill=tk.X, padx=6, pady=2)

    def _canvas_ready_for_pick(self) -> bool:
        return self._ax is not None and self._image_array is not None

    def _is_calibrated(self) -> bool:
        return (
            self._map_time is not None
            and self._map_pitch is not None
            and self._duration_s > 0.0
        )

    def _preview_time_width(self) -> float:
        return max(0.05, self._duration_s * 0.01) if self._duration_s > 0 else 0.05

    def _export_session_metadata(self) -> Dict[str, Any]:
        meta: Dict[str, Any] = {"source": "image"}
        if self._image_path:
            meta["image_path"] = self._image_path
        if self._pitch_p0 and self._pitch_p1 and self._time_p0_px is not None and self._time_p1_px is not None:
            meta["image_calibration"] = {
                "assumption": CALIBRATION_NOTE,
                "duration_s": float(self._duration_s),
                "pitch": describe_axis_calibration(
                    self._pitch_p0[0], self._pitch_p0[1], self._pitch_p1[0], self._pitch_p1[1]
                ),
                "time": describe_axis_calibration(
                    self._time_p0_px, 0.0, self._time_p1_px, float(self._duration_s)
                ),
            }
        return meta

    def _update_calibration_label(self) -> None:
        pitch_txt = "—"
        if self._pitch_p0 and self._pitch_p1:
            pitch_txt = (
                f"y={self._pitch_p0[0]:.0f}→{self._pitch_p0[1]:.0f}st, "
                f"y={self._pitch_p1[0]:.0f}→{self._pitch_p1[1]:.0f}st"
            )
        time_txt = "—"
        if self._time_p0_px is not None and self._time_p1_px is not None and self._duration_s > 0:
            time_txt = (
                f"x={self._time_p0_px:.0f}→0s, "
                f"x={self._time_p1_px:.0f}→{self._duration_s:.3f}s"
            )
        ready = " ✓" if self._is_calibrated() else ""
        self._cal_var.set(f"Pitch: {pitch_txt} | Time: {time_txt}{ready}")

    def _load_image(self) -> None:
        if not HAS_MPL:
            messagebox.showwarning("Warning", "matplotlib required for image picking.")
            return
        fp = filedialog.askopenfilename(
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                ("All", "*.*"),
            ]
        )
        if not fp:
            return
        try:
            img = imread(fp)
        except Exception as exc:
            log.exception("image load failed")
            messagebox.showerror("Error", f"Could not load image:\n{exc}")
            return

        self._image_path = fp
        self._image_array = img
        self._img_height, self._img_width = img.shape[0], img.shape[1]
        self._pitch_p0 = self._pitch_p1 = None
        self._time_p0_px = self._time_p1_px = None
        self._map_time = self._map_pitch = None
        self._duration_s = 0.0
        self._cal_mode = None
        self.reset_session()
        self._render_image_pixel_view()
        self._update_calibration_label()
        if self._status_var is not None:
            self._status_var.set(f"Loaded {Path(fp).name}. Calibrate pitch and time axes.")

    def _render_image_pixel_view(self) -> None:
        assert self._image_frame is not None and self._image_array is not None
        for w in self._image_frame.winfo_children():
            w.destroy()
        self._disconnect_pickers()
        self._fig = Figure(figsize=(8, 5), dpi=100)
        self._ax = self._fig.add_subplot(111)
        self._ax.imshow(self._image_array, origin="upper", aspect="auto")
        self._ax.set_xlim(0, self._img_width)
        self._ax.set_ylim(self._img_height, 0)
        self._ax.set_xlabel("Image x (pixels)")
        self._ax.set_ylabel("Image y (pixels)")
        self._ax.set_title("Score excerpt — calibrate axes before picking")
        self._canvas = FigureCanvasTkAgg(self._fig, master=self._image_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self._canvas, self._image_frame)
        self._connect_pickers()
        self._redraw_overlays()

    def _apply_data_coordinates(self) -> None:
        assert self._map_time is not None and self._map_pitch is not None
        assert self._image_frame is not None and self._image_array is not None

        t_left = self._map_time(0.0)
        t_right = self._map_time(float(self._img_width))
        p_top = self._map_pitch(0.0)
        p_bottom = self._map_pitch(float(self._img_height))
        x0, x1 = min(t_left, t_right), max(t_left, t_right)
        y0, y1 = min(p_bottom, p_top), max(p_bottom, p_top)

        for w in self._image_frame.winfo_children():
            w.destroy()
        self._disconnect_pickers()
        self._fig = Figure(figsize=(8, 5), dpi=100)
        self._ax = self._fig.add_subplot(111)
        self._ax.imshow(
            self._image_array,
            origin="upper",
            aspect="auto",
            extent=[x0, x1, y0, y1],
        )
        self._ax.set_xlim(x0, x1)
        self._ax.set_ylim(y0, y1)
        self._ax.set_xlabel("Time (s)")
        self._ax.set_ylabel("Pitch (semitones)")
        self._ax.set_title("Score excerpt — VD10 image picking")
        self._canvas = FigureCanvasTkAgg(self._fig, master=self._image_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self._canvas, self._image_frame)
        self._connect_pickers()
        self._redraw_overlays()

    def _rebuild_maps(self) -> None:
        self._map_time = None
        self._map_pitch = None
        if self._pitch_p0 and self._pitch_p1:
            self._map_pitch = make_axis_calibration(
                self._pitch_p0[0], self._pitch_p0[1], self._pitch_p1[0], self._pitch_p1[1]
            )
        if self._time_p0_px is not None and self._time_p1_px is not None and self._duration_s > 0:
            self._map_time = make_axis_calibration(
                self._time_p0_px, 0.0, self._time_p1_px, self._duration_s
            )
        self._update_calibration_label()
        if self._is_calibrated():
            self._apply_data_coordinates()
            if self._status_var is not None:
                self._status_var.set(
                    "Calibration complete. Enable Pick mode or drag existing markers to edit."
                )

    def _ensure_pixel_view(self) -> None:
        if self._image_array is None:
            return
        if self._ax is not None and self._ax.get_xlabel() == "Image x (pixels)":
            return
        self._render_image_pixel_view()

    def _start_pitch_calibration(self) -> None:
        if not self._canvas_ready_for_pick():
            messagebox.showwarning("Warning", "Load an image first.")
            return
        self._ensure_pixel_view()
        self._cal_mode = "pitch_p0"
        self._pitch_p0 = self._pitch_p1 = None
        self._map_pitch = None
        self._update_calibration_label()
        if self._status_var is not None:
            self._status_var.set("Pitch calibration: click the first reference point on the image.")

    def _start_time_calibration(self) -> None:
        if not self._canvas_ready_for_pick():
            messagebox.showwarning("Warning", "Load an image first.")
            return
        self._ensure_pixel_view()
        self._cal_mode = "time_p0"
        self._time_p0_px = self._time_p1_px = None
        self._map_time = None
        self._duration_s = 0.0
        self._update_calibration_label()
        if self._status_var is not None:
            self._status_var.set("Time calibration: click the start of the excerpt (0 s).")

    def _pixel_from_event(self, event) -> Tuple[float, float]:
        return float(event.xdata if event.xdata is not None else 0.0), float(
            event.ydata if event.ydata is not None else 0.0
        )

    def _handle_calibration_click(self, event) -> None:
        if self._cal_mode is None:
            return
        x_px, y_px = self._pixel_from_event(event)
        host = self._image_frame

        if self._cal_mode == "pitch_p0":
            dlg = _PitchValueDialog(host, title="Pitch at first point", initial="48")
            host.wait_window(dlg)
            if dlg.result is None:
                return
            self._pitch_p0 = (y_px, float(dlg.result))
            self._cal_mode = "pitch_p1"
            if self._status_var is not None:
                self._status_var.set("Pitch calibration: click the second reference point.")
            return

        if self._cal_mode == "pitch_p1":
            dlg = _PitchValueDialog(host, title="Pitch at second point", initial="72")
            host.wait_window(dlg)
            if dlg.result is None:
                self._cal_mode = None
                return
            self._pitch_p1 = (y_px, float(dlg.result))
            self._cal_mode = None
            self._rebuild_maps()
            return

        if self._cal_mode == "time_p0":
            self._time_p0_px = x_px
            self._cal_mode = "time_p1"
            if self._status_var is not None:
                self._status_var.set("Time calibration: click the end of the excerpt.")
            return

        if self._cal_mode == "time_p1":
            self._time_p1_px = x_px
            self._cal_mode = None
            host = self._image_frame
            duration = simpledialog.askfloat(
                "Excerpt duration",
                "Total duration of the excerpt (seconds):",
                minvalue=0.001,
                parent=host,
            )
            if duration is None:
                self._time_p0_px = self._time_p1_px = None
                self._update_calibration_label()
                return
            self._duration_s = float(duration)
            self._rebuild_maps()

    def _on_press(self, event) -> None:
        if event.inaxes != self._ax:
            return
        if self._cal_mode is not None:
            if event.button == 1:
                self._handle_calibration_click(event)
            return
        super()._on_press(event)

    def _event_to_data(self, event) -> Tuple[float, int]:
        assert self._ax is not None
        x, y = self._ax.transData.inverted().transform((event.x, event.y))
        return max(0.0, float(x)), snap_semitone(y)

    def _redraw_overlays(self) -> None:
        if not self._ax or not self._canvas or not self._is_calibrated():
            return
        self._clear_overlays()
        self._draw_block_overlays()
        self._canvas.draw_idle()

    def _on_pick_toggle(self) -> None:
        if self._pick_mode.get():
            if not self._canvas_ready_for_pick():
                messagebox.showwarning("Warning", "Load an image first.")
                self._pick_mode.set(False)
                return
            if not self._is_calibrated():
                messagebox.showwarning("Calibration required", CALIBRATION_NOTE + "\n\nCalibrate both axes first.")
                self._pick_mode.set(False)


def main() -> None:
    """Launch standalone image-based VD10 picker."""
    root = tk.Tk()
    root.title("Granular_v2 — VD10 registral trajectory (image)")
    root.geometry("1200x720")
    from .logging_config import configure_logging

    configure_logging()
    TrajectoryImageTab(root)
    root.mainloop()


if __name__ == "__main__":
    main()
