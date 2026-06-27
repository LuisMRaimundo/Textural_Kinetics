# Test Quality Audit — Granularity-Analyser

**Date:** 2026-06-10 (summary refreshed; module table below reflects 2026-06-06 audit unless noted)  
**Scope:** Current pytest suite (`tests/`), `test_inventory.txt`, corpus fixtures (`corpus/fixtures/`, `corpus/reference/`), and `granular_v2` coverage as reported by the project's pytest configuration.  
**Constraint:** Audit only — no production code, tests, or CI configuration were modified.  
**Metric semantics:** [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) — use when extending scalar regression (EPS, IOI CV, synchrony).

---

## 1. Overview of the current test suite

### Summary statistics

| Metric | Value |
|--------|------:|
| Collected tests | **174** |
| Test modules (excluding `conftest.py`) | **22** |
| Shared fixtures | `tests/conftest.py` → `sample_musicxml` |
| Corpus MusicXML fixtures | 3 (`dense_onset_burst`, `layered_async`, `sparse_homophony`) |
| Corpus reference JSON snapshots | 3 (matching fixture stems) |
| `granular_v2` line coverage (full suite) | **~87%** (threshold: 72%) |
| External regression script | `corpus/scripts/compare_all.py` (invoked by `tests/test_corpus.py`) |

Source of truth for individual test names: `test_inventory.txt` (may lag; prefer `pytest --collect-only` for current count).

### Test modules and analytical coverage

| Module | Tests | Primary analytical / software area |
|--------|------:|-----------------------------------|
| `test_coincidence_merge.py` | 3 | Mustextu coincidence merging (anchor-based onset grouping, no transitive chaining) |
| `test_config.py` | 2 | `AnalysisConfig` validation (`pitch_domain`, heatmap mode) |
| `test_corpus.py` | 1 | End-to-end corpus regression script (`compare_all.py` exit code) |
| `test_event_rates.py` | 4 | Global, windowed, per-bar, and binned event-rate computations |
| `test_fusion.py` | 2 | Partitional fusion layer and empty-matrix handling |
| `test_global_offsets_integration.py` | 3 | Global QL through tempo segments, loader onsets, sparse_homophony span/rate |
| `test_granularity_axioms.py` | 6 | VD4 fused IOI CV, burstiness, granularity index, raw/fused diagnostics, global rate |
| `test_heatmaps.py` | 8 | Pitch–time matrices, spectral energy, plot smoke tests, heatmap pipeline |
| `test_loader.py` | 5 | Single-parse loader, tempo fallback chain, MIDI branch, sounding pitch |
| `test_mustextu.py` | 1 | Mustextu wiring through loader (smoke) |
| `test_note_extraction.py` | 17 | Tie-aware note extraction: ties, chords, velocity, degenerate scores |
| `test_offset_audit.py` | 8 | Corpus timeline invariants, Mustextu/loader alignment, static offset guards, export audit keys |
| `test_offsets.py` | 12 | `global_offset` / `global_ql` / `boundary_ql` defensive fallbacks |
| `test_onset_extraction.py` | 16 | Per-layer onset extraction, grace/rest filtering, window resolution |
| `test_pipeline.py` | 2 | Full `run_analysis` with/without heatmaps and JSON export |
| `test_plots.py` | 1 | Activity plot smoke test (`granular_v2.plots`, omitted from coverage) |
| `test_timebase_axioms.py` | 13 | Tempo segments, QL→seconds, note time conversion in place |
| `test_trajectory.py` | 25 | VD10 core, relations, session, interpolation, export, calibration edge cases |
| `test_util_tempo_branches.py` | 11 | Repeat detection/expansion, `build_seconds_map` multi-segment behaviour |
| `test_util_tempo_fallbacks.py` | 8 | Repeat-expansion and metronome-boundary fallback paths (monkeypatch/fakes) |
| `test_util_tempo_parity.py` | 4 | Parity between `util_tempo` and `timebase` on synthetic + corpus scores |

