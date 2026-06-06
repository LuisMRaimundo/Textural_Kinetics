# Metric semantics and interpretive limits

**Audience:** Analysts, thesis readers, and maintainers promoting values to golden regression.  
**Status:** Describes the **implemented model** in `granular_v2/` as of the current export schema.  
**Companion docs:** [FORMULAS.md](FORMULAS.md), [MANUAL_METRICAS.md](MANUAL_METRICAS.md), [MANUAL_TECNICO.md](MANUAL_TECNICO.md) §5–8.

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
| **Unique onset** | A distinct onset time after collapsing exact or tolerance-based equality. *Not* the basis for core IOI/EPS unless explicitly stated (see §4). |
| **Coincident onset** | Two or more events whose onset times fall within Mustextu `coincidence_ms` (anchor-based merge; see §7). |
| **Active event** | An event whose sounding interval `[onset, onset + duration)` overlaps a time bin. |
| **Onset count per bin** | Number of events whose onset falls in bin \([t, t+\Delta)\). Stored as `onset_density[j]` (float count). |
| **Active count per bin** | Number of events sounding during bin \(j\) (overlap with \([b_j, b_{j+1})\)). Stored as `active_density[j]`. |
| **Bin-based density** | Per-bin counts or rates derived from `TemporalDensityAnalyzer` (`onset_density`, `active_density`, `events_per_sec_per_bin = onset_count / Δ`). |
| **Window-based activity rate** | Onsets counted in a sliding window \([t_c - W/2, t_c + W/2)\), divided by \(W\) → `activity_rate.events_per_sec`. |

**Default “event” sense:** symbolic pitch-event (or layer onset in Mustextu), not one fused sonority. A four-note chord yields **four** events and **four** onsets at the same time unless tie/merge policy removes attacks earlier in the pipeline.

---

## 3. EPS global / `events_per_second`

**Module:** `activity_granularity.granularity_metrics` → `event_rates.global_event_rates`.

**Implementation:**

```text
onsets = sorted onset_sec per note-matrix row (not deduplicated)
N      = len(onsets)  (= len(note_matrix))
span   = max(onsets) - min(onsets)   # numpy.ptp; if N < 2 or span ≤ 0 → span := 1.0
events_per_second = N / span
events_per_millisecond = events_per_second / 1000
```

Equivalent export definition string: `N / (t_last_onset - t_first_onset)` in seconds.

**Interpretive limits:**

- This is **not** necessarily the event rate over the full notated duration (last note-off, score length, or Mustextu window). The denominator is **onset span only**.
- EPS global can be **high** when many events are packed between the first and last attack, even if the score is mostly rest or sustain outside that span.
- Read it as **attack-event concentration over the onset span**, not as sustained temporal density for the whole piece.
- If notes **continue sounding** after the last onset, EPS global does **not** describe that later sustained period (use **active density** or duration-aware views).

---

## 4. IOI and IOI CV

**Module:** `activity_granularity.inter_onset_intervals`, `granularity_metrics`.

**Implementation:**

```text
onsets = get_onsets_sorted(note_matrix)   # one value per row, sorted, NOT deduplicated
IOI_k  = onsets[k+1] - onsets[k]          # numpy.diff
ioi_mean = mean(IOI)
ioi_std  = std(IOI)
ioi_cv   = ioi_std / ioi_mean             # NaN if mean ≤ 0
```

**Explicit basis:** IOIs are taken from the **raw event onset sequence**, including **zero IOIs** when consecutive sorted onsets are equal (simultaneous attacks in the same stream).

The implementation does **not** collapse to unique onsets before IOI computation.

**Interpretive warning:**

- Simultaneous events insert **zero** inter-onset intervals.
- A homorhythmic or chordal texture can show a **high IOI CV** even when the **unique-onset** grid is perfectly regular (`regular_homorhythm` is a documented example in [MUSICOLOGICAL_GOLDEN_VALUES_DECISION.md](MUSICOLOGICAL_GOLDEN_VALUES_DECISION.md)).
- **IOI CV measures irregularity of the extracted event stream**, not automatically irregularity of the unique-onset pulse. For pulse regularity, derive IOIs from **deduplicated** onset times (or inspect Mustextu merged IEIs) separately.

