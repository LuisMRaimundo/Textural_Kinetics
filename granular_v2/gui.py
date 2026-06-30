"""Tkinter GUI — Temporal_Granularity fused analysis."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

log = logging.getLogger(__name__)

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class GranularGUI:
    def __init__(self, root: tk.Tk):
        from .logging_config import configure_logging
        configure_logging()
        self.root = root
        root.title("Temporal_Granularity — temporal density & heatmaps")
        root.geometry("1200x720")
        self.path_var = tk.StringVar(value="(no file)")
        self.status_var = tk.StringVar(value="Open a MusicXML/MIDI file.")
        self.results = None
        self.note_matrix = None
        self.score = None
        self.file_path = None
        self.tempo_audit = {}
        self.trajectory_tab = None
        self._build()

    def _build(self):
        header = tk.Frame(self.root)
        header.pack(fill=tk.X, padx=6, pady=4)
        tk.Button(header, text="Open file", command=self._open).pack(side=tk.LEFT, padx=4)
        tk.Label(header, textvariable=self.path_var, fg="gray").pack(side=tk.LEFT, padx=8)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        analysis_frame = tk.Frame(notebook)
        notebook.add(analysis_frame, text="Analysis")
        self._build_analysis_tab(analysis_frame)

        trajectory_frame = tk.Frame(notebook)
        notebook.add(trajectory_frame, text="Registral trajectory")
        from .gui_trajectory import TrajectoryTab

        self.trajectory_tab = TrajectoryTab(
            trajectory_frame,
            get_note_matrix=lambda: self.note_matrix,
            get_score=lambda: self.score,
            get_file_path=lambda: self.file_path,
        )

        trajectory_image_frame = tk.Frame(notebook)
        notebook.add(trajectory_image_frame, text="Registral trajectory (image)")
        from .gui_trajectory_image import TrajectoryImageTab

        self.trajectory_image_tab = TrajectoryImageTab(
            trajectory_image_frame,
            get_note_matrix=lambda: self.note_matrix,
        )

        tk.Label(self.root, textvariable=self.status_var, fg="blue").pack(pady=4)

    def _build_analysis_tab(self, parent: tk.Frame) -> None:
        frm = tk.Frame(parent)
        frm.pack(pady=12)
        for i, (txt, cmd) in enumerate([
            ("Run analysis", self._run),
            ("Plots", self._plots),
            ("Export JSON", self._export),
            ("Heatmap basic", lambda: self._heatmap("basic")),
            ("Heatmap advanced", lambda: self._heatmap("advanced")),
            ("Heatmap spectral", lambda: self._heatmap("spectral")),
        ]):
            tk.Button(frm, text=txt, command=cmd, width=14).grid(row=i // 3, column=i % 3, padx=4, pady=3)

    def _open(self):
        fp = filedialog.askopenfilename(
            filetypes=[("Scores", "*.musicxml *.xml *.mxl *.mid *.midi"), ("All", "*.*")]
        )
        if not fp:
            return
        try:
            from .loader import load_score_and_note_matrix
            self.score, self.note_matrix, self.tempo_audit = load_score_and_note_matrix(fp)
            self.file_path = fp
            self.results = None
            self.path_var.set(Path(fp).name)
            self.status_var.set(f"Loaded {len(self.note_matrix)} events. Run analysis.")
            if self.trajectory_tab is not None:
                self.trajectory_tab.on_score_loaded()
        except Exception as e:
            log.exception("load failed")
            messagebox.showerror("Error", str(e))

    def _run(self):
        if not self.file_path:
            messagebox.showwarning("Warning", "Open a file first.")
            return
        try:
            from .config import default_analysis_config
            from .fusion import run_full_analysis
            cfg = default_analysis_config()
            cfg.enable_heatmaps = False
            self.results = run_full_analysis(
                self.note_matrix, self.score, cfg, tempo_audit=self.tempo_audit
            )
            g = self.results["event_rates"]["global"]
            self.status_var.set(
                f"events/s={g['events_per_second']:.3f} | "
                f"events/ms={g['events_per_millisecond']:.6f} | "
                f"N={self.results['num_events']}"
            )
        except Exception as e:
            log.exception("analysis failed")
            messagebox.showerror("Error", str(e))

    def _export(self):
        if not self.results:
            messagebox.showwarning("Warning", "Run analysis first.")
            return
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not fp:
            return
        from .reports import export_results_json
        export_results_json(self.results, Path(fp))
        self.status_var.set(f"Saved {fp}")

    def _plots(self):
        if not self.results:
            messagebox.showwarning("Warning", "Run analysis first.")
            return
        if not HAS_MPL:
            messagebox.showwarning("Warning", "matplotlib required.")
            return
        from .plots import plot_activity_granularity
        fig = plot_activity_granularity(self.results)
        win = tk.Toplevel(self.root)
        win.title("Activity & granularity")
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(canvas, win)

    def _heatmap(self, kind: str):
        if not self.note_matrix:
            messagebox.showwarning("Warning", "Open a file first.")
            return
        if not HAS_MPL:
            messagebox.showwarning("Warning", "matplotlib required.")
            return
        from .config import HeatmapConfig
        from .heatmaps import (
            extract_measure_starts_from_score,
            plot_heatmap_advanced,
            plot_heatmap_basic,
            plot_spectral_energy_heatmap,
        )
        cfg = HeatmapConfig()
        mstarts = extract_measure_starts_from_score(self.score) if self.score else []
        if kind == "basic":
            fig = plot_heatmap_basic(self.note_matrix, cfg)
        elif kind == "advanced":
            fig = plot_heatmap_advanced(self.note_matrix, cfg, measure_starts=mstarts)
        else:
            fig = plot_spectral_energy_heatmap(self.note_matrix, cfg, score=self.score)
        win = tk.Toplevel(self.root)
        win.title(f"Heatmap {kind}")
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(canvas, win)


def main():
    root = tk.Tk()
    GranularGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
