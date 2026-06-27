# Changelog

## 1.0.16

- **Tests:** `test_audit_merge.py` (**24** tests) — `merge_audits` warning concatenation, scalar metadata override, shallow nested-dict replace, malformed warning structures, loader-shaped integration smoke, JSON serialisability; `audit.py` **~92%** line coverage.
- **Docs:** README, `MANUAL_TECNICO.md` §14, `TEST_QUALITY_AUDIT.md`, `current_rating.md`; version **1.0.16**.

Suite: **273** tests; coverage ~**94%** on `granular_v2`; corpus `compare_all` **3/3** OK.

## 1.0.15

- **VD10 group parts into one block:** multi-select part labels in the trajectory tab side panel; **Group selected into one block** builds envelope samples via `auto_pick_samples_for_group` (min–max pitch across selected parts at each onset); appends block without replacing existing ones; VD10 and block relations unchanged.
- **API:** `auto_pick_samples_for_group`, `distinct_part_labels_from_note_matrix`, `group_block_default_name` in `trajectory.py`.
- **Tests:** `test_auto_pick.py` **23** tests (+7 group envelope cases).
- **Docs:** README, manuals, audit docs; version **1.0.15**.

Suite: **249** tests; coverage ~**93%** on `granular_v2`; corpus `compare_all` **3/3** OK.

## 1.0.14

- **Tests:** expanded `test_auto_pick.py` from 7 → **16** — empty pitch list, MIDI 127 clamp, empty matrix stats, unordered onsets, strictly increasing times, unknown-part grouping, stable block IDs, dense-sample warning, direct `compute_vd10` compatibility (plus existing chord merge, session, determinism).
- **Docs:** README, `MANUAL_TECNICO.md` §14, `TEST_QUALITY_AUDIT.md`, `current_rating.md`; version **1.0.14**.

Suite: **242** tests; coverage ~**93%** on `granular_v2`; corpus `compare_all` **3/3** OK.

## 1.0.13

- **VD10 auto-pick from score:** toolbar button builds **one block per MusicXML part** from the loaded note matrix (one sample per onset; chord tones in the same part merge to a min–max band); confirms before replacing blocks; recomputes VD10 immediately; manual edit/undo unchanged.
- **API:** `auto_pick_blocks_from_note_matrix`, `auto_pick_samples_for_part`, `part_label_from_note`, `band_from_pitches` in `trajectory.py` (pure, unit-tested).
- **Registral note map (heatmap tab):** each extracted XML part drawn as a **connected registral line** in a deterministic colour with a **Part** legend (`heatmaps.py`; `overlay_points` on VD10 heatmap).
- **Regression layers:** Tier-2 analytical/corpus invariants (`test_tier2_analytical_regression.py`); input-layer loading (`test_input_layer_regression.py`); note-map colours (`test_registral_trajectory_note_map_colours.py`); auto-pick (`test_auto_pick.py`).
- **VD10 fix (1.0.13 baseline):** `shape_hint` uses \|straightness\| for descending trajectories (merged earlier on main).
- **Docs:** README, `MANUAL_TECNICO.md` §10.1/§10.6/§14, `MANUAL_METRICAS.md`, `METRIC_SEMANTICS.md`, `FORMULAS.md`, `LIMITATIONS.md`, `current_rating.md`, `TEST_QUALITY_AUDIT.md`, `CITATION.cff`; version **1.0.13**.

### Tests

- `test_auto_pick.py` (7) — part grouping, chord merge, session compute, determinism.
- `test_registral_trajectory_note_map_colours.py` (8) — per-part line colours and legend.
- `test_input_layer_regression.py` (16) — MusicXML/MIDI load, ties, repeats, errors.
- `test_tier2_analytical_regression.py` (23) — corpus invariants and cross-fixture ordering.

Suite: **233** tests; coverage ~**93%** on `granular_v2`; corpus `compare_all` **3/3** OK.

## 1.0.12

- **VD10 image picking:** new tab **Registral trajectory (image)** (`gui_trajectory_image.py`) — load PNG/JPG excerpt, two-axis calibration (pitch + time), same multi-block pick/edit/compute/export as heatmap tab.
- **Shared GUI:** `gui_trajectory_common.py` factors session state, side panel, and pick/edit handlers used by heatmap and image tabs (heatmap tab behaviour unchanged).
- **API:** `make_axis_calibration`, `describe_axis_calibration`, `TrajectoryCalibrationError` in `trajectory.py` (pure, unit-tested linear pixel→value maps).
- **Export:** image session JSON includes `source: "image"` and `image_calibration` reference points for reproducibility.
- **Standalone:** `python -m granular_v2.gui_trajectory_image` launches image picker without a score.

