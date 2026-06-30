# Metric reference (Textural_Kinetics)

Compact definitions. Full derivations and algorithms: **[MANUAL_TECNICO.md](MANUAL_TECNICO.md)**.  
**Interpretive limits** (what each metric does *not* mean): **[METRIC_SEMANTICS.md](METRIC_SEMANTICS.md)**.

## `num_events` — naming (read carefully)

The export JSON uses **`num_events` in three places with different meanings**:

| JSON path | Meaning |
|-----------|---------|
| Top-level `num_events` | **Raw** note-matrix row count (every extracted note event) |
| `event_rates.global.num_events` | **Fused** unique onsets (τ = 2 ms coincidence merge) |
| `activity_granularity.granularity.num_events` | **Fused** unique onsets (same engine as above) |
| `activity_granularity.num_events` | **Raw** note-matrix row count (duplicate of top-level) |

The GUI status line `N=` shows **top-level (raw)** count. Rate metrics under `event_rates.global` use the **fused** series. Prefer `event_rates.global.num_events_raw` vs `num_events` when comparing fusion effects.

## Event rates (global, under `event_rates.global`)

| Metric | Unit | Formula |
|--------|------|---------|
| `num_events` | count | unique **fused** onsets (τ = 2 ms) — **under `event_rates.global` only** |
| `num_events_raw` | count | raw note-matrix onsets before fusion |
| `sync_fraction` | — | \(1 - \mathrm{num\_events}/\mathrm{num\_events\_raw}\) |
| `events_per_second` | s⁻¹ | \(N_{\mathrm{unique}} / T_{\mathrm{span}}\) on fused series (diagnostic) |
| `events_per_second_raw` | s⁻¹ | \(N_{\mathrm{raw}} / T_{\mathrm{span}}\) |
| `events_per_millisecond` | ms⁻¹ | `events_per_second` / 1000 |

\(T_{\mathrm{span}} = t_{\mathrm{last}} - t_{\mathrm{first}}\) on **fused** onsets (1 s support if degenerate). Not full score duration. **Canonical VD4\_s:** Mustextu `rate_eps` — see [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) §3.

## Per time bin (width \(\Delta\) s, under `event_rates.by_bin_sec.<Δ>`)

| Metric | Formula |
|--------|---------|
| `onset_count_per_bin` | attacks in \([t, t+\Delta)\) |
| `events_per_second_per_bin` | count / \(\Delta\) |
| `events_per_millisecond_per_bin` | `events_per_second_per_bin` / 1000 |
| `active_count_per_bin` | sounding-note overlap count per bin (sustain-inclusive) |

## Per millisecond window (width \(W\) ms, under `event_rates.by_ms_window.<W>`)

Default window widths: **50**, **100**, **500** ms (`AnalysisConfig.ms_rate_windows`).

| Metric | Formula |
|--------|---------|
| `events_per_millisecond_in_window` | count in centred window \([t_c - W/2,\ t_c + W/2)\) / \(W\) (window shrinks if the timeline is shorter than \(W\)) |

## Per bar (under `event_rates.per_bar[]`)

| Metric | Formula |
|--------|---------|
| `events_per_second_in_bar` | onsets in bar / bar duration (s) |
| `events_per_millisecond_in_bar` | `events_per_second_in_bar` / 1000 |
| `events_per_beat_in_bar` | onsets in bar / notated beats |

Aggregate: `event_rates.per_bar_summary` — `mean_events_per_second_in_bar`, `mean_events_per_millisecond_in_bar`, `num_bars`.

## Activity / IOI (VD4 — fused onsets)

| Metric | Formula |
|--------|---------|
| IOI\(_k\) (canonical) | \(t^{\mathrm{fused}}_{k+1} - t^{\mathrm{fused}}_k\) after τ = 2 ms merge |
| `ioi_cv` | \(\sigma_{\mathrm{IOI}} / \mu_{\mathrm{IOI}}\) on fused IOIs |
| `granularity_index` | \(1 / (1 + \mathrm{ioi\_cv})\) |
| `burstiness` | \((\sigma - \mu) / (\sigma + \mu)\) on **fused-onset** counts in **0.5 s** windows |
| `ioi_cv_raw` | IOI CV on raw sorted onsets (includes zero IOIs) |
| `granularity_index_raw` | \(1 / (1 + \mathrm{ioi\_cv\_raw})\) |

Raw IOI list for plots: `inter_onset_intervals()` / `run_activity_granularity.ioi_sec`.

## Mustextu (composite)

