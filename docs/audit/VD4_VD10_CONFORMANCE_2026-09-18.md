# VD4 / VD10 conformance — 2026-09-18

Package **1.0.17**. Landed on `main` as `1f0d9fb` (`Merge branch 'fix/vd4-vd10-conformance'`). No tag.

Executed snapshots: `docs/audit/_before_vd4_vd10.json` (commit `76eeef9`, pre-change) and `docs/audit/_after_vd4_vd10.json` (`run_analysis` + `auto_pick_blocks_from_note_matrix` on this branch).

VD4 rate (`mustextu_summary.rate_events_per_second`), `ioi_cv`, burstiness, and VD10 auto-picked aggregates from this version are **not comparable** with ≤ 1.0.16.

---

## What changed (file:line)

### 1. VD4 burst — Fano factor

- `granular_v2/activity_granularity.py:62-96` `burstiness_fano`: \(F=\mathrm{var}(c)/\mathrm{mean}(c)\), \(B=(F-1)/(F+1)\). Full 0.5 s windows tile `[t_start, t_end)`; trailing partial window dropped; `< 2` full windows or `mean(c)≤0` → NaN. Last-bin-closed `np.histogram` is not used (all bins half-open).
- Optional `support` on `granularity_metrics` (`activity_granularity.py:191-246`) and `run_activity_granularity` (`:249`).
- Pipeline supplies score support `[0, highestTime)` via `onset_extraction.score_support_sec` (`onset_extraction.py:223-233`) from `fusion.py:28-41`.
- Special-case `B=0` removed.
- Export string: `event_rates.py:73-77`.

### 2. One onset source (ties)

- Rate and regularity both start from the tie-merged note matrix.
- `onset_extraction.onsets_per_layer_from_note_matrix` (`:127-144`) takes unique attack times per layer.
- `extract_onsets_per_layer_ms_from_score` (`:164-198`) now: `extract_notes_with_ties` → seconds → grace placement → per-layer unique times. The old `notesAndRests` walk (no tie check) is deleted.
- Mustextu `extract_onsets_per_layer_from_musicxml` (`mustextu/horizontal_density.py:442-456`) delegates to that path.
- `analyze_mustextu_from_score` (`granularity_mustextu.py:17-48`) accepts the loaded `note_matrix`; `fusion.py:48-51` passes it.
- Chord ties are per pitch (`note_extraction.py:46-57`, `:139-158`). A continuation is only a non-attack when every pitch is tied; a new pitch starts a new row / onset (`T2`).

Duplicate extraction was deleted rather than patched in place. The flatten-fallback unit test of the old walk was removed with it.

Unnamed parts get a stable `Part-{index}` label (`note_extraction.py:87-90`) so layers do not collapse to one `"Unknown"` pool. That is required for a shared per-layer onset source.

### 3. Grace notes are attacks (VD4)

- Default `ignore_grace=False` (`config.py:18`, `onset_extraction.py:169`).
- `GRACE_NOMINAL_SPACING_SEC = 0.05` (`onset_extraction.py:12`).
- `assign_grace_nominal_onsets` (`:46-124`): \(k\) graces before principal \(t\) at \(t-ks,\ldots,t-s\); if gap \(g<(k+1)s\) then \(s=g/(k+1)\); if \(s\le\tau\) events are kept and `grace_compressed=true`.
- Applied in the loader (`loader.py:123-127`) and in the standalone onset path.
- Export: `grace_onsets_included`, `grace_compressed` (`event_rates.py:59-60`, `activity_granularity.py:177-188`).

### 4. One fusion rule

