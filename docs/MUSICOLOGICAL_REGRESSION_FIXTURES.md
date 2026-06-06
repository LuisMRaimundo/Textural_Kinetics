# Musicological regression fixtures (phase 1)

Controlled MusicXML fixtures for **qualitative** analytical regression.  
Location: `corpus/fixtures/musicological_regression/`

## Regeneration

```bash
python corpus/scripts/create_musicological_regression_fixtures.py
python corpus/scripts/inspect_musicological_regression.py
```

- **Generator:** `corpus/scripts/create_musicological_regression_fixtures.py` (music21, deterministic)
- **Exploratory report:** `corpus/reports/musicological_regression_inspection.md` (+ JSON sibling)
- **Qualitative tests:** `tests/test_musicological_regression.py`

> Phase 1 does **not** lock numerical golden values in `corpus/reference/`.  
> Review inspection output before promoting metrics to strict regression.  
> **Metric semantics:** [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) — especially before promoting EPS, IOI CV, or synchrony fraction.

---

## Fixture catalogue

### `regular_homorhythm`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | Three parts (Soprano, Alto, Tenor) in four measures; each part plays one pitch class per beat; all parts attack on the same quarter-note grid (120 BPM). |
| **Analytical purpose** | Vertical alignment / homorhythmic coincidence; near-periodic IOIs on the composite onset train. |
| **Expected behaviour** | High `max_simultaneous_pitches` (3); inspection reports synchrony fraction ≈ 0.67 (layer τ-merge, not pitch count alone). Unique-onset IOIs ~0.5 s at 120 BPM; raw-event IOI CV may be high — see [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) §4. |

### `tied_sustained_texture`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | Two parts with half-note ties crossing the barline (start → stop), then a whole note. |
| **Analytical purpose** | Tie-merge correctness; sustained sonority without spurious re-attacks. |
| **Expected behaviour** | Few unique onsets; merged event count < raw tied components; long durations. |

### `dense_chordal_blocks`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | Single part; three four-note chords alternating with quarter rests. |
| **Analytical purpose** | Vertical density per attack; temporal spacing between chord blocks. |
| **Expected behaviour** | Up to four simultaneous pitches per onset; moderate global event rate due to rests. |

### `layered_async`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | Three parts with staggered eighth-note entries (0, 0.5, 1.0 quarter offsets within a 8-QL span). |
| **Analytical purpose** | Low vertical coincidence; dispersed onset layers. |
| **Expected behaviour** | Low Mustextu synchrony fraction vs homorhythm (staggered layer onsets); staggered IOI profile on the event stream. |

> **Note:** Distinct from legacy `corpus/fixtures/layered_async.musicxml` (older corpus regression set).

### `tempo_change_mid_score`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | Four measures: 60 BPM (m1–2), then 120 BPM (m3–4); one note per beat throughout. |
| **Analytical purpose** | Stepwise tempo model; QL spacing constant but `onset_sec` spacing must compress after the mark. |
| **Expected behaviour** | ≥2 tempo segments; unique-onset IOIs ~1.0 s then ~0.5 s after the change. |

### `repeated_section`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | Two measures enclosed in a forward repeat (`||:` … `:`||). |
| **Analytical purpose** | Repeat expansion increases event count when enabled; failures must fall back safely. |
| **Expected behaviour** | `expand_repeats_if_requested(..., True)` doubles note events for this simple ||: :|| structure. |

### `grace_note_passage`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | Grace notes before four principal quarter notes. |
| **Analytical purpose** | `ignore_grace` policy in onset extraction / Mustextu path. |
| **Expected behaviour** | More layer onsets when `ignore_grace=False`; grace excluded when `True`. |

### `transposing_instrument_score`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | B♭ clarinet; written C4–E4–G4. |
| **Analytical purpose** | `pitch_domain` written vs sounding. |
| **Expected behaviour** | Identical event count and onset times; sounding pitches lowered by major second. |

### `multi_voice_polyphony`

| Aspect | Detail |
|--------|--------|
| **Musical situation** | One piano part, two voices with interleaved quarter notes across two measures. |
| **Analytical purpose** | Preserve independent voice onsets inside a single part. |
| **Expected behaviour** | Events from both voices present; no erroneous onset collapse. |

### `empty_or_degenerate_score` *(defensive / degenerate)*

| Aspect | Detail |
|--------|--------|
| **Musical situation** | One measure, no notes. |
| **Fixture class** | **Defensive / degenerate** — not a normal analytical reference score. |
| **Analytical purpose** | Probe how the stack behaves when there is nothing to analyse. |
| **Expected behaviour (phase 1)** | Either an **explicitly empty** loader result (`num_events == 0`) **or** a **controlled, reported failure** when a downstream step (e.g. Mustextu onset layers) cannot proceed on empty input. Both outcomes are acceptable for this fixture until phase 2 defines a single contract. |
| **Not in scope** | Golden reference metrics, synchrony/EPS/IOI baselines, or “successful normal analysis” in `inspect_musicological_regression.py`. |

**Current observation (2026-06-06):** `load_score_and_note_matrix` succeeds with an empty note matrix, but `run_analysis` with Mustextu enabled raises `ValueError('onsets_per_layer_ms cannot be empty.')`. The inspection report records this as a **controlled load failure** — not as a completed analysis row comparable to the other fixtures.

**Qualitative tests:** `tests/test_musicological_regression.py` checks loader-level invariants (no crash, empty matrix). Full-pipeline behaviour on this fixture remains **under review** for phase 2.

---

## Defensive vs normal fixtures

| Class | Fixtures | Phase-1 role |
|-------|----------|----------------|
| **Normal** | All except `empty_or_degenerate_score` | Exploratory metrics + qualitative musical invariants |
| **Defensive / degenerate** | `empty_or_degenerate_score` | Document empty-input behaviour; no golden reference yet |

---

## Relationship to existing corpus

| Set | Role |
|-----|------|
| `corpus/fixtures/*.musicxml` | Legacy scalar regression (`compare_all.py`, reference JSON) |
| `corpus/fixtures/musicological_regression/` | Phase-1 musicological situations + qualitative invariants |

---

## Analyst checklist before phase 2

1. Run `inspect_musicological_regression.py` and review IOIs, synchrony, and event counts against [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md).
2. Confirm qualitative pytest invariants pass on Python 3.10 and 3.11.
3. Select metrics to promote into `corpus/reference/musicological_regression/*.json` (if desired).
4. Document tolerances in `docs/CORPUS_REFERENCIA.md` or a dedicated phase-2 note.
