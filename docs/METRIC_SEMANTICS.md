# Metric semantics and interpretive limits

**Audience:** Analysts, thesis readers, and maintainers promoting values to golden regression.  
**Status:** Describes the **implemented model** in **Temporal_Granularity** (`granular_v2/`) as of the current export schema (VD4 fused-onset granularity, VD10 registral trajectory, v1.0.16).  
**Companion docs:** [FORMULAS.md](FORMULAS.md), [MANUAL_METRICAS.md](MANUAL_METRICAS.md), [MANUAL_TECNICO.md](MANUAL_TECNICO.md) §5–10.

---

## 1. Scope and methodological status

The metrics documented here are **symbolic, score-derived descriptors** of evental and temporal organisation. They are computed from a **note matrix** (and, for Mustextu, per-part onset lists) produced by the loader and timebase pipeline.

They are **not**:

- direct acoustic or spectral measurements;
- perceptual or psychoacoustic loudness or roughness;
- performance timing from audio;
- harmonic or voice-leading analysis.

They describe how **this implementation** quantifies attacks, overlaps, and multi-layer coincidence on a notated timeline. Musicological claims should treat them as **model outputs**, to be read together with curves and structural counts—not as self-evident facts about the score or a performance.

---

## 2. Basic event vocabulary

| Term | Meaning in this codebase |
|------|--------------------------|
| **Event** | One row in the note matrix after loader extraction (typically one symbolic pitch attack). Several events may share the same onset time (chords, homorhythm across parts). |
| **Onset** | The attack time of an event: `onset_sec` (or `onset_beats` if seconds unavailable). |
| **Raw onset** | One onset value per note-matrix row (not deduplicated). |
| **Fused / unique onset (VD4)** | After `merge_coincident_onsets`: anchor-based merge within **τ = 2 ms** (`COINCIDENCE_TOL_SEC`); group time = mean of members. Basis for VD4 IOI CV, granularity index, burstiness, and span-referenced EPS global. |
| **Coincident onset** | Two or more raw onsets whose times fall within τ of the **group anchor** (first onset of the group; no transitive chaining). |
| **Active event** | An event whose sounding interval `[onset, onset + duration)` overlaps a time bin. |
| **Onset count per bin** | Number of events whose onset falls in bin \([t, t+\Delta)\). Stored as `onset_density[j]` (float count). |
| **Active count per bin** | Number of events sounding during bin \(j\) (overlap with \([b_j, b_{j+1})\)). Stored as `active_density[j]`. |
| **Bin-based density** | Per-bin counts or rates derived from `TemporalDensityAnalyzer` (`onset_density`, `active_density`, `events_per_sec_per_bin = onset_count / Δ`). |
| **Window-based activity rate** | Onsets counted in a sliding window \([t_c - W/2, t_c + W/2)\), divided by \(W\) → `activity_rate.events_per_sec`. |

**VD4 horizontal granularity** measures **temporal spacing between fused attack times**, not vertical sonority thickness. Vertical simultaneity is reported separately via `sync_fraction` (note-matrix fusion) and Mustextu `synchrony_fraction` (multi-layer pool).

**Raw IOI helper:** `inter_onset_intervals()` keeps **raw** semantics (includes zero IOIs) for plotting and `run_activity_granularity.ioi_sec`; it is **not** the basis for exported VD4 scalars.

---

## 3. EPS global / `events_per_second`

**Module:** `activity_granularity.granularity_metrics` → `event_rates.global_event_rates`.

**Implementation (v1.0.7+):**

```text
raw_onsets  = sorted onset_sec per note-matrix row
merged      = merge_coincident_onsets(raw_onsets, tau=2 ms)
N_unique    = len(merged)
N_raw       = len(raw_onsets)
span        = max(merged) - min(merged)   # if N_unique < 2 → span := 0, support := 1.0
events_per_second = N_unique / support
events_per_second_raw = N_raw / support   # diagnostic
```

Equivalent export definition: **unique fused onsets / (t_last − t_first)** on the fused series — a **span-referenced diagnostic**.

