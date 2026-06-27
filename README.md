# Granularity Analyser

**Fused symbolic temporal-density analyzer** for **MusicXML** and **MIDI** scores.

Granularity Analyser combines precise **event rates** (per second, millisecond, bar), **activity granularity**, **Mustextu** horizontal coincidence density (LCM/GCD onset structure), three **pitch–time heatmaps** (basic, advanced, spectral), and **VD10 registral trajectory** (interactive registral displacement on the heatmap or on a calibrated score image). It is symbolic notation analysis — not audio, perception, or harmonic function.

**Package version:** 1.0.16 (`granular_v2/__init__.py`)  
**Python:** ≥ 3.10

**Structure:** `granular_v2/` (loader, timebase, event rates, Mustextu, heatmaps, trajectory/VD10, GUI) + `corpus/` (fixtures & regression).

**CI:** GitHub Actions + CircleCI — **273** tests, coverage ≥72% (~**94%**), corpus comparison (`compare_all.py`), mypy on core timeline modules — see `.github/workflows/ci.yml`.

## Documentation

| Document | Description |
|----------|-------------|
| **[docs/MANUAL_TECNICO.md](docs/MANUAL_TECNICO.md)** | **Full technical manual** (tutorial + formulas + algorithms) |
| [docs/MANUAL_METRICAS.md](docs/MANUAL_METRICAS.md) | Quick metric reference |
| [docs/METRIC_SEMANTICS.md](docs/METRIC_SEMANTICS.md) | **Metric semantics & interpretive limits** (EPS, IOI CV, synchrony, density) |
| [docs/FORMULAS.md](docs/FORMULAS.md) | Compact formula sheet |
| [docs/LIMITATIONS.md](docs/LIMITATIONS.md) | Scope and tempo model |
| [docs/CORPUS_REFERENCIA.md](docs/CORPUS_REFERENCIA.md) | Regression corpus |
| [docs/README.md](docs/README.md) | Documentation index |

## Heatmaps

Publication-style rendering (`granular_blue` / `granular_ember` palettes, percentile contrast, 200 DPI export). See manual §9.

## Programmatic usage

```python
from granular_v2 import run_analysis, default_analysis_config

result = run_analysis("score.musicxml", default_analysis_config(), output_dir="out")
print(result["event_rates"]["global"]["events_per_second"])
print(result["mustextu_summary"]["rate_events_per_second"])
print(result["tempo_audit"])
```

**VD10 registral trajectory** (user-defined textural block on the heatmap):

```python
from granular_v2.trajectory import compute_vd10, export_vd10_json

samples = [
    {"time_s": 0.0, "low": 60, "high": 64},
    {"time_s": 2.0, "low": 68, "high": 72},
]
vd10 = compute_vd10(samples)
print(vd10["summary"])  # uses net_speed (robust); inspect segments for mean/max
print(vd10["aggregates"]["straightness"])
export_vd10_json(vd10, "out/vd10_registral_trajectory.json")
```

**Multi-block session** (several independent textural blocks + pairwise relations):

```python
from granular_v2.trajectory import compute_vd10_session, export_vd10_session_json

session = compute_vd10_session([
    {"id": "block_a", "name": "Upper", "samples": [...]},
    {"id": "block_b", "name": "Lower", "samples": [...]},
])
print(session["relations"]["pairs"])
export_vd10_session_json(session, "out/vd10_session.json")
```

**Auto-pick from note matrix** (one VD10 block per XML part; chord onsets merged):

```python
from granular_v2.trajectory import auto_pick_blocks_from_note_matrix, compute_vd10_session

picked = auto_pick_blocks_from_note_matrix(note_matrix)
session = compute_vd10_session(picked["blocks"])
print(picked["stats"])  # num_parts, total_samples, computable_parts, …
```

**Image-based picking** (proportional graphic scores — linear pixel↔pitch/time calibration):

```python
from granular_v2.trajectory import make_axis_calibration, describe_axis_calibration

map_pitch = make_axis_calibration(p0_px=120.0, p0_val=48.0, p1_px=420.0, p1_val=72.0)
map_time = make_axis_calibration(p0_px=10.0, p0_val=0.0, p1_px=210.0, p1_val=12.5)
# map_pitch(y_px) → semitones; map_time(x_px) → seconds
```

