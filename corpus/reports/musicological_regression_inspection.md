# Musicological regression — exploratory inspection

Generated: 2026-06-06 12:20 UTC

Phase 1 report. Values are **exploratory** — not locked golden references.

**Defensive fixture:** `empty_or_degenerate_score` is documented separately below. It is **not** a successful normal analysis row; the summary table shows loader-level zeros only because loading succeeds before the pipeline step that fails.

| Fixture | Events | Unique onsets | Max simultaneous | Sync fraction | EPS global | IOI CV |
|---------|-------:|--------------:|-----------------:|--------------:|-----------:|-------:|
| dense_chordal_blocks | 12 | 3 | 4 | 0.000 | 6.0000 | 2.1213 |
| empty_or_degenerate_score † | 0 | 0 | 0 | — | — | — |
| grace_note_passage | 8 | 4 | 2 | 0.000 | 5.3333 | 1.1547 |
| layered_async | 12 | 12 | 1 | 0.000 | 3.4286 | 0.3499 |
| multi_voice_polyphony | 5 | 5 | 1 | 0.000 | 4.0000 | 0.3464 |
| regular_homorhythm | 48 | 16 | 3 | 0.667 | 6.4000 | 1.4606 |
| repeated_section | 2 | 2 | 1 | 0.000 | 1.0000 | 0.0000 |
| tempo_change_mid_score | 16 | 16 | 1 | 0.000 | 1.3913 | 0.3254 |
| tied_sustained_texture | 4 | 2 | 2 | 0.500 | 2.0000 | 1.4142 |
| transposing_instrument_score | 3 | 3 | 1 | 0.000 | 3.0000 | 0.0000 |

## Per-fixture notes

### `dense_chordal_blocks`
- Tempo source: `timebase_segments`; segments: `1`

### `empty_or_degenerate_score` *(defensive / degenerate — not normal analysis)*

- **Fixture role:** Degenerate input (one empty measure). Used to observe empty-score behaviour, **not** as a golden reference for standard metrics.
- **Loader:** Succeeds; note matrix has **0 events** (see summary table above).
- **Full pipeline (`run_analysis`, Mustextu enabled):** **Controlled failure** — `ValueError('onsets_per_layer_ms cannot be empty.')`. This is **expected and reported** in phase 1; it does **not** indicate a bug in the inspection script.
- **Status:** Not comparable to other fixtures. Do **not** treat sync/EPS/IOI columns as meaningful for this row. Phase 2 should decide whether the contract is (a) explicit empty analysis output or (b) a documented, non-fatal skip when Mustextu has no layers.
- **Not a golden reference** for `corpus/reference/` until that contract is agreed.

### `grace_note_passage`
- Tempo source: `timebase_segments`; segments: `1`
- Grace onsets: ignore `4`, include `8`

### `layered_async`
- Tempo source: `timebase_segments`; segments: `3`

### `multi_voice_polyphony`
- Tempo source: `timebase_segments`; segments: `1`

### `regular_homorhythm`
- Tempo source: `timebase_segments`; segments: `3`

### `repeated_section`
- Tempo source: `timebase_segments`; segments: `1`
- Repeat expansion: `2` → `4` events

### `tempo_change_mid_score`
- Tempo source: `timebase_segments`; segments: `4`
- Unique-onset IOIs (sec): `[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]`

### `tied_sustained_texture`
- Tempo source: `timebase_segments`; segments: `1`
- Tie merge: raw `6` / merged `4` events; unique onsets raw `3` → merged `2`

### `transposing_instrument_score`
- Tempo source: `timebase_segments`; segments: `1`
- Written pitches: `[60, 64, 67]`
- Sounding pitches: `[58, 62, 65]`

† `empty_or_degenerate_score`: loader-only zeros; full pipeline did not complete (see per-fixture notes).

> Review these values before promoting any to `corpus/reference/` golden files.  
> Exclude `empty_or_degenerate_score` from golden promotion until empty-input pipeline behaviour is specified.
