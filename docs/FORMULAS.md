# Formula sheet (compact)

Full derivations, algorithms, and tutorials: **[MANUAL_TECNICO.md](MANUAL_TECNICO.md)**.  
One-page metric table: **[MANUAL_METRICAS.md](MANUAL_METRICAS.md)**.  
Interpretive limits: **[METRIC_SEMANTICS.md](METRIC_SEMANTICS.md)**.

## Global event rates (VD4 span diagnostic)

- \(N_{\mathrm{raw}}\) = note-matrix rows (one onset per event)
- \(N_{\mathrm{unique}}\) = fused onset count after anchor merge within **τ = 2 ms**
- \(T_{\mathrm{span}} = t_{\mathrm{last}} - t_{\mathrm{first}}\) on **fused** onsets (seconds; support = 1 s if degenerate) — **not** full notated duration
- **events_per_second** = \(N_{\mathrm{unique}} / T_{\mathrm{span}}\) (span-referenced diagnostic)
- **events_per_second_raw** = \(N_{\mathrm{raw}} / T_{\mathrm{span}}\)
- **events_per_millisecond** = events_per_second / 1000
- **sync_fraction** = \(1 - N_{\mathrm{unique}}/N_{\mathrm{raw}}\)
- **Canonical VD4\_s rate:** Mustextu **rate_eps** (see Mustextu section)

## Per time bin (width \(\Delta\) seconds)

- **onset_count_per_bin** = attacks in \([t, t+\Delta)\)
- **events_per_second_per_bin** = onset_count / \(\Delta\)

## Per millisecond window (width \(W\) ms)

- **events_per_millisecond_in_window** = count in window / \(W\)

## Per bar (measure \(m\))

- **onset_count** = attacks with onset in measure \(m\)
- **events_per_second_in_bar** = onset_count / measure_duration_sec
- **events_per_beat_in_bar** = onset_count / notated_beats_in_bar

## IOI and granularity (VD4 — fused onsets)

- Fuse sorted raw onsets within **τ = 2 ms** (anchor-based; `merge_coincident_onsets`)
- \(\mathrm{IOI}_k = t^{\mathrm{fused}}_{k+1} - t^{\mathrm{fused}}_k\) — **no zero IOIs** from vertical simultaneity
- **ioi_cv** = \(\sigma / \mu\) on those fused IOIs
- **granularity_index** = \(1 / (1 + \mathrm{ioi\_cv})\)
- **burstiness** = \((\sigma_c - \mu_c) / (\sigma_c + \mu_c)\) on **fused-onset** counts in fixed **0.5 s** windows

**Raw diagnostics:** `ioi_cv_raw`, `granularity_index_raw` from `diff(raw sorted onsets)` (includes zero IOIs). Plot helper `inter_onset_intervals()` keeps raw semantics.

## Mustextu

- **rate_events_per_second** (composite key `rate_eps`) = unique merged layer onsets / (window_ms / 1000) — **canonical VD4\_s**
- **rate_eps_raw** = raw layer onsets / (window_ms / 1000)
- **synchrony_fraction** = \(1 - N_{\mathrm{unique}}/N_{\mathrm{raw}}\) after coincidence merge of **all layer** onsets (default τ = 2 ms, adaptive optional)
- **granularity_score** = clip(rate_eps / gran_max_eps, 0, 1)
- Regular layers: \(g^\* = \gcd(e_i)\), \(\mathrm{LCM}^\* = \mathrm{lcm}(e_i)\) — see manual §8.7

## Tempo (stepwise)

\[
t(q) = s_0^{(i)} + \frac{60}{b_i}(q - q_0^{(i)})\quad \text{for the first segment with } q \in [q_0^{(i)}, q_1^{(i)}]
\]

(Canonical `timebase.ql_to_seconds_fn` uses the closed test `q0 ≤ q ≤ q1` and returns the first matching segment; the `util_tempo` fallback uses the half-open `[q0, q1)`. Both agree at the shared, contiguous segment boundaries.)