**Canonical VD4 rate (thesis):** Mustextu **`rate_eps`** (`mustextu_summary.rate_events_per_second`), computed over the Mustextu window with multi-layer τ-merge. Do **not** equate `events_per_second` with `rate_eps` without aligning window and layer definitions.

**Interpretive limits:**

- Denominator is **fused onset span only**, not full notated duration or Mustextu window length.
- Homorhythmic or chordal scores: `events_per_second` reflects **horizontal attack times** after 2 ms fusion; `events_per_second_raw` retains pre-fusion count on the same span support.
- Sustained overlap after the last fused onset is not described by EPS global (use **active density**).

---

## 4. IOI and IOI CV

**Module:** `activity_granularity.granularity_metrics` (canonical); `inter_onset_intervals` (raw diagnostic / plots only).

**Implementation (VD4 — canonical export):**

```text
merged = merge_coincident_onsets(get_onsets_sorted(note_matrix), tau=2 ms)
IOI_k  = merged[k+1] - merged[k]          # no zero IOIs from vertical simultaneity
ioi_mean = mean(IOI)
ioi_std  = std(IOI)
ioi_cv   = ioi_std / ioi_mean             # NaN if mean ≤ 0
```

**Raw diagnostics** (pre-fusion, same note matrix):

```text
raw_iois = diff(sorted raw onsets)        # includes zero IOIs when simultaneous
ioi_cv_raw = std(raw_iois) / mean(raw_iois)
granularity_index_raw = 1 / (1 + ioi_cv_raw)
```

**Interpretive warning:**

- **`ioi_cv`** measures irregularity of the **horizontal fused-onset pulse** (Annex VD4).
- **`ioi_cv_raw`** inflates when chords or homorhythm insert zero IOIs in the raw stream (`regular_homorhythm`: fused `ioi_cv = 0`, raw `ioi_cv_raw ≈ 1.46`).
- For plotting the full attack stream including simultaneities, use `run_activity_granularity.ioi_sec` (raw `inter_onset_intervals`).

---

## 5. `granularity_index`

**Implementation** (`granularity_metrics`):

```text
granularity_index = 1 / (1 + ioi_cv)           # on fused IOIs; 0.5 if ioi_cv non-finite
granularity_index_raw = 1 / (1 + ioi_cv_raw) # diagnostic
```

**Interpretation:**

- Inversely related to **IOI CV on fused unique onsets** (§4).
- High chordal density with a regular fused grid can yield **`granularity_index = 1.0`** even when `num_events_raw` ≫ `num_events`.
- Read together with `sync_fraction`, EPS diagnostics, density curves, and Mustextu `rate_eps`.

---

## 6. `burstiness`

**Implementation** (`granularity_metrics`, v1.0.7+):

1. Fuse onsets (§4); let \(T = \max(\mathrm{merged}) - \min(\mathrm{merged})\).
2. Fixed window **0.5 s** (`BURST_WINDOW_SEC`); bin edges anchored at \(\min(\mathrm{merged})\).
3. Histogram **fused-onset** counts \(c_k\) across bins; \(\mu = \mathrm{mean}(c_k)\), \(\sigma = \mathrm{std}(c_k)\).
4. `burstiness = (σ − μ) / (σ + μ)` if \((\sigma + \mu) > 0\) and ≥ 2 bins, else `NaN` / omitted in export when undefined.

**Interpretation:**

- Unevenness of **fused horizontal attack times** across 0.5 s windows (VD4\_burst).
- **Not** identical to `density_by_bins` onset counts (which count raw matrix rows per bin).
- Positive → clustered fused attacks; sustained overlap does not enter burstiness.

---

## 7. `sync_fraction` (VD4) vs `synchrony_fraction` (Mustextu)

### 7.1 `sync_fraction` — note-matrix fusion (VD4)

**Export:** `event_rates.global.sync_fraction`, `granularity_metrics.sync_fraction`.

```text
sync_fraction = 1 - N_unique / N_raw    # 0 if N_raw == 0
```

τ = 2 ms anchor merge on **all note-matrix onsets** (single pool, not per-part layers). Measures how many raw attacks collapse to the same horizontal time within tolerance.

### 7.2 `synchrony_fraction` — Mustextu multi-layer pool