---

## 5. `granularity_index`

**Implementation** (`granularity_metrics`):

```text
granularity_index = 1 / (1 + ioi_cv)     # 0.5 if ioi_cv is non-finite
```

**Interpretation:**

- Inversely related to **IOI CV on raw event onsets** (§4).
- **Not** a direct count-density measure; high event count does not by itself raise the index.
- High density with many simultaneous zero-IOI events can **lower** the index (higher IOI CV).
- Best read **together with** EPS global, onset/active density curves, activity-rate windows, IOI histograms, and structural onset counts.

---

## 6. `burstiness`

**Implementation** (`granularity_metrics`):

1. Build onset counts per **0.5 s** bin via `density_by_bins` → `onset_density` (attacks per bin only).
2. Let \(\mu = \mathrm{mean}(c_k)\), \(\sigma = \mathrm{std}(c_k)\) over bins.
3. `burstiness = (σ - μ) / (σ + μ)` if \((\sigma + \mu) > 0\), else `0.0` (requires ≥ 2 bins).

**Interpretation:**

- Describes **temporal clustering / concentration** of attacks across fixed bins.
- **Positive** values → more uneven bin counts (burst-like attack distribution).
- **Not** the same as event density or EPS global (a steady high rate with flat bins can yield low burstiness).
- Use with the **activity-rate curve** and IOI distribution; sustained overlap does not enter burstiness (onset bins only).

---

## 7. `sync_fraction` / `synchrony_fraction`

**Export name:** `synchrony_fraction` in `mustextu_summary` / composite JSON. **`sync_fraction`** is an informal alias for the same quantity.

**Module:** `mustextu/horizontal_density.py` (`compute_horizontal_density_from_onsets`).

**Procedure:**

1. For each part/layer, collect onset times in ms (optionally skip grace notes).
2. Concatenate all layer lists → `all_onsets`; `total_raw = len(all_onsets)`.
3. Sort and **merge** onsets within effective tolerance `coincidence_ms_effective` (default base **2.0 ms**; optionally `min(coincidence_ms, 0.05 × median IEI per layer)` when `adaptive_tolerance` is true). Merge is **anchor-based** (no transitive chaining across distant onsets).
4. `total_unique = len(merged_times)`.
5. **`synchrony_fraction = 1 - total_unique / total_raw`** (0 if `total_raw == 0`).

**What it measures:**

- The fraction of **raw layer onset entries** that are “redundant” after tolerance merge **across the full multi-layer pool** (intra-layer and inter-layer).
- Unit counted: **one per layer onset entry**, not pairs or arbitrary groups.
- **Intra-chord simultaneity in a single part** contributes only if multiple onset entries fall within **τ** of the same anchor. Micro-separation in ms (or separate layer lists) can yield **low** synchrony despite high vertical pitch count in the note matrix.

**Related Mustextu fields (not interchangeable):**

| Field | Meaning |
|-------|---------|
| `max_multiplicity` | Largest merge-group size after coincidence merge |
| `coincident_groups` | Count of merge groups with multiplicity ≥ 2 |
| `avg_multiplicity` | `total_raw / total_unique` |
| `rate_eps` | `total_unique / (window_ms/1000)` — unique merged onsets per second |
| `rate_eps_raw` | `total_raw / (window_ms/1000)` |

**`max_simultaneous_pitches`** (inspection/regression helper, not core export): maximum number of note-matrix rows sharing the **same** `onset_sec` (exact equality after loader). This can be **high** while `synchrony_fraction` is **low** (e.g. `dense_chordal_blocks`: four pitches per attack, synchrony 0.0 when per-layer ms onsets do not merge within τ).

**Explicit warning:**