## Heatmaps (symbolic)

- Occupancy: bin counts \(H_{p,t}\); display often \(\log(1+H)\)
- Spectral grid: velocity-weighted sum per cell (not audio FFT)

## Registral trajectory (VD10)

User picks ≥2 samples \((t, \mathrm{low}, \mathrm{high})\) in **integer semitones** on the pitch×time heatmap (time from `timebase` / `onset_sec` axis), or via **Auto-pick from score** (one block per XML part; one sample per onset; chord tones merged to min–max band).

Per sample: \(\mathrm{centre}=(\mathrm{low}+\mathrm{high})/2\), \(\mathrm{width}=\mathrm{high}-\mathrm{low}\).

Between consecutive samples (\(\Delta t>0\)):

- **speed_centre** = \((\mathrm{centre}_{i+1}-\mathrm{centre}_i)/\Delta t\) (signed: + up, − down)
- **speed_width** = \((\mathrm{width}_{i+1}-\mathrm{width}_i)/\Delta t\) (signed: + diverging, − converging)

Aggregates:

- **net_displacement** = \(\mathrm{centre}_{\mathrm{last}}-\mathrm{centre}_{\mathrm{first}}\)
- **net_speed** = net_displacement / \((t_{\mathrm{last}}-t_{\mathrm{first}})\) — **canonical headline speed** (not total_path / time)
- **total_path** = \(\sum_i \|\mathrm{centre}_{i+1}-\mathrm{centre}_i\|\)
- **straightness** = net_displacement / total_path (0 if total_path = 0)
- **inflections** = sign changes in centre deltas
- **mean_speed**, **median_speed**, **max_speed** = mean / median / max of \(\|\mathrm{speed\_centre}\|\) — **sampling-dependent** (tiny \(\Delta t\) inflates segment quotients)
- **min_segment_dt_s** = smallest segment duration
- Inspect **segments** (`dt_s`, `speed_centre`); export may include **sampling_warnings** when `dt_s` < 0.1 s

## Block relations (multi-block)

- Linear centre interpolation: `interpolate_centre_at_times`
- Overlap \([t_0, t_1]\) = intersection of block time spans
- \(d(t) = |\mathrm{centre}_B(t) - \mathrm{centre}_A(t)|\)
- **mean_inter_distance_rate_st_per_s** = \((d(t_1) - d(t_0)) / (t_1 - t_0)\)
- **relation:** converging / diverging / parallel from rate vs ε
- **direction:** pairwise net centre motion labels (not VD8)

**Not** event-rate granularity (VD4). Block detection is user-defined by default; **Auto-pick from score** proposes blocks from XML part labels (optional, editable).

## Auto-pick (optional GUI / API)

One block per note-matrix `part`; sample at each distinct onset; chord in same part → \(\mathrm{low}=\min\mathrm{pitch}\), \(\mathrm{high}=\max\mathrm{pitch}\); single pitch → band width 1 st. **Group parts:** several `part` labels → one block; at each onset \(\mathrm{low}=\min\) and \(\mathrm{high}=\max\) across **all** selected parts (envelope, not average). **API:** `auto_pick_blocks_from_note_matrix`, `auto_pick_samples_for_group` → feed to `compute_vd10_session`. Does not alter VD10 formulas.

## Image axis calibration (VD10 image tab)

Two reference points per axis define a **linear** pixel → value map:

\[
v(p) = v_0 + \frac{v_1 - v_0}{p_1 - p_0}(p - p_0)
\]

- **Pitch axis:** \(v\) in semitones (MIDI integer after pick snap)
- **Time axis:** \(v\) in seconds (excerpt duration set at calibration)

**API:** `make_axis_calibration`, `describe_axis_calibration` · **Error:** `TrajectoryCalibrationError` if reference pixels coincide.