**Export name:** `synchrony_fraction` in `mustextu_summary` / composite JSON.

**Module:** `mustextu/horizontal_density.py` (`compute_horizontal_density_from_onsets`).

**Procedure:**

1. For each part/layer, collect onset times in ms (optionally skip grace notes).
2. Concatenate all layer lists → `all_onsets`; `total_raw = len(all_onsets)`.
3. Sort and **merge** within `coincidence_ms_effective` (default **2.0 ms**; adaptive optional). Anchor-based merge.
4. `synchrony_fraction = 1 - total_unique / total_raw`.

**What it measures:** redundant **layer onset entries** after cross-layer τ-merge — not identical to `sync_fraction` when layer lists differ from the flat note matrix or grace policy diverges.

**Related Mustextu fields (not interchangeable):**

| Field | Meaning |
|-------|---------|
| `max_multiplicity` | Largest merge-group size after coincidence merge |
| `coincident_groups` | Count of merge groups with multiplicity ≥ 2 |
| `avg_multiplicity` | `total_raw / total_unique` |
| `rate_eps` | `total_unique / (window_ms/1000)` — **canonical VD4\_s rate** |
| `rate_eps_raw` | `total_raw / (window_ms/1000)` |

**`max_simultaneous_pitches`** (inspection helper): max note-matrix rows sharing identical `onset_sec`. Can be high while Mustextu `synchrony_fraction` is low when per-layer ms onsets do not merge within τ.

---

## 8. Onset density versus active density

**Module:** `temporal_density.TemporalDensityAnalyzer`.

| | Onset density | Active density |
|---|---------------|----------------|
| **Increments when** | Note **starts** in bin | Note **sounds** during bin (overlap) |
| **Typical use** | Attack rate, rhythmic “entry” profile | Polyphonic thickness, sustain |
| **Rests** | Zero in rest bins | Zero unless overlap from prior sustain |

A passage can show **high initial onset density** (many entries in a short bin) followed by **high active density** (few new attacks but many overlapping durations). The two curves can describe **different textural regimes**; comparing them is often more informative than either scalar alone.

---

## 9. Metric interpretation table

| Metric | Measures | Does not measure | Main interpretive risk |
|--------|----------|------------------|------------------------|
| **EPS global** (`events_per_second`) | Fused unique onsets / fused onset span | Full score duration; Mustextu window rate; raw attack rate | Treating as canonical VD4\_s instead of `rate_eps`; ignoring `events_per_second_raw` |
| **Onset count per bin** | Raw attacks entering each bin | Fused horizontal pulse; notes already sounding | Equating bin peaks with fused IOI regularity |
| **Active count per bin** | Concurrent sounding events per bin | New attacks only; timbre | Treating overlap count as attack rate |
| **IOI CV** | Variability of **fused** IOIs | Raw stream zeros from chords; Mustextu IEIs | Using `ioi_cv_raw` as the thesis VD4 scalar |
| **granularity_index** | \(1/(1+\mathrm{ioi\_cv})\) on fused IOIs | Direct note count or vertical density | Low index on homorhythm when reading raw IOIs only |
| **burstiness** | Unevenness of **fused** counts in 0.5 s windows | Raw bin density from `TemporalDensityAnalyzer` | Confusing with EPS or active density |
| **sync_fraction** (VD4) | Share of note-matrix onsets merged within 2 ms | Mustextu layer pool; exact chord pitch count | Equating with `synchrony_fraction` |
| **synchrony_fraction** (Mustextu) | Share of **layer** onsets merged within τ | Note-matrix `sync_fraction`; pairwise part correlation | Equating with vertical density |
| **max_multiplicity** (Mustextu) | Largest τ-merge group size | Inter-part phase over long spans | Substituting for sync metrics |
| **Mustextu `rate_eps`** | Unique merged layer onsets / Mustextu window | Global EPS span; raw rate | Comparing `rate_eps` to EPS global without aligning definitions |

---

## 10. Recommended use in analysis

Robust interpretation should normally **combine**:

