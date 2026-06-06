# Musicological golden values — Phase 2 decision record

**Source report:** `corpus/reports/musicological_regression_inspection.md` (generated 2026-06-06 12:20 UTC)  
**Phase:** Decision only — no golden tests or reference files are created by this document.

---

## 1. Purpose

Phase 1 introduced ten controlled MusicXML fixtures under `corpus/fixtures/musicological_regression/`, qualitative pytest invariants in `tests/test_musicological_regression.py`, and an exploratory inspection report (`corpus/reports/musicological_regression_inspection.md`).

Phase 1 answers: *does the pipeline behave plausibly on musically labelled situations?*

Phase 2 must answer: *which numerical observations are stable and semantically clear enough to become **strict** regression references?*

This document records analyst-facing decisions before any values are written to `corpus/reference/` or enforced by golden tests. **No value listed here is locked until explicitly reviewed and implemented in Phase 2.**

---

## 2. Decision categories

| Category | Meaning |
|----------|---------|
| **PROMOTE** | Structurally exact, analytically unambiguous, safe to become golden values after analyst sign-off. |
| **EXPLORE** | Useful diagnostic values; keep in inspection reports but do not enforce as strict references yet. |
| **CLARIFY** | Interpretation depends on metric definition or fixture class; resolve semantics before any lock. |

---

## 3. Decision table

Values below are taken from the current inspection report unless noted as derived from per-fixture notes in the same report.