- `effective_coincidence_tol_sec` (`activity_granularity.py:16-40`): \(\min(0.002, 0.05\times\min_{\mathrm{layer}}\mathrm{median\ IOI})\). Adaptive when that median is `< 40\,\mathrm{ms}\). IOIs \(\le\) base \(\tau\) are excluded from the median so coincidence-scale doubles do not shrink \(\tau\) (see doubled-grid axiom).
- `merge_coincident_onsets` (`:43-59`) is the only merge. Mustextu `_merge_coincident_onsets` (`horizontal_density.py:57-68`) converts ms→s, calls it, converts back. **Algorithm is identical** (anchor, no transitive chaining). `test_coincidence_merge.py` still passes; no fixture in this corpus has a merge-algorithm delta. Rate/CV changes below come from the onset source and the Fano burst, not from a different merge.
- Effective \(\tau\) is exported (`event_rates.py:58`, `granularity_mustextu.py:71-76`).

### 5. VD4_GI removed

Deleted from `granularity_metrics`, `global_event_rates`, `plots.py:76` (summary panel), and live docs. `ioi_cv` / `ioi_cv_raw` kept. Mustextu `granularity_score` / `granularity_label` untouched (`horizontal_density.py` composite block).

### 6. VD10 sounding band / zero width

- `band_from_pitches` (`trajectory.py:670-677`): single pitch returns `(p, p)`; forced `hi = lo + 1` removed.
- `auto_pick_samples_for_part` / `_for_group` (`:696-727`, `:760-799`): at each distinct **non-grace** onset, band from all pitches with `onset ≤ t < offset`.
- GUI display-only minimum thickness: `gui_trajectory_common.py:391` and `:456` `max(hi-lo, 0.5)`. Data width stays 0.
- **Grace notes are not VD10 sample times** (`trajectory.py:692-694`, `:718-721`). This was already implicit when grace and principal shared a notated time; it is now explicit after nominal grace placement. Not changed silently.

### 7. Housekeeping

Version **1.0.17** (`metadata.py`, `pyproject.toml`, `CITATION.cff`). CHANGELOG, README, manuals, FORMULAS, METRIC_SEMANTICS, LIMITATIONS.

---

## B4 value (window aliasing)

Regular onsets, period \(0.30\,\mathrm{s}\), 80 events, default support = first-to-last unique onset.

**Executed:** `B = -0.7710469830670165` (`burstiness_fano`; `test_vd4_vd10_conformance.py::test_b4_regular_period_not_dividing_window`).

\(0.30\) does not divide the \(0.5\,\mathrm{s}\) window. Count series aliases (pattern \(2,2,1,\ldots\)). Declare this in the thesis: \(B=-1\) only when the period divides the window (or all full-window counts are equal).

---

## BEFORE / AFTER — corpus fixtures used by regression tests

Sources: `_before_vd4_vd10.json` (executed on `76eeef9`), `_after_vd4_vd10.json` (this branch). Rate = Mustextu `rate_eps`. Burst AFTER uses score support when the pipeline supplies it.

| Fixture | rate BEFORE → AFTER | ioi_cv BEFORE → AFTER | burst BEFORE → AFTER | VD10 aggregates |
|---------|---------------------|----------------------|----------------------|-----------------|
| `dense_onset_burst.musicxml` | 20.0 → 20.0 | ~0 → ~0 | −1.0 → **None** (`<2` full 0.5 s windows on score support) | width 1→**0**, centre 72.5→**72** (6a). net 0 unchanged |
| `layered_async.musicxml` | 8.0 → 8.0 | 0.4100 → 0.4100 | −1.0 → −1.0 | **Was** one `Unknown` block, net +7, path 105, width 1. **Now** `Part-1`/`Part-2` (8 samples each), net 0, width 0. Reason: stable per-part labels + 6a. Old +7 was the collapsed-Unknown envelope, not a 6b pedal |
| `sparse_homophony.musicxml` | 0.6 → 0.6 | 0 → 0 | 0.1270 → **−0.1765** (Fano) | chord width 7 unchanged; `num_events_raw` 9→3 (unique-per-layer) |
| `musicological_regression/dense_chordal_blocks.musicxml` | 1.0 → 1.0 | 0 → 0 | −0.2679 → **−0.3333** (Fano) | net +3.5, width 11/10 unchanged (multi-pitch) |
| `musicological_regression/empty_or_degenerate_score.musicxml` | error both sides: `onsets_per_layer_ms cannot be empty` | — | — | — |
| `musicological_regression/grace_note_passage.musicxml` | **2.0 → 3.5** (grace attacks) | **0 → 0.8940** | −0.4776 → **−0.8065** | `grace_onsets_included=4`. VD10 samples still 4 (graces not sample times). width 14→**0**, centre 67→**60**: graces no longer share the principal onset, so they drop out of the band (6a + §6c) |
| `musicological_regression/layered_async.musicxml` | 3.0 → 3.0 | 0.3499 → 0.3499 | −0.4202 → **−0.7143** (Fano) | one Unknown → three `Part-N` monodies, width 1→0, centres 60.5→60 (6a + labels) |
| `musicological_regression/multi_voice_polyphony.musicxml` | 1.6667 → 1.6667 | 0.3464 → 0.3464 | −0.5590 → **−0.0169** (Fano) | width 1→0, centre 60.5→60; path 28→**15** (6a halves each ±1 st monodic step) |
| `musicological_regression/regular_homorhythm.musicxml` | 2.0 → 2.0 | 0 → 0 | −0.6209 → **−1.0** (Fano, regular counts) | one Unknown envelope width 7 → three `Part-N` monodies width 0 (labels + 6a). `num_events_raw` stays 48 (three layers) |
| `musicological_regression/repeated_section.musicxml` | 0.5 → 0.5 | 0 → 0 | 0.0 → **−0.1429** (Fano; old 0.0 was the removed special case) | width 1→0, centres 60.5/62.5→60/62; **net still +2** (6a) |
| `musicological_regression/tempo_change_mid_score.musicxml` | 1.3333 → 1.3333 | 0.3254 → 0.3254 | −0.1201 → **−0.5000** (Fano) | width 1→0, centre 67.5→67 (6a) |
| `musicological_regression/tied_sustained_texture.musicxml` | **0.75 → 0.5** (tie continuations no longer count as attacks on the rate path) | 0 → 0 | 0.0 → **−0.1429** | one Unknown width 19 → two parts width 0 (labels + 6a). `num_events` still 2 |
| `musicological_regression/transposing_instrument_score.musicxml` | 2.0 → 2.0 | 0 → 0 | −0.5 → **−1.0** (Fano) | width 1→0, centres 60.5/67.5→60/67; **net still +7** (6a) |

`events_per_second` (span diagnostic) moved only where the onset set moved: `grace_note_passage` 2.667→5.161.

---

## Updated goldens (old, new, reason)

| Test | Old | New | Reason |
|------|-----|-----|--------|
| `test_band_from_pitches_single_note_gets_unit_width` | `(60, 61)` | `(60, 60)` | 6a |
| `test_auto_pick_samples_merges_chord` second sample | high 68 | high 67 | 6a, monody after the chord |
| `test_group_pick_convergent_lines` end width | 1.0 | 0.0 | 6a, both parts on the same pitch |
| `test_regular_train_maximally_regular` burst | `< 0` (old Gini-style) | `−1` | Fano, equal counts |
| `test_vd4_fused_onsets_doubled_grid` | GI == 1 | GI absent | GI removed |
| `test_grace_note_included_when_ignore_grace_false` | both at 0 ms | −50 ms, 0 ms | nominal grace spacing |
| `test_layered_async_distinguishable_from_sparse_homophony` | `num_events < num_events_raw` on sparse | `len(note_matrix) > num_events` | unique-per-layer: a 3-pitch chord is one attack |
| Flatten-fallback onset test | present | **deleted** | duplicate score walk removed |

`test_auto_pick_blocks_compatible_with_compute_vd10` net +7 **unchanged** (both endpoints shift by −0.5 st under 6a).

---

## Mustextu merge vs `activity_granularity`

Wrapper only (`horizontal_density.py:57-68`). Same anchor rule. No corpus case showed a merge-algorithm difference. Changes in the table are from the shared onset source, Fano burst, grace policy, or Part-N labels.

---

## Tests added

`tests/test_vd4_vd10_conformance.py`: B1 (seeded Poisson 0.5/2/8/20), B2, B3, B4, B5, T1, T2, T3, G1, G2, F1, R1, V1, V2, V3, plus grace-not-a-VD10-sample-time.

---

## NOT VERIFIED

- Interactive GUI picking / drag of a zero-width band (display thickness is coded; not exercised in a browser).
- Image-tab VD10 calibration path (unchanged; not re-proven here).
- Whether every MusicXML exporter writes per-note chord ties that music21 exposes on `Chord.notes[i].tie`. T2 constructs them in memory.
- Empty-score Mustextu still raises `onsets_per_layer_ms cannot be empty` (pre-existing; not in scope).
- Thesis prose beyond the code and the B4 aliasing value.
- Perceptual validity of the 50 ms nominal grace spacing.

---

## Unchanged (as required)

Half-open sounding interval; support-referenced Mustextu rate; IOI CV definition (std/mean on fused unique IOIs); VD10 net-speed, straightness, inflection counting; label thresholds 0.8 / 0.4; `DEFAULT_EPS`. No compatibility aliases.