- **Docs:** README, `MANUAL_TECNICO.md` §10.9, `MANUAL_METRICAS.md`, `FORMULAS.md`, `METRIC_SEMANTICS.md`, `LIMITATIONS.md`, `current_rating.md`, `TEST_QUALITY_AUDIT.md`; version **1.0.12**.

### Tests (VD10 multi-block API)

- `test_block_relations_converging_same_direction` — pairwise converging + same_direction labels.
- `test_block_relations_diverging_opposite_direction` — pairwise diverging + opposite_direction labels.
- `test_block_relations_parallel_and_no_overlap` — constant separation + disjoint time spans.
- `test_vd10_session_two_blocks` — per-block VD10 + relations in one session.
- `test_vd10_session_single_sample_block_error` — incomplete block yields `vd10_error`, no relations.
- `test_interpolate_band_midpoint_and_clamp` — linear midpoint + edge clamp + single-sample hold.
- `test_export_vd10_session_json` — multi-block session JSON round-trip.

Suite: **173** tests; `trajectory.py` coverage **~96%** (Tier-1 VD10 multi-block API complete).

### Tests (VD10 edge cases)

- `test_describe_axis_calibration_rejects_equal_pixels` — serialisable calibration rejects coincident reference pixels.
- `test_unsorted_samples_sorted_before_compute` — out-of-order picks sorted silently before VD10.
- `test_vd10_session_propagates_trajectory_error` — duplicate-time block surfaces `vd10_error`.
- `test_block_relations_static_direction_labels` — `both_static` and `one_static` pair directions.
- `test_interpolate_band_empty_samples` — empty pick list defaults to MIDI 60.

Suite: **178** tests; `trajectory.py` **~98%** line coverage (VD10 edge cases complete).

## 1.0.11

- **VD10 GUI — editable picks:** select samples on heatmap or list; drag band (vertical), top/bottom handles, or time axis; double-click row for numeric edit; insert between samples or right-click centre line; undo/delete; live recompute.
- **VD10 multi-block:** blocks panel (add/rename/delete/active); per-block colours; `compute_vd10` once per block via `compute_vd10_session`; `compute_block_relations` for pairwise converging/diverging/parallel inter-centre motion; session JSON export (`export_vd10_session_json`).
- **API:** `interpolate_band_at_time`, `interpolate_centre_at_times`, `compute_block_relations`, `compute_vd10_session`, `export_vd10_session_json`.
- **Docs:** README, `MANUAL_TECNICO.md` §10.6–10.7, `MANUAL_METRICAS.md`, `FORMULAS.md`, `METRIC_SEMANTICS.md`, `LIMITATIONS.md`, audit docs; version **1.0.11**.

## 1.0.10

- **VD10 sampling discipline:** `median_speed`, `min_segment_dt_s`, `sampling_warnings`, `descriptor_roles` (robust vs sampling-dependent); GUI lists segment `dt_s` and warns when Δt < 0.1 s.
- **VD10 GUI fix:** re-pick at same heatmap x replaces existing sample (avoids duplicate-time errors).
- **Tests:** `tests/test_trajectory.py` (13 tests); suite **162** collected; coverage ~92%.
- **Docs:** robust vs sampling-dependent VD10 interpretation across `METRIC_SEMANTICS.md`, `MANUAL_METRICAS.md`, `MANUAL_TECNICO.md` §10, `FORMULAS.md`, `LIMITATIONS.md`; README and audit docs aligned.

## 1.0.9

- **Feature:** VD10 registral trajectory — `granular_v2/trajectory.py` (pure computation), GUI tab **Registral trajectory** (`gui_trajectory.py`), interactive picking on the advanced pitch×time heatmap, JSON export via `export_vd10_json`.
- **Docs:** README, `MANUAL_TECNICO.md` §9.6, `MANUAL_METRICAS.md`, `FORMULAS.md`, `METRIC_SEMANTICS.md`, `LIMITATIONS.md`, docs index; `CITATION.cff` keywords/abstract; export scope strings in `reports.py`.

## 1.0.8

- **Corpus harness:** `compare_all.py` and `compare_reference.py` freeze canonical VD4 fused `num_events` (`event_rates.global.num_events`); raw note count retained as `num_notes` for traceability. Golden references regenerated.
- **Docs:** README, `CORPUS_REFERENCIA.md`, `TEST_QUALITY_AUDIT.md`, `current_rating.md` aligned to v1.0.8 harness semantics.

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