- **`max_multiplicity` / `max_simultaneous_pitches` and `synchrony_fraction` are not equivalent.**
- A chordal block can show strong vertical pitch coincidence in the note matrix but **low** synchrony if merge tolerance or per-layer onset lists do not collapse those entries.
- Do **not** treat `synchrony_fraction` as generic vertical density unless you have verified merge behaviour for that score and τ.

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
| **EPS global** (`events_per_second`) | Attack-event count / first-to-last onset span | Full score duration, sustained overlap rate, audio tempo | Confusing onset span with piece length; ignoring post-last-onset sustain |
| **Onset count per bin** | Attacks entering each bin | Notes already sounding without new attack | Equating bin peaks with “loudness” or spectral density |
| **Active count per bin** | Concurrent sounding events per bin | New attacks only; timbre | Treating overlap count as attack rate |
| **IOI CV** | Variability of **raw** event IOIs (incl. zeros) | Unique-onset pulse regularity alone | Calling homorhythmic scores “irregular” because of chordal zeros |
| **granularity_index** | \(1/(1+\mathrm{ioi\_cv})\) on same IOIs | Direct fineness of subdivision or note count | Assuming high density ⇒ high index |
| **burstiness** | Unevenness of 0.5 s **onset** bin counts | Sustained texture; spectral flux | Confusing with EPS or active density |
| **sync_fraction** (`synchrony_fraction`) | Share of layer onsets merged within τ (all layers) | Pairwise part correlation; exact chord pitch count | Equating with vertical density or `max_simultaneous_pitches` |
| **max_multiplicity** (Mustextu) | Largest τ-merge group size | Inter-part phase alignment over long spans | Substituting for sync_fraction or pitch simultaneity |
| **max_simultaneous_pitches** (helper) | Max note-matrix rows per identical `onset_sec` | Mustextu merge groups; audio polyphony | Using in place of synchrony_fraction |
| **Mustextu `rate_eps`** | Unique merged onsets per second over Mustextu window | Raw attack rate (`rate_eps_raw` differs); global EPS span | Comparing `rate_eps` to EPS global without aligning window definitions |

---

## 10. Recommended use in analysis

Robust interpretation should normally **combine**:

- onset-density curve (`activity_granularity.by_interval[*].onset_density`);
- active-density curve (`active_density`);
- activity-rate window curve (`activity_rate.events_per_sec`);
- IOI histogram or list (`ioi_sec`);
- EPS global (`event_rates.global.events_per_second`);
- IOI CV and granularity index (with §4 in mind);
- burstiness;
- Mustextu `synchrony_fraction`, `max_multiplicity`, `rate_eps` / `rate_eps_raw`;
- layer or part distribution and structural counts (`num_events`, unique onsets).

**Avoid** basing a musicological conclusion on **one scalar alone** (especially EPS global, IOI CV, or synchrony fraction).

---

## 11. Relation to musicological regression fixtures

Phase-1 fixtures and inspection: [MUSICOLOGICAL_REGRESSION_FIXTURES.md](MUSICOLOGICAL_REGRESSION_FIXTURES.md), `corpus/reports/musicological_regression_inspection.md`.

Phase-2 promotion rules: [MUSICOLOGICAL_GOLDEN_VALUES_DECISION.md](MUSICOLOGICAL_GOLDEN_VALUES_DECISION.md).

Values marked **EXPLORE** or **CLARIFY** in the golden-values decision (e.g. EPS global, IOI CV on `regular_homorhythm`, Mustextu synchrony fraction on `dense_chordal_blocks`) should **not** be promoted to strict regression until:

1. This semantics document is accepted for the thesis/reporting context, and  
2. The analyst confirms the implemented behaviour matches the intended claim.

Structural counts (event totals, unique onsets, pitch lists, IOI bands tied to tempo) are safer first golden targets than interpretive composites.

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
| EPS, IOI CV, granularity index, burstiness | `granular_v2/activity_granularity.py` → `granularity_metrics` |
| Onset / active density | `granular_v2/temporal_density.py` → `TemporalDensityAnalyzer.run` |
| Global export wrapper | `granular_v2/event_rates.py` → `global_event_rates` |
| Mustextu synchrony, `rate_eps` | `granular_v2/mustextu/horizontal_density.py` → `compute_horizontal_density_from_onsets` |
| Mustextu summary export | `granular_v2/granularity_mustextu.py` |

No formula in this document should be read as overriding the code; if they diverge, **the code wins** and this file should be updated.
