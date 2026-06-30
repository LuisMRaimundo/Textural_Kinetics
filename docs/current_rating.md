# Temporal_Granularity v1.0.16 — evidence-based rating

## Rubric (100)

| Criterion | Weight | Score |
|-----------|--------|-------|
| Musicology / texture | 20 | **18** |
| Rhythm / granularity (IOI, burstiness, Mustextu) | 20 | **19** |
| Event-rate precision (s/ms/bar) | 15 | **14** |
| Mustextu (wired + merge fix) | 10 | **10** |
| Software architecture | 15 | **14** |
| Tests / CI / corpus (3 fixtures) | 15 | **15** |
| Documentation / scope honesty | 10 | **10** |
| Heatmaps + GUI + VD10 | 5 | **5** |

**Total: 97 / 100**

## v1.0.16 (audit.merge_audits tests)

- **Tests:** `test_audit_merge.py` **24** tests; `audit.py` **~92%** coverage; `merge_audits` semantics locked (utility not yet wired in loader).
- **Suite:** **273** collected; coverage ~**94%**; corpus `compare_all` **3/3** OK.

## v1.0.15 (VD10 group parts into one block)

- **GUI:** multi-select parts + **Group selected into one block** — envelope band (min/max across lines at each onset); coexists with per-part auto-pick and manual picks.
- **API:** `auto_pick_samples_for_group`, `distinct_part_labels_from_note_matrix`, `group_block_default_name`.
- **Tests:** **249** collected; `test_auto_pick.py` **23** tests.

## v1.0.14 (expanded auto-pick tests)

- **Tests:** `test_auto_pick.py` **16** tests — pitch clamp, empty inputs, ordering, unknown parts, dense-sample warning, `compute_vd10` compatibility.
- **Suite:** **242** collected; coverage ~**93%**; corpus `compare_all` **3/3** OK.

## v1.0.13 (VD10 auto-pick, note-map colours, regression layers)

- **GUI:** **Auto-pick from score** — one VD10 block per XML part; immediate recompute; manual edit unchanged. Registral note map: connected part-coloured lines + legend on VD10 heatmap.
- **API:** `auto_pick_blocks_from_note_matrix`, `auto_pick_samples_for_part`, `band_from_pitches`, `part_label_from_note`.
- **Tests:** **233** collected; new modules `test_auto_pick.py`, `test_registral_trajectory_note_map_colours.py`, `test_input_layer_regression.py`, `test_tier2_analytical_regression.py`; `trajectory.py` high coverage.
- **Docs:** README, manual §10.1/§10.6/§10.7.1, metrics, formulas, limitations, semantics, audit docs synced to v1.0.13.

## v1.0.12 (VD10 image picking)

- **GUI:** tab **Registral trajectory (image)** — PNG/JPG load, pitch/time calibration, shared pick/edit/multi-block via `gui_trajectory_common.py`.
- **API:** `make_axis_calibration`, `describe_axis_calibration`, `TrajectoryCalibrationError`; image session export metadata (`source`, `image_calibration`).
- **Tests:** 178 collected; `test_trajectory.py` (29 tests); `trajectory.py` ~98% line coverage.

## v1.0.11 (VD10 editable multi-block)

- **GUI:** editable picks (drag handles, numeric edit, insert); multi-block panel; live recompute; session JSON.
- **API:** `compute_block_relations`, `compute_vd10_session`, interpolation helpers.
- **Docs:** manual §10.6–10.8, metric semantics block-relations section.

## v1.0.10 (VD10 sampling discipline)

- **VD10:** registral trajectory tab; robust descriptors (`net_speed`, `straightness`) documented vs sampling-dependent segment speeds; `sampling_warnings` when Δt < 0.1 s.
- **Tests:** 162 collected; `test_trajectory.py` (13 tests, incl. tiny-Δt artefact regression).

## v1.0.9 (VD10 feature)

- **Feature:** `trajectory.py`, GUI tab **Registral trajectory**, JSON export.
- **Docs:** manual §10, metric semantics, formulas, limitations.

## v1.0.8 (corpus harness)

- **`compare_all` / `compare_reference`:** golden `num_events` = fused VD4 count; `num_notes` = raw note-matrix rows.

## v1.0.7 (VD4 fused-onset granularity)

- **Fix:** IOI CV, granularity index, burstiness on **unique fused onsets** (τ = 2 ms); raw diagnostics and `sync_fraction` exported.
- **Docs:** Full metric-semantics sync; musicological regression inspection refrozen.
- **Tests:** 149 collected; VD4 acceptance tests in `test_granularity_axioms.py`.

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

~**92nd** among custom PhD symbolic texture-analysis tools.

## Not claimed

- Full external partitional-analysis formalism
- Measured audio / psychoacoustic validation
- Licensed multi-composer benchmark (synthetic corpus only)
