# Granular_v2 v1.0.6 — evidence-based rating

## Rubric (100)

| Criterion | Weight | Score |
|-----------|--------|-------|
| Musicology / texture | 20 | **17** |
| Rhythm / granularity (IOI, burstiness, Mustextu) | 20 | **18** |
| Event-rate precision (s/ms/bar) | 15 | **14** |
| Mustextu (wired + merge fix) | 10 | **10** |
| Software architecture | 15 | **14** |
| Tests / CI / corpus (3 fixtures) | 15 | **15** |
| Documentation / scope honesty | 10 | **9** |
| Heatmaps + GUI | 5 | **5** |

**Total: 95 / 100**

## v1.0.6 (documentation & heatmaps)

- Full **`docs/MANUAL_TECNICO.md`** bundle; metric quick reference; corpus index.
- Publication heatmap style (`heatmap_style.py`); GUI import fix for measure starts.
- Package version **1.0.6** aligned across `__init__.py`, `pyproject.toml`, `CITATION.cff`, manuals.

## v1.0.5 (engineering audit)

- Offset class closed in package; corpus + static tests; `tempo_audit.warnings`.
- CI: Windows/Ubuntu, mypy on core timeline modules.
- See `docs/ENGINEERING_95.md` for path to 95.

## v1.0.4 (critical fix — global offsets)

- `timebase` + `note_extraction` use score-global offsets (`getOffsetInHierarchy`).
- Multi-measure timelines and event rates no longer collapsed to measure-local span.

## v1.0.3

- Multi-tempo `build_seconds_map` boundary bug fixed.
- `tempo_audit` in exported JSON.

## v1.0.2 additions

- Tempo parity tests (`timebase` vs `util_tempo`) on synthetic + corpus fixtures
- Corpus: `sparse_homophony`, `dense_onset_burst`, `layered_async` + `compare_all.py`
- Tkinter GUI: analysis, plots, three heatmaps, JSON export
- Coincidence merge anchor fix (v1.0.1)

## Doctoral percentile

~**90th** among custom PhD symbolic texture-analysis tools.

## Not claimed

- Full PARSEMAT / Gentil-Nunes equivalence
- Measured audio / psychoacoustic validation
- Licensed multi-composer benchmark (synthetic corpus only)