- onset-density curve (`activity_granularity.by_interval[*].onset_density`);
- active-density curve (`active_density`);
- activity-rate window curve (`activity_rate.events_per_sec`);
- raw IOI list for plots (`ioi_sec` from `run_activity_granularity`);
- EPS global and **`events_per_second_raw`** (with §3 in mind);
- **fused** IOI CV, granularity index, burstiness;
- **`ioi_cv_raw` / `granularity_index_raw`** when vertical simultaneity matters;
- **`sync_fraction`** and Mustextu `synchrony_fraction`, `max_multiplicity`, `rate_eps` / `rate_eps_raw`;
- structural counts (`num_events`, `num_events_raw`, unique onsets).

**Avoid** basing a musicological conclusion on **one scalar alone**.

---

## 11. Relation to musicological regression fixtures

Phase-1 fixtures and inspection: [MUSICOLOGICAL_REGRESSION_FIXTURES.md](MUSICOLOGICAL_REGRESSION_FIXTURES.md), `corpus/reports/musicological_regression_inspection.md`.

Phase-2 promotion rules: [MUSICOLOGICAL_GOLDEN_VALUES_DECISION.md](MUSICOLOGICAL_GOLDEN_VALUES_DECISION.md).

After v1.0.7 (VD4 fix), inspection values for **`ioi_cv`**, **`granularity_index`**, and **`burstiness`** on chordal/homorhythmic fixtures reflect **fused-onset** semantics. **`regular_homorhythm`** now shows `ioi_cv = 0`, `granularity_index = 1.0` (fused grid) with elevated `ioi_cv_raw`.

Values marked **EXPLORE** for EPS global or Mustextu synchrony on specific fixtures should still be reviewed before strict golden lock.

---

## VD10 — Registral trajectory

**Module:** `granular_v2/trajectory.py` → `compute_vd10`  
**GUI:** tab *Registral trajectory* — picks on `plot_heatmap_advanced` axes (seconds × MIDI semitones). Tab *Registral trajectory (image)* — calibrated PNG/JPG excerpt (linear pixel↔pitch/time); shared pick/edit logic in `gui_trajectory_common.py`. See [LIMITATIONS.md](LIMITATIONS.md) for image calibration scope.

### What VD10 measures

Displacement of a **user-enclosed registral band** (lower/upper boundary per sample time). Units: **semitones** (integer MIDI); speeds in **semitones per second**. Time on the heatmap tab comes from the same seconds axis as the note matrix (`loader` + `timebase`); on the image tab, time and pitch come from user calibration (`make_axis_calibration`).

### What VD10 does **not** measure

- **Not granularity / event rate (VD4):** many attacks per second does not imply registral motion; sparse textures can move quickly in register.
- **Not automatic voice or layer detection by default:** the analyst defines blocks manually; optional **Auto-pick from score** proposes one block per XML `part`; optional **Group selected parts** merges several parts into one envelope block (same VD10 computation after confirmation).
- **Not total-path speed as headline metric:** a block that ascends then returns yields **net_speed ≈ 0**; `total_path` and `inflections` describe oscillation, not directional displacement.

### Canonical speed

**net_speed** = \((\mathrm{centre}_{\mathrm{last}} - \mathrm{centre}_{\mathrm{first}}) / (t_{\mathrm{last}} - t_{\mathrm{first}})\).

Per-segment **speed_centre** = \(\Delta\mathrm{centre}/\Delta t\). When two picks are very close in time, \(\Delta t \to 0\) and segment speed can reach thousands of st/s **without any musically plausible gesture** — an **sampling artefact**, not a bug.

### Robust vs sampling-dependent descriptors

| Role | Keys | Thesis use |
|------|------|------------|
| **Robust** | `net_speed`, `net_displacement`, `straightness`, `total_path`, `inflections` | Primary interpretation |
| **Sampling-dependent** | `mean_speed`, `median_speed`, `max_speed`, `segments[].speed_centre` | Secondary; always inspect `segments[].dt_s` before citing max |

**median_speed** is less sensitive to a single tiny \(\Delta t\) than **max_speed**, but still depends on pick spacing. Never cite **max_speed** without checking the segment that produced it.

Export includes `sampling_warnings` when any segment has `dt_s` < 0.1 s (recommended minimum spacing).