### Coverage omissions (by design)

`pyproject.toml` excludes from coverage: `input_layer.py`, `gui.py`, `gui_trajectory.py`, `gui_trajectory_common.py`, `gui_trajectory_image.py`, `plots.py`, `run.py`, `__main__.py`, `logging_config.py`, `mustextu/horizontal_density.py`. Tests exist for some omitted modules indirectly (e.g. loader wraps input paths; coincidence tests hit `horizontal_density`; VD10 core in `test_trajectory.py`).

---

## 2. Classification by analytical area

| Area | Rating | Rationale |
|------|--------|-----------|
| **Loading and parsing** | **Strong** | `test_loader.py` covers MusicXML happy path, dual tempo fallback, MIDI, sounding pitch; pipeline tests exercise `run_analysis`. Core `loader.py` at 97% coverage. `input_layer.py` not directly covered (omitted). |
| **Offsets and temporal positioning** | **Strong** | `test_offsets.py` (100%), `test_offset_audit.py` static guards + corpus parametrized span checks, `test_global_offsets_integration.py` multi-measure QL regression. |
| **QuarterLength-to-seconds conversion** | **Strong** | `test_timebase_axioms.py` (98%), `test_util_tempo_branches.py` + `test_util_tempo_fallbacks.py` (100%), `test_util_tempo_parity.py` cross-checks util vs timebase on corpus. |
| **Note extraction** | **Strong** | `test_note_extraction.py` — 17 focused unit tests; `note_extraction.py` at 100% coverage. |
| **Onset extraction** | **Strong** | `test_onset_extraction.py` — 16 unit tests; `onset_extraction.py` at 100% coverage. |
| **Repeat expansion and tempo fallback** | **Strong** | Repeat expand/disable/safe-fail paths in branches + fallbacks; empty/exception boundaries and global BPM fallback with auditable `tempo_info`. |
| **Event rates** | **Strong** | `test_event_rates.py` on synthetic matrices; `event_rates.py` at 100% coverage. |
| **Fusion / coincidence** | **Medium** | `test_fusion.py` and `test_coincidence_merge.py` cover key behaviours; `horizontal_density` (Mustextu core) excluded from coverage metrics. Partitional layer tested on minimal fixture only. |
| **Granularity axioms** | **Strong** | `test_granularity_axioms.py` validates VD4 fused-onset IOI/burstiness/granularity-index on synthetic trains plus raw/fused parity; musicological inspection report refrozen (v1.0.7). |
| **Corpus regression fixtures** | **Medium** | Three fixtures with JSON snapshots and `compare_all.py`; parametrized offset/Mustextu alignment. Limited musical diversity; no per-metric golden files beyond three scalars. |
| **Heatmaps and plotting** | **Medium** | `test_heatmaps.py` strong on matrix shapes and smoke plots; `heatmaps.py` 87%. `plots.py` omitted from coverage; only one activity-plot smoke test. |
| **Reports / export** | **Medium** | `reports.py` 100%; `test_pipeline.py` checks `analysis.json`; `test_offset_audit.py` checks `tempo_model` and `warnings` key. No deep schema/content regression for exports. |
| **Audit metadata** | **Medium** | Loader tempo-fallback warnings tested; export includes audit keys. `audit.py` itself lightly exercised (33% coverage) — `merge_audits` largely untested. |
| **Configuration validation** | **Weak** | Only invalid `pitch_domain` and heatmap mode; most `AnalysisConfig` fields and edge cases untested. |

---

## 3. Musical-methodological invariants already tested