**VD10 interpretation:** anchor thesis claims on **`net_speed`** and **`straightness`**; `mean_speed` / `max_speed` depend on pick spacing (see `sampling_warnings` when segment Δt < 0.1 s). Full semantics: [docs/METRIC_SEMANTICS.md](docs/METRIC_SEMANTICS.md) §VD10.

## One-click install (no Python knowledge required)

Download or clone the project, then use **one file** for your system:

| System | First-time install | Later (already installed) |
|--------|-------------------|---------------------------|
| **Windows 10/11** | Double-click **installers/windows/INSTALL.bat** (or **INSTALL-WINDOWS.bat** at repo root) | **START-Granularity.bat** |
| **macOS** | Double-click **INSTALL-MAC.command** | **START-Granularity.command** |
| **Linux** | **bash installers/linux/install-easy.sh** (or **INSTALL-LINUX.sh**) | **./START-Granularity.sh** |

The installer installs Python 3.10+ if needed, creates `.venv/`, installs dependencies, and opens the **desktop GUI** (Tkinter). Details: [installers/README.md](installers/README.md).

## Manual install (developers)

```bash
pip install -e ".[dev,full]"
```

Runtime-only deps (used by installers): `requirements-app.txt`.

## CLI

```bash
python -m granular_v2.run score.musicxml -o out
python -m granular_v2.run score.musicxml -o out --no-heatmaps --partitional
```

## GUI

```bash
python -m granular_v2.gui
```

Tabs:

- **Analysis** — event rates, heatmap pop-outs, JSON export.
- **Registral trajectory** — VD10 on the embedded advanced heatmap (part-coloured registral lines; **Auto-pick from score**; **Group selected parts** into one envelope block; editable multi-block picking; drag/edit/insert; live recompute; block relations; session JSON).
- **Registral trajectory (image)** — VD10 on a PNG/JPG excerpt with two-axis calibration (pitch + time); same pick/edit/multi-block workflow; auto-pick when a score is loaded on Analysis.

Standalone image picker (no score required):

```bash
python -m granular_v2.gui_trajectory_image
```

Windows: `run_gui.bat` or **START-Granularity.bat** (after installer).

## Tests and corpus

```bash
pytest tests -q
python corpus/scripts/compare_all.py
```

Corpus fixtures: `corpus/fixtures/*.musicxml`.

## Limitations (summary)

* Symbolic notation only; stepwise tempo plateaus (not continuous accelerandi).
* See `docs/LIMITATIONS.md` and `tempo_audit` in exported JSON (`tempo_model`, `warnings`).

## Legal and citation

| File | Purpose |
|------|---------|
| **[NOTICE.md](NOTICE.md)** | Copyright and use terms (proprietary; no open-source licence granted). |
| **[CITATION.cff](CITATION.cff)** | Citation metadata for software recognition. |

## Installers (optional)

**Repository:** https://github.com/LuisMRaimundo/Granularity-Analyser

End users without Python: see **installers/** — especially on Windows, double-click **`installers/windows/INSTALL.bat`**.

| Folder | Standard install | Portable build (PyInstaller) |
|--------|------------------|------------------------------|
| [installers/windows/](installers/windows/) | **INSTALL.bat** | *Not in git* |
| [installers/mac/](installers/mac/) | install-easy.sh / install.sh | *Not in git* |
| [installers/linux/](installers/linux/) | install-easy.sh / install.sh | *Not in git* |

Built `.exe` / `.app` / `.dmg` / `.tar.gz` files are **not** in git — use GitHub Releases if you distribute frozen builds.

## Acknowledgements

This project was developed by **Luís Raimundo** with the support and funding of the **Fundação para a Ciência e a Tecnologia (FCT)** and **Universidade NOVA de Lisboa**.

**Funding DOI:** https://doi.org/10.54499/2020.08817.BD

The author also gratefully acknowledges **Isabel Pires** for her support throughout the development of this work.
