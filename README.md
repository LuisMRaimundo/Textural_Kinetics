# Granularity Analyser

**Fused symbolic temporal-density analyzer** for **MusicXML** and **MIDI** scores.

Granularity Analyser combines precise **event rates** (per second, millisecond, bar), **activity granularity**, **Mustextu** horizontal coincidence density (LCM/GCD onset structure), and three **pitch–time heatmaps** (basic, advanced, spectral). It is symbolic notation analysis — not audio, perception, or harmonic function.

**Package version:** 1.0.6 (`granular_v2/__init__.py`)  
**Python:** ≥ 3.10

**Structure:** `granular_v2/` (loader, timebase, event rates, Mustextu, heatmaps, GUI) + `corpus/` (fixtures & regression).

**CI:** GitHub Actions — **62** tests, coverage ≥72% (~**82%**), corpus comparison (`compare_all.py`), mypy on core timeline modules — see `.github/workflows/ci.yml`.

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