| Invariant | Where tested | Strength |
|-----------|--------------|----------|
| **Non-negative onset times** | `test_loader.py` (`onset_sec >= 0`); `test_util_tempo_branches.py` (monotonic/non-negative QL map); `test_onset_extraction.py` (positive ms onsets) | Strong (unit); corpus checks min onsets indirectly |
| **Positive durations** | `test_loader.py` (`duration_sec > 0`); `test_note_extraction.py` (duration = end − start on ties/chords) | Strong (unit) |
| **end ≥ start (tie merge)** | `test_note_extraction.py` (merged tie duration 2.0, 3.0 QL; open tie flush 2.5 QL) | Strong |
| **Ties merged correctly** | `test_note_extraction.py` (start/continue/stop, chord ties, merge vs raw count); `test_loader.py` via fixture merge count | Strong |
| **Open ties flushed at part end** | `test_note_extraction.py::test_tied_note_start_without_stop_flushes_at_part_end` | Strong |
| **Chords → one event per pitch** | `test_note_extraction.py::test_chord_extracts_one_event_per_pitch` | Strong |
| **Rests excluded from onsets** | `test_onset_extraction.py::test_rests_do_not_generate_onsets` | Strong |
| **Grace notes per `ignore_grace`** | `test_onset_extraction.py` (excluded when True, included when False) | Strong |
| **Tempo fallback explicit and auditable** | `test_loader.py` (warning codes, `source`, `reason`); `test_util_tempo_fallbacks.py` (`tempo_info`); `test_offset_audit.py` (`tempo_model`, `warnings`) | Strong |
| **Repeat expansion failure → safe fallback** | `test_util_tempo_branches.py`, `test_util_tempo_fallbacks.py` (RecursionError, RuntimeError, part-level failure) | Strong |
| **Global QL (not measure-local collapse)** | `test_offset_audit.py` (span > 1.5 s for multi-measure corpus); `test_global_offsets_integration.py` (sparse_homophony span 4 s; raw note-matrix rate 2.25; fused EPS global 0.75 in corpus ref) | Strong for 3 fixtures |
| **Mustextu onsets align with loader** | `test_offset_audit.py` (parametrized, ±50 ms) | Medium |
| **util_tempo ↔ timebase parity** | `test_util_tempo_parity.py` on synthetic + all corpus fixtures | Medium–Strong |
| **Monotonic time mapping** | `test_timebase_axioms.py`, `test_util_tempo_branches.py`, `test_util_tempo_parity.py` | Strong |
| **Corpus metric stability** | `test_corpus.py` + `compare_all.py` (`num_events` fused, `num_notes` raw, `events_per_second`, `rate_eps` ± tolerances) | Medium (3 scores only) |
| **No raw `element.offset` in core timeline modules** | `test_offset_audit.py::test_core_modules_avoid_raw_element_offset` | Strong (static guard) |

---

## 4. Musical-methodological invariants not yet sufficiently tested

| Gap | Current state | Risk |
|-----|---------------|------|
| **Multi-voice / polyphonic textures** | No dedicated fixture or test for multiple voices in one part with independent rhythms | Voice collision, onset double-counting, layer mislabelling |
| **Cross-measure and cross-part ties** | Unit tests use single-part, single-measure or adjacent-note ties; no MusicXML tie across measures/parts | Duration inflation, duplicate onsets in real scores |
| **Tempo changes combined with repeats** | Tempo and repeat paths tested separately; no integrated score with both | Wrong timeline after expansion + segment shift |
| **Transposing instruments beyond simple clarinet** | One B♭ clarinet case in `test_loader.py`; no horn in F, piccolo, etc. | Written vs sounding errors in multi-instrument scores |
| **Complex MusicXML layouts** | Corpus fixtures are music21-generated, relatively regular; no pickup measures, tuplets, divisions quirks, multi-staff parts | Parser edge cases in wild exports |
| **Malformed / incomplete score data** | Good defensive unit tests (fakes/monkeypatch); few real corrupt MusicXML files | Production failures on user uploads |
| **Numerical metric regression** | Only 3 scalar snapshots per fixture; no golden IOI distributions, burstiness, heatmap hashes, or per-bar rates | Silent analytical drift in thesis-facing metrics; interpret scalars per [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) before locking |
| **Negative / zero duration prohibition at pipeline level** | Asserted in unit tests, not as a global post-condition on every corpus run | Rare corruption could slip through integration |
| **`merge_audits` and multi-warning export** | `audit.py` mostly untested | Incomplete warning propagation in combined exports |
| **`input_layer` direct paths** | Omitted from coverage; loader tests partially subsume | MIDI/MusicXML divergence between layers |
| **Partitional / fusion on real polyphony** | Single minimal `sample.musicxml` smoke test | Layer fusion untested on layered_async fixture |
| **GUI and CLI entry points** | Not tested | User-facing regressions undetected |