| Fixture | Value / property | Current value | Decision | Rationale |
|---------|------------------|---------------|----------|-----------|
| `tempo_change_mid_score` | Unique-onset IOIs before tempo change | ~1.0 s (first eight IOIs in `[1.0, …, 1.0, 0.5, …]`) | **PROMOTE** | Direct consequence of 60 BPM (1 s per quarter); analytically unambiguous. |
| `tempo_change_mid_score` | Unique-onset IOIs after tempo change | ~0.5 s (remaining seven IOIs) | **PROMOTE** | Direct consequence of 120 BPM (0.5 s per quarter); analytically unambiguous. |
| `tempo_change_mid_score` | Tempo segments | ≥ 2 (inspection: 4) | **PROMOTE** | Golden invariant is detection of **both** 60 BPM and 120 BPM sections; exact segment count (e.g. 4) may vary with MetronomeMark representation and is not required unless the fixture generator documents an exact target. |
| `tempo_change_mid_score` | Events / unique onsets | 16 / 16 | **PROMOTE** | One note per beat across four measures; structurally exact. |
| `tempo_change_mid_score` | EPS global | 1.3913 | **EXPLORE** | Depends on span and event-count policy; not primary tempo proof. |
| `tempo_change_mid_score` | IOI CV | 0.3254 | **EXPLORE** | Useful diagnostic; clarify unique-onset vs raw-event basis before lock. |
| `transposing_instrument_score` | Written pitches | `[60, 64, 67]` | **PROMOTE** | B♭ clarinet written content; deterministic. |
| `transposing_instrument_score` | Sounding pitches | `[58, 62, 65]` | **PROMOTE** | Major-second transposition; deterministic. |
| `transposing_instrument_score` | Onset times written vs sounding | unchanged (report: 3 events, 3 unique onsets each) | **PROMOTE** | Transposition must not alter timing. |
| `grace_note_passage` | Layer onsets, `ignore_grace=True` | 4 | **PROMOTE** | Direct test of grace exclusion policy. |
| `grace_note_passage` | Layer onsets, `ignore_grace=False` | 8 | **PROMOTE** | Direct test of grace inclusion policy. |
| `grace_note_passage` | Note-matrix events | 8 | **PROMOTE** | Loader/note-extraction structural value: four principal notes plus four grace notes are preserved **before** onset filtering; analytical onset count is governed separately by `ignore_grace=True` (4) / `False` (8). |
| `repeated_section` | Events without repeat expansion | 2 | **PROMOTE** | Simple two-measure source material. |
| `repeated_section` | Events with repeat expansion | 4 | **PROMOTE** | Deterministic doubling for `\|\|:` … `:\|\|` structure. |
| `dense_chordal_blocks` | Events | 12 | **PROMOTE** | Three chords × four pitches. |
| `dense_chordal_blocks` | Unique onsets | 3 | **PROMOTE** | Three chordal attack times (rests between blocks). |
| `dense_chordal_blocks` | Max simultaneous pitches | 4 | **PROMOTE** | Four-note chords; direct vertical density. |
| `dense_chordal_blocks` | Sync fraction | 0.000 | **CLARIFY** | Max simultaneous = 4 shows chordal simultaneity, but sync = 0 suggests inter-part/layer metric, not intra-chord density. Clarify Mustextu synchrony semantics before lock. |
| `dense_chordal_blocks` | IOI CV | 2.1213 | **EXPLORE** | Reflects rest spacing; useful but secondary to structural counts. |
| `regular_homorhythm` | Events | 48 | **PROMOTE** | 3 parts × 16 beats. |
| `regular_homorhythm` | Unique onsets | 16 | **PROMOTE** | One composite attack time per quarter across four measures. |
| `regular_homorhythm` | Max simultaneous pitches | 3 | **PROMOTE** | Three parts attack together. |
| `regular_homorhythm` | Sync fraction | 0.667 | **EXPLORE** | Useful homorhythm diagnostic; confirm layer labelling and coincidence tolerance before strict lock. |
| `regular_homorhythm` | IOI CV | 1.4606 | **CLARIFY** | Counter-intuitive for “regular” homorhythm if read as unique-onset regularity; likely affected by simultaneous-event structure in granularity code. Clarify whether IOI CV uses raw events or unique onsets. |
| `tied_sustained_texture` | Raw events | 6 | **PROMOTE** | Pre-merge tie components. |
| `tied_sustained_texture` | Merged events | 4 | **PROMOTE** | Tie merge reduces spurious attacks. |
| `tied_sustained_texture` | Unique onsets raw → merged | 3 → 2 | **PROMOTE** | Direct sustained-texture / tie-merge proof. |
| `tied_sustained_texture` | Sync fraction | 0.500 | **EXPLORE** | Two-part texture; interpret after synchrony definition is fixed. |
| `layered_async` | Events / unique onsets | 12 / 12 | **EXPLORE** | Staggered layers; counts useful but not yet tied to a single structural formula. |
| `layered_async` | Max simultaneous | 1 | **EXPLORE** | Confirms low vertical coincidence; good qualitative check, weak alone as golden scalar. |
| `layered_async` | Sync fraction | 0.000 | **EXPLORE** | Consistent with async design; keep diagnostic until synchrony semantics clarified. |
| `layered_async` | IOI CV | 0.3499 | **EXPLORE** | Useful contrast to homorhythm; interpret with IOI definition care. |
| `multi_voice_polyphony` | Events | 5 | **EXPLORE** | Qualitative invariant passes; lock only after multi-voice extraction semantics verified across music21 versions. |
| `multi_voice_polyphony` | Unique onsets | 5 | **EXPLORE** | Same as above. |
| `multi_voice_polyphony` | Pitch classes preserved (C4, G4, …) | qualitative only | **EXPLORE** | Tested structurally in pytest; defer numeric golden until voice semantics documented. |
| `multi_voice_polyphony` | EPS global | 4.0000 | **EXPLORE** | Span-dependent derived metric. |
| All fixtures (except empty) | EPS global | see inspection table | **EXPLORE** | Useful dashboards; depend on duration-window and event-count definitions. |
| `empty_or_degenerate_score` | Loader events | 0 | **CLARIFY** | Defensive fixture only. Loader empty result is observed; full pipeline fails with `ValueError('onsets_per_layer_ms cannot be empty.')`. Do not promote to normal golden reference until empty-input contract is defined. |
| `empty_or_degenerate_score` | Pipeline / Mustextu output | controlled failure | **CLARIFY** | Not a successful analysis; exclude from standard golden JSON. |

---

## 4. Recommended Phase 2 golden file structure

**Proposed path (not created in Phase 1):**

`corpus/reference/musicological_regression_golden.json`

**Design principles:**

- One top-level key per fixture (excluding `empty_or_degenerate_score` until contract is defined).
- Prefer **structural** fields (counts, pitch lists, IOI bands) over interpretive composites (sync fraction, IOI CV, EPS).
- Use explicit tolerances for floating-point seconds.
- Keep Mustextu-derived metrics out of the first golden slice unless semantics are documented.

**Suggested skeleton (illustrative only):**