### Labels (heuristic)

| Label | Rule (default ε = 0.01 st) |
|-------|----------------------------|
| `direction` | ascending / descending / static from `net_displacement` |
| `band_behaviour` | diverging / converging / stable width from Δwidth end−start |
| `shape_hint` | \|straightness\| > 0.8 → unidirectional; \|straightness\| < 0.4 → undulating; else mixed (export `straightness` is **signed**) |

Internal coherence / orientation of the block (e.g. anisotropy / VD8) is **out of scope** for VD10.

### Export

Separate JSON via `export_vd10_json` (single block) or `export_vd10_session_json` (multi-block). Keys: `metric` = `"VD10"` / `"VD10_session"`, `samples`, `segments`, `aggregates`, `labels`, `summary`; session adds `blocks[]` and `relations`. Image sessions may add `source: "image"` and `image_calibration`.

---

## VD10 block relations (multi-block)

**Function:** `compute_block_relations` · **Module:** `granular_v2/trajectory.py`

### What it measures

Whether the **centre trajectories** of two user-defined blocks **converge, diverge, or stay parallel** in register separation over their shared time span, and whether their **net registral directions** align or oppose.

### What it does **not** measure

- **Not VD10 net speed** per block (use each block's `vd10.aggregates.net_speed`).
- **Not VD8 / anisotropy:** internal coherence or orientation within a block is out of scope.
- **Not voice detection:** blocks are analyst-defined regions.

### Implementation summary

Centres are linearly interpolated between picks; inter-centre distance \(d(t)\) is sampled on the overlap grid. **mean_inter_distance_rate_st_per_s** = \((d_{\mathrm{end}} - d_{\mathrm{start}}) / T_{\mathrm{overlap}}\). Labels use the same ε tolerance as VD10 (default 0.01 st).

---

## 12. Documentation map

| Document | Role |
|----------|------|
| [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) (this file) | Interpretive limits and implementation-aligned definitions |
| [FORMULAS.md](FORMULAS.md) | Compact formula sheet |
| [MANUAL_METRICAS.md](MANUAL_METRICAS.md) | One-page metric table |
| [MANUAL_TECNICO.md](MANUAL_TECNICO.md) | Algorithms and tutorials |
| [LIMITATIONS.md](LIMITATIONS.md) | Symbolic-only scope, tempo stepwise model |
| [MUSICOLOGICAL_GOLDEN_VALUES_DECISION.md](MUSICOLOGICAL_GOLDEN_VALUES_DECISION.md) | PROMOTE / EXPLORE / CLARIFY gate |

---

## 13. Code references (implementation source)

| Metric | Primary module / function |
|--------|---------------------------|
| Fused IOI CV, granularity index, burstiness, VD4 sync_fraction | `granular_v2/activity_granularity.py` → `granularity_metrics`, `merge_coincident_onsets` |
| Raw IOI list (plots) | `granular_v2/activity_granularity.py` → `inter_onset_intervals` |
| Onset / active density | `granular_v2/temporal_density.py` → `TemporalDensityAnalyzer.run` |
| Global export wrapper | `granular_v2/event_rates.py` → `global_event_rates` |
| Mustextu synchrony, `rate_eps` | `granular_v2/mustextu/horizontal_density.py` → `compute_horizontal_density_from_onsets` |
| Mustextu summary export | `granular_v2/granularity_mustextu.py` |
| VD10 registral trajectory | `granular_v2/trajectory.py` → `compute_vd10`, `export_vd10_json` |
| VD10 multi-block session | `granular_v2/trajectory.py` → `compute_vd10_session`, `export_vd10_session_json` |
| VD10 block relations | `granular_v2/trajectory.py` → `compute_block_relations`, `interpolate_centre_at_times` |
| VD10 auto-pick (proposal) | `granular_v2/trajectory.py` → `auto_pick_blocks_from_note_matrix`, `auto_pick_samples_for_part` |
| VD10 image calibration | `granular_v2/trajectory.py` → `make_axis_calibration`, `describe_axis_calibration` |

No formula in this document should be read as overriding the code; if they diverge, **the code wins** and this file should be updated.