---

## 5. Corpus fixture review

### `dense_onset_burst`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | Single part, 120 BPM, rapid succession of short notes — a local **onset burst** within a measure. |
| **Expected analytical behaviour** | High global EPS (~21 events/s over onset span); many distinct onset times; tests global-offset timeline span; Mustextu `rate_eps` ≈ 20 (window-based, distinct merged onsets — see [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md)). |
| **Reference snapshot** | `num_events: 20`, `events_per_second: 21.053…`, `rate_eps: 20.0` |
| **Test usage** | **Strong** — parametrized in `test_offset_audit.py` (timeline span, Mustextu alignment); included in `compare_all.py` and `test_util_tempo_parity.py`. |

### `layered_async`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | **Two parts** with staggered entries — asynchronous **layered** texture (not homorhythmic). |
| **Expected analytical behaviour** | Moderate event rate (~8.77 events/s); per-part onset layers; checks that multi-part global QL does not collapse layers onto one timeline. |
| **Reference snapshot** | `num_events: 16`, `events_per_second: 8.767…`, `rate_eps: 8.0` |
| **Test usage** | **Medium** — same parametrized offset/Mustextu tests and `compare_all.py`; **no test asserts per-part rates or fusion behaviour** on this fixture specifically. |

### `sparse_homophony`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | Single part, **60 BPM**, homophonic chordal attacks over 2 measures — sparse, synchronized texture. |
| **Expected analytical behaviour** | Fused EPS global 0.75 (3 horizontal attacks / 4 s span at 60 BPM); raw note-matrix rate 9/4 = 2.25; Mustextu `rate_eps` ≈ 0.6. |
| **Reference snapshot** | `num_events: 3`, `num_notes: 9`, `events_per_second: 0.75`, `rate_eps: 0.6` |
| **Test usage** | **Strong** — dedicated `test_global_offsets_integration.py::test_sparse_homophony_fixture_span_and_rate`; export audit test; full corpus regression. |

### Cross-fixture observation

All three fixtures share the same regression shape (3 scalars). They validate **stability** and **global-offset sanity** well, but do not exhaust **musical topology** (ties, grace, repeats, tempo mid-score, transposition).

---

## 6. Recommendations — additional fixtures

| Proposed fixture | Purpose | Priority |
|------------------|---------|----------|
| **`regular_homorhythm`** | Steady homorhythmic layers — fused IOI CV = 0 on regular grid; raw IOI CV elevated (chordal zeros) — see [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) §4 | High (implemented in `musicological_regression/`) |
| **`tied_sustained_texture`** | Cross-measure tied notes — validate merged durations and onset counts | High |
| **`tempo_change_mid_score`** | Mid-piece BPM change (e.g. 120→60) — anchor QL→seconds and rate denominators | High |
| **`repeated_section`** | Start/end repeat or DC al coda — exercise `expand_repeats_if_requested` in pipeline + metric stability | High |
| **`grace_note_passage`** | Grace notes before main beats — validate `ignore_grace` default in full pipeline | Medium |
| **`transposing_instrument_score`** | B♭ clarinet + concert-pitch part — written vs sounding pipeline option | Medium |
| **`dense_chordal_blocks`** | Large chords per onset — chord extraction + spectral/heatmap density | Medium |
| **`empty_or_degenerate_score`** | Empty part or zero-duration score — safe degradation, audit warnings | Low |