| Metric | Formula |
|--------|---------|
| `rate_eps` | \(N_{\mathrm{unique}} / T_{\mathrm{win}}\) (events/s) — **canonical VD4\_s** |
| `rate_eps_raw` | \(N_{\mathrm{raw}} / T_{\mathrm{win}}\) |
| `synchrony_fraction` | \(1 - N_{\mathrm{unique}}/N_{\mathrm{raw}}\) after τ-merge of **all layer** onsets (ms) |
| `granularity_score` | \(\mathrm{clip}( \mathrm{rate\_eps} / \mathrm{gran\_max\_eps},\, 0,\, 1)\) |
| GCD/LCM (regular layers) | analytic coincidence on integer events/beat |

## Heatmaps (symbolic)

| View | Quantity |
|------|----------|
| Basic | \(\log(1 + H_{p,t})\) occupancy |
| Advanced | smoothed, gamma, percentile-scaled \(H\) |
| Spectral | velocity-weighted energy grid \(E_{p,t}\) |

Not measured audio spectra.

## Registral trajectory (VD10)

**Module:** `trajectory.py` · **GUI:** tabs *Registral trajectory* (`gui_trajectory.py`, heatmap) and *Registral trajectory (image)* (`gui_trajectory_image.py`, calibrated excerpt); shared session logic in `gui_trajectory_common.py`

Separate from event-rate **granularity** (VD4): VD10 measures **movement of a user-defined registral band** over time, not attack density.

| Metric | Unit | Formula |
|--------|------|---------|
| `centre` | semitones (MIDI int.) | \((\mathrm{low}+\mathrm{high})/2\) per sample |
| `width` | semitones | \(\mathrm{high}-\mathrm{low}\) |
| `speed_centre` | st/s | \((\mathrm{centre}_{i+1}-\mathrm{centre}_i)/\Delta t\) (signed) |
| `speed_width` | st/s | \((\mathrm{width}_{i+1}-\mathrm{width}_i)/\Delta t\) (signed) |
| `net_displacement` | semitones | \(\mathrm{centre}_{\mathrm{last}}-\mathrm{centre}_{\mathrm{first}}\) |
| `net_speed` | st/s | `net_displacement` / total elapsed time — **headline speed** |
| `total_path` | semitones | \(\sum_i \|\mathrm{centre}_{i+1}-\mathrm{centre}_i\|\) (descriptive) |
| `straightness` | — | `net_displacement` / `total_path` (0 if path = 0) |
| `inflections` | count | sign changes in centre deltas |
| `mean_speed` | st/s | mean of \(\|\mathrm{speed\_centre}\|\) — **sampling-dependent** |
| `median_speed` | st/s | median of \(\|\mathrm{speed\_centre}\|\) — less fragile than max |
| `max_speed` | st/s | max of \(\|\mathrm{speed\_centre}\|\) — **always check `segments[].dt_s`** |
| `min_segment_dt_s` | s | smallest \(\Delta t\) between consecutive picks |

Labels: `direction` (ascending / descending / static), `band_behaviour` (diverging / converging / stable width), `shape_hint` (unidirectional / mixed / undulating). See [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) §VD10.

**Auto-pick (GUI / API):** `auto_pick_blocks_from_note_matrix` — one block per XML `part`, one sample per onset (chord merge). **Group parts:** `auto_pick_samples_for_group` — envelope of selected parts at each onset. Toolbar **Auto-pick from score** and side-panel **Group selected into one block** on trajectory tabs when note matrix is available.

## Block relations (multi-block VD10)

**Function:** `compute_block_relations(blocks)` · **Not** VD8 anisotropy.

| Output | Unit | Meaning |
|--------|------|---------|
| `mean_inter_distance_rate_st_per_s` | st/s | Net change in inter-centre distance over overlap / overlap duration |
| `relation` | — | converging / diverging / parallel (inter-block distance trend) |
| `direction` | — | same_direction / opposite_direction / one_static / both_static (net centre motion) |
| `distance_start_st`, `distance_end_st` | st | Inter-centre distance at overlap endpoints |

## Image axis calibration (VD10 image tab)

**Functions:** `make_axis_calibration`, `describe_axis_calibration` · **Assumption:** linear pixel ↔ pitch (semitones) and pixel ↔ time (seconds). Valid for proportional graphic / spatial scores only.

| Output | Meaning |
|--------|---------|
| `slope`, `intercept` | Linear map \(v = \mathrm{slope} \cdot p + \mathrm{intercept}\) |
| `p0_px`, `p0_val`, `p1_px`, `p1_val` | Reference calibration points |

Session export may include `image_calibration` when picks were made on an image backdrop.