```json
{
  "_meta": {
    "phase": 2,
    "source_report": "corpus/reports/musicological_regression_inspection.md",
    "analyst_review_required": true
  },
  "tempo_change_mid_score": {
    "num_events": 16,
    "unique_onsets": 16,
    "min_tempo_segments": 2,
    "required_bpm_sections": [60, 120],
    "unique_onset_iois_sec": {
      "before_change": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
      "after_change": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
      "tolerance": 1e-6
    }
  },
  "transposing_instrument_score": {
    "written_pitches": [60, 64, 67],
    "sounding_pitches": [58, 62, 65],
    "onset_sec_tolerance": 1e-6
  },
  "grace_note_passage": {
    "onsets_ignore_grace": 4,
    "onsets_include_grace": 8
  },
  "repeated_section": {
    "events_collapsed": 2,
    "events_expanded": 4
  },
  "dense_chordal_blocks": {
    "num_events": 12,
    "unique_onsets": 3,
    "max_simultaneous_pitches": 4
  },
  "regular_homorhythm": {
    "num_events": 48,
    "unique_onsets": 16,
    "max_simultaneous_pitches": 3
  },
  "tied_sustained_texture": {
    "raw_events": 6,
    "merged_events": 4,
    "unique_onsets_raw": 3,
    "unique_onsets_merged": 2
  }
}
```

Optional later sections (after **CLARIFY** items resolved): `sync_fraction`, `ioi_cv`, `eps_global`, `multi_voice_polyphony` counts.

---

## 5. Phase 2 implementation rules

1. **Lock structurally exact values first** — event counts, unique onsets, pitch lists, repeat expansion ratios, grace onset counts, tempo IOI bands.
2. **Avoid locking ambiguous derived metrics** — EPS global, IOI CV, Mustextu synchrony fraction until definitions are written in `docs/FORMULAS.md` or `docs/MANUAL_METRICAS.md` and agreed by the analyst.
3. **Use tolerances for floating-point seconds** — recommend `1e-6` for synthetic fixtures at 60/120 BPM; looser tolerances only if MusicXML export rounding is proven platform-dependent.
4. **Keep `empty_or_degenerate_score` out of normal golden regression** — treat as defensive/degenerate; define empty-input contract separately (explicit empty output vs documented skip).
5. **Analyst review gate** — every golden value must be compared against a fresh `inspect_musicological_regression.py` run and signed off before pytest enforcement or CI integration.
6. **Regenerate fixtures before locking** — run `create_musicological_regression_fixtures.py` and confirm inspection stability on Python 3.10 and 3.11.
7. **Do not conflate fixture sets** — `corpus/fixtures/musicological_regression/` is independent of legacy `corpus/fixtures/*.musicxml` used by `compare_all.py`.

---

## 6. Final recommendation

Phase 2 should **begin with structural golden values**, not interpretively complex metrics.

**First golden slice (recommended PROMOTE set):**

- `tempo_change_mid_score` — IOI bands and segment count  
- `transposing_instrument_score` — pitch lists and timing invariance  
- `grace_note_passage` — onset counts under `ignore_grace` True/False  
- `repeated_section` — 2 → 4 event expansion  
- `dense_chordal_blocks`, `regular_homorhythm`, `tied_sustained_texture` — structural counts from the inspection table  

**Defer:**

- All **EPS global** values (**EXPLORE**)  
- **IOI CV** on `layered_async`, `tempo_change_mid_score`, and especially `regular_homorhythm` (**CLARIFY** / **EXPLORE**)  
- **Sync fraction** where it conflicts with intuitive vertical density (**CLARIFY**)  
- **`multi_voice_polyphony`** numeric locks (**EXPLORE**)  
- **`empty_or_degenerate_score`** entirely (**CLARIFY** — defensive only)  

After the first structural golden file is reviewed, add a dedicated compare script (e.g. `corpus/scripts/compare_musicological_regression.py`) and only then introduce strict pytest golden tests. Until that review completes, Phase 1 qualitative tests and the exploratory inspection report remain the authoritative regression layer for musicological fixtures.

---

*Cross-references: `docs/MUSICOLOGICAL_REGRESSION_FIXTURES.md`, `corpus/reports/musicological_regression_inspection.md`, `docs/TEST_QUALITY_AUDIT.md`.*
