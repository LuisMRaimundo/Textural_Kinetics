# Changelog

## 1.0.7

- **Fix (VD4):** `granularity_metrics()` computes IOI CV, granularity index, and burstiness on **unique fused onsets** (τ = 2 ms anchor merge); raw diagnostics (`ioi_cv_raw`, `granularity_index_raw`, `sync_fraction`, `events_per_second_raw`) retained.
- **Export:** `global_event_rates()` exposes VD4 diagnostic keys and per-field `definition` strings.
- **Tests:** VD4 acceptance tests (doubled grid, no-simultaneity parity); `test_granularity_axioms.py` extended (6 tests).
- **Corpus:** Refrozen `musicological_regression_inspection` report; `sparse_homophony.json` `events_per_second` → 0.75.
- **Docs:** Full sync — `METRIC_SEMANTICS.md`, `FORMULAS.md`, `MANUAL_METRICAS.md`, `MANUAL_TECNICO.md` §5–6, `CORPUS_REFERENCIA.md`, golden-values decision, regression fixtures catalogue, `TEST_QUALITY_AUDIT.md`.

## 1.0.6

- **Docs:** `docs/MANUAL_TECNICO.md` (tutorial + full formulas & algorithms), `MANUAL_METRICAS.md`, `CORPUS_REFERENCIA.md`, docs index.
- **Heatmaps:** Publication style (`heatmap_style.py`), custom palettes, robust contrast.
- **Fix:** GUI heatmap import (`extract_measure_starts_from_score` from `heatmaps`).
- **Docs sync:** README CI test count (147 collected), coverage ~91% (91.48%, threshold 72%); `current_rating.md` v1.0.6; corpus fixture count (3); `LIMITATIONS` coincidence fix version (1.0.1).

## 1.0.5

- **Engineering:** Central `offsets.py` + `audit.py`; offset audit tests on corpus; `tempo_audit.warnings` + `tempo_model`.
- **Fix:** `onset_extraction`, MIDI fallback (`input_layer`), Mustextu legacy XML path.
- **CI:** Windows + Ubuntu; mypy on core package. See `docs/OFFSET_AUDIT.md`, `docs/ENGINEERING_95.md`.
- **Release:** `NOTICE.md`, `CITATION.cff`, one-click installers (`installers/`, `INSTALL-*.bat|.sh|.command`), README legal & acknowledgements (aligned with Music_anisotropy).

## 1.0.4

- **Fix:** `timebase.build_tempo_segments` and `note_extraction` use `getOffsetInHierarchy` (measure-local `.offset` collapsed multi-bar timelines).
- **Fix:** Regenerated `corpus/reference/sparse_homophony.json` (was locking in collapsed span).
- **Tests:** `test_global_offsets_integration.py` (file-based multi-measure path).

## 1.0.3

- **Fix:** `build_seconds_map` reads float boundaries from `metronomeMarkBoundaries()` via `_boundary_offset` (was silently wrong for multi-tempo scores: e.g. fn(4.0) 6.0 → 3.0 s).
- **Audit:** `tempo_audit` in `analysis.json` (source, fallback, segment count).
- **Tests:** `test_util_tempo_branches.py` (11 tests); parity tests tightened.
- **Docs:** `docs/LIMITATIONS.md` (stepwise tempo).

## 1.0.2

- GUI (`granular_v2.gui`), activity plots (`plots.py`).
- Corpus: 3 Granularidade fixtures + `compare_all.py`.
- Tempo parity: `timebase_parity.py`, `test_util_tempo_parity.py`.

## 1.0.1

- **Fix:** Mustextu `_merge_coincident_onsets` uses group **anchor** (no transitive chaining).
- **Tests:** coincidence merge adversarial cases; IOI/burstiness axioms; timebase segments; tie merge.

## 1.0.0

- Fused pipeline: event rates (s/ms/bar), activity granularity, Mustextu, three heatmaps, optional partitional layer.