Each new fixture should gain a `corpus/reference/<name>.json` snapshot **and** at least one invariant test beyond the three global scalars (e.g. span, per-part onset count, or a named metric from `docs/FORMULAS.md`).

---

## 7. Priority list

### High priority

1. Add **cross-measure tie** and **tempo-change** corpus fixtures with reference metrics and loader/onset invariant tests.
2. Add **repeat-section** fixture run through full `run_analysis` with expanded vs unexpanded comparison.
3. Extend corpus regression beyond three scalars — e.g. golden **IOI CV**, **burstiness**, and **per-bar rates** for at least one fixture (definitions and risks in [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md)).
4. Test **partitional fusion** on `layered_async` (multi-part fixture already exists).
5. Add **`input_layer`**-targeted tests or remove omission only after coverage — document parity with `loader` for MIDI/MusicXML.

### Medium priority

6. **`grace_note_passage`** fixture through pipeline; assert onset count with default `ignore_grace=True`.
7. **`transposing_instrument_score`** with written vs sounding config and pitch assertions.
8. Broaden **`AnalysisConfig`** validation tests (window sizes, bin widths, invalid combinations).
9. Test **`audit.merge_audits`** warning concatenation.
10. Increase **heatmap** regression (matrix sum or hash) on one corpus fixture.

### Low priority

11. **`empty_or_degenerate_score`** fixture for graceful empty outputs.
12. CLI / **`run.py`** smoke test.
13. GUI smoke test (if GUI remains in scope).
14. **`plots.py`** coverage or explicit omission rationale in docs.

---

## 8. Final judgement

### Technically robust?

**Yes, for the symbolic timeline core.** The suite achieves **91.48%** coverage on `granular_v2`, with **100%** on `offsets`, `note_extraction`, `onset_extraction`, `util_tempo`, `event_rates`, `fusion`, `pipeline`, and `reports`. Defensive branches (tempo fallback, repeat failure, offset resolution, grace/rest filtering) are exercised with deterministic unit tests and monkeypatches portable across Python 3.10 and 3.11. Static guards prevent measure-local offset regressions in core modules.

### Methodologically adequate?

**Partially.** Unit-level tests strongly encode music-analytical axioms (tie merge, monotonic time, rate definitions, granularity indices on synthetic trains). The **corpus layer is thin**: three music21-generated fixtures and three scalar snapshots per file. That is adequate for **engineering regression** but not yet for **musicological confidence** across real score diversity.

### Still missing musicological regression tests?

**Yes.** The largest gaps are **multi-voice polyphony**, **cross-part/measure ties**, **combined tempo + repeat scenarios**, **richer MusicXML layouts**, and **numerical golden metrics** beyond global event rate and Mustextu `rate_eps`. The current suite would catch most **timeline/offset bugs** and **tempo-map failures** quickly, but could miss **texture-specific** analytical errors that only appear in varied orchestral or piano-vocal scores.

### Overall grade (qualitative)

| Dimension | Assessment |
|-----------|------------|
| Unit-test depth (core parsing/timebase) | **A** |
| Defensive / fallback coverage | **A** |
| Integration / pipeline | **B+** |
| Corpus / musicological regression | **C+** |
| Export & GUI surface | **C** |

**Bottom line:** The repository has a **mature engineering test suite** around the critical path from MusicXML/MIDI to timed note/onset matrices. To support thesis-grade claims about analytical behaviour across musical styles, the next investment should be **targeted corpus fixtures** and **richer reference metrics**, not further micro-unit coverage of already-saturated modules.

---

*Summary refreshed 2026-06-27 (173 tests; Tier-1 VD10 multi-block API tests complete — `trajectory.py` ~96% coverage).*
